"""
audit.py

The full pipeline, in the order a real wage audit actually needs it:

  1. CLASSIFY each employee's award level from their job description.
     AI, using the structured_confidence strategy — the only one of the
     three tested approaches that can say "not sure" instead of guessing
     (see classify.py / strategies.py). If it's not confident, the
     employee is set aside for a human to classify, and NO pay
     calculation is attempted for them — a wrong classification would
     silently produce a wrong pay calculation, which is worse than an
     honest "needs review."

  2. CALCULATE what each shift should have paid, using the award rules
     as plain code (rules.py). Not AI. This has to be exactly right,
     every time, and explainable by hand if challenged.

  3. COMPARE actual vs. expected pay and flag discrepancies, tagged with
     the exact clause numbers that were breached.

The output of this file is two lists: confirmed discrepancies (ready for
a report) and employees needing manual classification review (nothing
calculated for them yet — that's the correct, safe behavior, not a gap).
"""

import csv
import argparse
from pathlib import Path
from dataclasses import dataclass

from classify import classify, get_client
from rules import expected_pay_for_shift

TIMESHEET_PATH = Path(__file__).parent / "data" / "timesheet.csv"
TOLERANCE = 0.02


@dataclass
class Discrepancy:
    employee_id: str
    name: str
    date: str
    classification: str
    employment_type: str
    day_type: str
    hours_worked: float
    amount_paid: float
    amount_expected: float
    underpayment: float
    clauses: list[str]


@dataclass
class NeedsReview:
    employee_id: str
    name: str
    job_description: str
    reason: str


def classify_employees(rows: list[dict], client, mock: bool) -> dict:
    """Classify each unique employee once (not once per shift row)."""
    seen = {}
    results = {}
    for row in rows:
        key = row["employee_id"]
        if key in seen:
            continue
        seen[key] = row["job_description"]
        outcome = classify(row["job_description"], "structured_confidence", client=client, mock=mock)
        results[key] = outcome
    return results


def run_audit(mock: bool = False, path: Path = TIMESHEET_PATH):
    client = get_client(mock)

    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))

    classifications = classify_employees(rows, client, mock)

    discrepancies = []
    needs_review = []
    reviewed_employees = set()

    for row in rows:
        emp_id = row["employee_id"]
        result = classifications[emp_id]

        if result["flagged_for_review"]:
            if emp_id not in reviewed_employees:
                needs_review.append(NeedsReview(
                    employee_id=emp_id,
                    name=row["name"],
                    job_description=row["job_description"],
                    reason=("Could not confidently classify from the job description alone "
                            "(low confidence or ambiguous duties/tenure)."),
                ))
                reviewed_employees.add(emp_id)
            continue  # no pay calculation for unclassified employees

        classification = result["predicted_level"]
        hours = float(row["hours_worked"])
        paid = float(row["amount_actually_paid"])

        expected, clauses = expected_pay_for_shift(
            classification=classification,
            employment_type=row["employment_type"],
            day_type=row["day_type"],
            hours=hours,
        )

        diff = round(expected - paid, 2)
        if abs(diff) > TOLERANCE:
            discrepancies.append(Discrepancy(
                employee_id=emp_id,
                name=row["name"],
                date=row["date"],
                classification=classification,
                employment_type=row["employment_type"],
                day_type=row["day_type"],
                hours_worked=hours,
                amount_paid=paid,
                amount_expected=expected,
                underpayment=diff,
                clauses=clauses,
            ))

    return discrepancies, needs_review


def print_summary(discrepancies, needs_review):
    if discrepancies:
        total = sum(d.underpayment for d in discrepancies)
        print(f"Found {len(discrepancies)} discrepancies. Total underpayment: ${total:.2f}\n")
        for d in discrepancies:
            sign = "underpaid" if d.underpayment > 0 else "overpaid"
            print(f"  {d.name} ({d.date}, {d.day_type}, {d.classification}): "
                  f"paid ${d.amount_paid:.2f}, should be ${d.amount_expected:.2f} "
                  f"({sign} ${abs(d.underpayment):.2f}) — clauses {', '.join(d.clauses)}")
    else:
        print("No pay discrepancies found among classified employees.")

    if needs_review:
        print(f"\n{len(needs_review)} employee(s) need manual classification review "
              f"(no pay calculation attempted):")
        for r in needs_review:
            print(f"  {r.name} ({r.employee_id}): \"{r.job_description}\" — {r.reason}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true",
                         help="Use a fake keyword classifier instead of a real API call, "
                              "to test the pipeline without an API key.")
    args = parser.parse_args()

    if args.mock:
        print("=" * 70)
        print("MOCK MODE — fake classifier, not a real model. Structural test only.")
        print("=" * 70 + "\n")

    discrepancies, needs_review = run_audit(mock=args.mock)
    print_summary(discrepancies, needs_review)