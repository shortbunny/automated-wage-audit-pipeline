"""
rules.py

The award's pay rules, written directly as code. No AI here on purpose:
this is the part that has to be 100% correct and explainable every time,
so it's just the rules from the award document turned into numbers and
simple logic.

(Rates match the same synthetic demo award used in the earlier RAG project.)
"""

# Minimum weekly rate per classification level (Clause 18)
WEEKLY_RATES = {
    "Level 1": 915.40,
    "Level 2": 945.20,
    "Level 3": 985.70,
    "Level 4": 1032.10,
}

STANDARD_WEEKLY_HOURS = 38
CASUAL_LOADING = 0.25          # Clause 22.2
SATURDAY_PENALTY = 1.25        # Clause 27.2
SUNDAY_PENALTY_PERMANENT = 1.50   # Clause 27.3
SUNDAY_PENALTY_CASUAL = 1.75      # Clause 27.3 (inclusive of loading)
PUBLIC_HOLIDAY_PERMANENT = 2.25   # Clause 27.4
PUBLIC_HOLIDAY_CASUAL = 2.50      # Clause 27.4 (inclusive of loading)
OVERTIME_FIRST_3H = 1.50       # Clause 31.2
OVERTIME_AFTER_3H = 2.00       # Clause 31.2
OVERTIME_THRESHOLD_DAILY = 7.6  # ordinary hours in a single day before overtime kicks in


def base_hourly_rate(classification: str) -> float:
    """Clause 18.2 — weekly rate divided by 38."""
    return WEEKLY_RATES[classification] / STANDARD_WEEKLY_HOURS


def expected_pay_for_shift(classification: str, employment_type: str,
                            day_type: str, hours: float) -> tuple[float, list[str]]:
    """
    Work out what a shift SHOULD have been paid, and which clauses applied.

    day_type: "weekday", "saturday", "sunday", or "public_holiday"
    employment_type: "casual" or "permanent"

    Overtime (hours beyond the daily threshold) is paid at the overtime
    rate regardless of day type, applied on top of ordinary hours at the
    normal rate for that day.
    """
    base = base_hourly_rate(classification)
    clauses_used = ["18"]

    ordinary_hours = min(hours, OVERTIME_THRESHOLD_DAILY)
    overtime_hours = max(0.0, hours - OVERTIME_THRESHOLD_DAILY)

    # Ordinary-hours rate depends on day type + employment type
    if day_type == "weekday":
        rate = base
        if employment_type == "casual":
            rate *= (1 + CASUAL_LOADING)
            clauses_used.append("22")
    elif day_type == "saturday":
        rate = base * SATURDAY_PENALTY
        if employment_type == "casual":
            rate *= (1 + CASUAL_LOADING)
            clauses_used.append("22")
        clauses_used.append("27")
    elif day_type == "sunday":
        rate = base * (SUNDAY_PENALTY_CASUAL if employment_type == "casual" else SUNDAY_PENALTY_PERMANENT)
        clauses_used.append("27")
    elif day_type == "public_holiday":
        rate = base * (PUBLIC_HOLIDAY_CASUAL if employment_type == "casual" else PUBLIC_HOLIDAY_PERMANENT)
        clauses_used.append("27")
    else:
        raise ValueError(f"Unknown day_type: {day_type}")

    ordinary_pay = ordinary_hours * rate

    # Overtime: base rate x overtime multiplier, no casual loading (Clause 31.3)
    overtime_pay = 0.0
    if overtime_hours > 0:
        clauses_used.append("31")
        first_3h = min(overtime_hours, 3)
        after_3h = max(0.0, overtime_hours - 3)
        overtime_pay = first_3h * base * OVERTIME_FIRST_3H + after_3h * base * OVERTIME_AFTER_3H

    total = round(ordinary_pay + overtime_pay, 2)
    return total, sorted(set(clauses_used))