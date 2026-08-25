# Automated Wage Audit Pipeline

One pipeline: given a company's timesheet data, work out who was
underpaid, why, and which employees need a human to double-check their
classification — the same shape as what Subi actually does, per their
job ad ("production LLM systems that audit real employment data against
Australian awards and legislation").

## The pipeline

```
timesheet.csv
     |
     v
[1] CLASSIFY   -- AI, classify.py + strategies.py
     |            Works out each employee's award level from their job
     |            description. Uses the "structured_confidence" approach,
     |            the only one of three tested that can say "not sure"
     |            instead of guessing (see eval.py for why that matters).
     |            Uncertain employees are set aside — no pay is calculated
     |            for them until a human confirms their level.
     v
[2] CALCULATE  -- Plain code, NOT AI. rules.py
     |            Works out what each shift should have paid, using the
     |            award's actual rates and penalty rules.
     v
[3] COMPARE    -- Plain code. audit.py
     |            Flags every shift where paid != expected, tagged with
     |            the clause numbers involved.
     v
[4] EXPLAIN    -- AI, grounded with retrieval. report.py + retrieve.py
                  Fetches the ACTUAL TEXT of every clause involved (not
                  a paraphrase from the model's memory) and writes a
                  plain-English report referencing the real wording.
```

## Why it's built this way

**AI is used exactly twice, in the two places that are genuinely
judgment calls** — classifying an employee from fuzzy language, and
writing a readable explanation. Everything else (the money) is
deterministic code, because that part has to be provably correct, not
just usually correct.

**The classifier is allowed to refuse.** `eval.py` shows why this
matters: two simpler prompting approaches were tested and rejected
specifically because they have no way to express uncertainty — they
always output a level, even for a bare job title with no duties
described. Only the approach that can output "not confident enough,
please review" is used in the actual pipeline.

**The report quotes the real rule, not the model's memory of it.**
`retrieve.py` fetches the exact clause text for every clause a
discrepancy is tagged with, and that real text — not a general
description of "penalty rate clauses tend to say" — is what gets fed to
the model when it writes the final explanation.

## Running it

```bash
pip install -r requirements.txt

# Test the whole pipeline runs correctly, no API key needed:
python audit.py --mock
python report.py --mock

# Real run — needs a free Groq API key (console.groq.com):
# create a file named .env in this folder containing:
#   GROQ_API_KEY=your_key_here
python audit.py
python report.py

# Reliability comparison for the classification step:
python eval.py --mock   # structural test only
python eval.py          # real comparison of the three prompting approaches
```

`.env` is loaded automatically via `python-dotenv` — never commit this file
(it's in `.gitignore`), and never paste a real key into the README or
anywhere else that might get committed or shared.

`--mock` replaces the real model with a dumb keyword-matcher, purely so
you can confirm the code runs correctly before spending real API calls.
It is not a real evaluation of anything — `eval.py` (without `--mock`) is
where the actual comparison happens.

## Files

| File | Role |
|---|---|
| `data/timesheet.csv` | Sample payroll data with job descriptions |
| `data/award.txt` | The award rules (synthetic, see note below) |
| `data/golden_set.json` | Test cases for the classifier reliability eval |
| `rules.py` | Award pay rates and penalty rules, as plain code |
| `classifications.py` | The four award levels, as reference text |
| `strategies.py` | Three prompting approaches for classification |
| `classify.py` | Runs one job description through one strategy |
| `retrieve.py` | Fetches real clause text for a given clause number |
| `audit.py` | Main pipeline — classify, calculate, compare, flag |
| `report.py` | Turns the audit output into a written, cited report |
| `eval.py` | Compares the three classification strategies' reliability |

## A note on the source document

`data/award.txt` is a document I wrote myself, structured like a real
Fair Work Modern Award (clause numbers, classifications, penalty rates)
but with invented rates and simplified rules — not a real award, and not
for actual compliance use. Swapping in a real award (downloaded from the
Fair Work Commission) would mean updating the regex in `retrieve.py` to
match its actual clause numbering, which nests more deeply than this
demo (e.g. 22.1(a)(ii)) — everything downstream is unchanged.

## Honest limitations

- No handling of interacting rules across multiple clauses at once
  (e.g. verifying the model's own arithmetic against the clause text,
  rather than trusting the deterministic engine's math, which is
  already handled separately and correctly in `rules.py`).
- Classification runs once per employee from a single description; a
  real system would need to handle employees whose duties change over
  time or across shifts.
- No versioning — awards are amended and rates change annually; a real
  system needs to know which version applied on which date.