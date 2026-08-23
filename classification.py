"""
classifications.py

The four job classification levels from the award (Clause 14), as plain
text. This is the reference material every prompting approach will be
given — the model isn't expected to know award rules from memory, it's
expected to apply the rules it's handed, the same way a human classifier
would work from the award document rather than guessing from vibes.
"""

CLASSIFICATION_LEVELS = {
    "Level 1": (
        "An employee who has not yet completed 6 months' retail experience and performs "
        "basic duties such as stacking shelves, price marking and cleaning, under direct "
        "supervision."
    ),
    "Level 2": (
        "An employee who has completed the equivalent of 6 months' retail experience or "
        "induction training, and who performs sales duties, operates a cash register, or "
        "provides customer service without direct, constant supervision."
    ),
    "Level 3": (
        "An employee who has completed the equivalent of 12 months' retail experience, "
        "exercises some responsibility for stock control, cash reconciliation, or the "
        "supervision of one or more Level 1 or Level 2 employees on a shift."
    ),
    "Level 4": (
        "An employee who supervises the work of other employees, has full responsibility "
        "for a section or department, or holds a trade qualification relevant to their "
        "duties."
    ),
}


def format_classifications_for_prompt() -> str:
    return "\n\n".join(f"{level}: {desc}" for level, desc in CLASSIFICATION_LEVELS.items())