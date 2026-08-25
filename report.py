"""
report.py

Turns the audit's output into a report a person could actually act on.

This is the only file that calls the model for open-ended generation, and it
does two things differently from a naive "summarize this" prompt:

1. It fetches the REAL clause text via retrieve.py for every clause
   number involved, and includes that in the prompt — so the model is
   explaining underpayments using the actual wording of the rule, not
   whatever it remembers (or misremembers) about award clauses in general.

2. It reports the employees who couldn't be confidently classified
   separately and explicitly, as "needs human review" — not silently
   dropped, and not guessed at just to make the report look complete.
"""

import os
from audit import run_audit, Discrepancy, NeedsReview
from retrieve import get_clause_text

SYSTEM_PROMPT = """You are writing a wage audit summary for an employment lawyer to send to a client. \
You are given:
1. A list of confirmed underpayment discrepancies, each with the exact dollar amount and the clause \
number(s) breached.
2. The actual text of those clauses, for reference.
3. A list of employees who could not be confidently classified into an award level from their job \
description, and therefore have not had their pay checked yet.

Rules:
1. Do NOT recalculate or alter any dollar figure — use only the numbers you're given.
2. For each discrepancy, explain in plain English what went wrong, and reference the clause using its \
actual wording (not a generic paraphrase of what that kind of clause usually says).
3. List the employees needing manual classification clearly, as an action item — do not guess a \
classification for them or estimate whether they were under- or overpaid.
4. End with a short summary: total confirmed underpayment, number of employees affected, and number of \
employees still needing manual review.
5. Professional, neutral tone suitable for a legal or HR audience.
"""


def build_prompt(discrepancies: list[Discrepancy], needs_review: list[NeedsReview]) -> str:
    all_clauses = sorted({c for d in discrepancies for c in d.clauses})
    clause_text = get_clause_text(all_clauses)

    disc_lines = [
        f"- {d.name} ({d.employee_id}), {d.date}, {d.day_type}, {d.classification}/{d.employment_type}: "
        f"paid ${d.amount_paid:.2f}, should have been ${d.amount_expected:.2f} "
        f"(underpaid ${d.underpayment:.2f}). Clauses: {', '.join(d.clauses)}."
        for d in discrepancies
    ]
    review_lines = [
        f"- {r.name} ({r.employee_id}): \"{r.job_description}\" — {r.reason}"
        for r in needs_review
    ]

    return (
        f"CONFIRMED DISCREPANCIES:\n" + ("\n".join(disc_lines) if disc_lines else "None.") +
        f"\n\nRELEVANT CLAUSE TEXT:\n{clause_text}\n\n" +
        f"EMPLOYEES NEEDING MANUAL CLASSIFICATION REVIEW:\n" +
        ("\n".join(review_lines) if review_lines else "None.")
    )


def generate_report(discrepancies: list[Discrepancy], needs_review: list[NeedsReview]) -> str:
    if not discrepancies and not needs_review:
        return "No discrepancies found and all employees classified confidently. Nothing to report."

    prompt = build_prompt(discrepancies, needs_review)

    try:
        import groq
    except ImportError:
        return "[groq SDK not installed — showing raw audit output only]\n\n" + prompt

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "[GROQ_API_KEY not set — showing raw audit output only]\n\n" + prompt

    client = groq.Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        max_tokens=900,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true")
    args = parser.parse_args()

    discrepancies, needs_review = run_audit(mock=args.mock)
    print(generate_report(discrepancies, needs_review))