"""
retrieve.py

Chunks the award document by clause and retrieves the exact clause text
for a given clause number. This is the RAG piece — but here it's not a
standalone "ask a question, get an answer" demo. It's used for one
specific, concrete job: when the audit engine says "clause 27 was
breached," this module fetches the ACTUAL WORDING of clause 27, so the
final report can quote the real rule instead of the AI paraphrasing (or
misremembering) it from training data.

Kept deliberately simple (regex chunking + exact clause lookup) rather
than a full similarity-search pipeline, because the audit engine already
knows exactly which clause numbers are relevant — it doesn't need to
*search* for them, just fetch them. A similarity-search version of this
would matter more for a free-text "ask a question about the award"
feature, which isn't what this pipeline needs.
"""

import re
from pathlib import Path

AWARD_PATH = Path(__file__).parent / "data" / "award.txt"
CLAUSE_HEADER_RE = re.compile(r"^CLAUSE\s+(\d+)\s+—\s+(.+)$", re.MULTILINE)


def load_clauses() -> dict[str, dict]:
    """Returns {clause_number: {"title": ..., "text": ...}}"""
    text = AWARD_PATH.read_text()
    matches = list(CLAUSE_HEADER_RE.finditer(text))
    clauses = {}
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        clause_num, title = m.group(1), m.group(2)
        clauses[clause_num] = {"title": title, "text": text[start:end].strip()}
    return clauses


def get_clause_text(clause_numbers: list[str]) -> str:
    """Fetch the real text of one or more clauses, for grounding a report."""
    clauses = load_clauses()
    parts = []
    for num in clause_numbers:
        if num in clauses:
            parts.append(f"[Clause {num} — {clauses[num]['title']}]\n{clauses[num]['text']}")
    return "\n\n".join(parts)