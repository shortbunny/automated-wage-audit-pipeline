"""
eval.py

Runs every strategy over the golden set and measures two different things,
because they matter for different reasons:

1. Accuracy on clear-cut cases — did it get the obviously-right answer
   right? This is the metric everyone thinks to measure.

2. Safe handling of ambiguous cases — when the job description genuinely
   doesn't give enough information, did the approach say so, or did it
   confidently guess anyway? This is the metric that actually matters for
   a compliance product: a wrong classification here isn't a UX
   inconvenience, it's a wrong wage calculation for a real person.

zero_shot and few_shot have no way to express uncertainty at all (see
strategies.py) — so by construction, they will ALWAYS "confidently guess"
on every ambiguous case. That's not a bug in the eval, it's the actual
finding: prompting style alone can't fix this, the output format has to
support saying "I don't know" for that option to even exist.
"""

import argparse
import json
from pathlib import Path
from collections import defaultdict

from classify import classify, get_client

GOLDEN_SET_PATH = Path(__file__).parent / "data" / "golden_set.json"


def load_golden_set():
    return json.loads(GOLDEN_SET_PATH.read_text())


def run_eval(mock: bool = False):
    cases = load_golden_set()
    client = get_client(mock)
    strategies = ["zero_shot", "few_shot", "structured_confidence"]

    results = defaultdict(list)

    for strategy in strategies:
        for case in cases:
            outcome = classify(case["job_description"], strategy, client=client, mock=mock)
            results[strategy].append({**case, **outcome})

    print_report(results, cases)
    return results


def print_report(results: dict, cases: list):
    clear_cases = [c for c in cases if not c["is_ambiguous"]]
    ambiguous_cases = [c for c in cases if c["is_ambiguous"]]

    print(f"{len(clear_cases)} clear-cut cases, {len(ambiguous_cases)} deliberately ambiguous cases\n")
    print(f"{'Strategy':<22} {'Accuracy (clear)':<18} {'Safe on ambiguous':<20} {'Unparseable':<12}")
    print("-" * 74)

    for strategy, outcomes in results.items():
        by_id = {o["id"]: o for o in outcomes}

        correct = sum(1 for c in clear_cases if by_id[c["id"]]["predicted_level"] == c["true_level"])
        accuracy = correct / len(clear_cases) if clear_cases else 0

        safe = sum(1 for c in ambiguous_cases if by_id[c["id"]]["flagged_for_review"])
        safe_rate = safe / len(ambiguous_cases) if ambiguous_cases else 0

        unparseable = sum(1 for o in outcomes if o["predicted_level"] is None and not o["flagged_for_review"])

        print(f"{strategy:<22} {accuracy:.0%} ({correct}/{len(clear_cases)})".ljust(22 + 18) +
              f"{safe_rate:.0%} ({safe}/{len(ambiguous_cases)})".ljust(20) +
              f"{unparseable}")

    print("\nAmbiguous case breakdown (what each strategy actually did):\n")
    for case in ambiguous_cases:
        print(f"  [{case['id']}] {case['job_description'][:70]}...")
        for strategy in results:
            o = next(r for r in results[strategy] if r["id"] == case["id"])
            verdict = "FLAGGED for review" if o["flagged_for_review"] else f"guessed {o['predicted_level']}"
            print(f"      {strategy:<22} -> {verdict}")
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true",
                         help="Run with a fake keyword-based classifier instead of a real API call, "
                              "to test the pipeline without an API key. NOT a real evaluation.")
    args = parser.parse_args()

    if args.mock:
        print("=" * 70)
        print("MOCK MODE — using a fake keyword-based classifier, not a real model.")
        print("This only tests that the pipeline runs end-to-end. Run without")
        print("--mock (with GROQ_API_KEY set) for a real evaluation.")
        print("=" * 70 + "\n")

    run_eval(mock=args.mock)