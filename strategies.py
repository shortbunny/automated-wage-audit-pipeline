"""
strategies.py

Three different ways to ask the model to do the same classification task.
The point of building three is that "does it work" isn't a useful question
for this kind of task — the useful question is "which approach is reliable
enough to trust, and what does it do when it's genuinely unsure?"

1. zero_shot       — just the rules and the job description. Simplest,
                      cheapest, and has NO way to express uncertainty.
2. few_shot        — same, plus a couple of worked examples. Usually more
                      accurate than zero-shot, but still can't say "unsure."
3. structured_conf — asks for a confidence level and an explicit
                      flag_for_review field. Costs a bit more in prompt
                      complexity, but is the only one of the three that can
                      admit it doesn't know — which matters a lot when a
                      wrong classification means a real underpayment claim.
"""

from classification import format_classifications_for_prompt

RULES_TEXT = format_classifications_for_prompt()

FEW_SHOT_EXAMPLES = """
Example 1:
Job description: "New starter, been here 3 weeks, restocks shelves and cleans under a supervisor's direct instruction."
Answer: Level 1

Example 2:
Job description: "Has completed training, runs the register and helps customers on their own, no one checking in."
Answer: Level 2

Example 3:
Job description: "Manages the entire electronics department, sets staff schedules, fully accountable for its performance."
Answer: Level 4
"""


def zero_shot_prompt(job_description: str) -> dict:
    system = (
        "You classify retail employees into one of four award levels based on their job "
        "description. Here are the four levels:\n\n"
        f"{RULES_TEXT}\n\n"
        "Respond with ONLY the level, e.g. 'Level 2'. No other text."
    )
    return {"system": system, "user": job_description}


def few_shot_prompt(job_description: str) -> dict:
    system = (
        "You classify retail employees into one of four award levels based on their job "
        "description. Here are the four levels:\n\n"
        f"{RULES_TEXT}\n\n"
        f"Here are some examples of how to classify:\n{FEW_SHOT_EXAMPLES}\n\n"
        "Respond with ONLY the level, e.g. 'Level 2'. No other text."
    )
    return {"system": system, "user": job_description}


def structured_confidence_prompt(job_description: str) -> dict:
    system = (
        "You classify retail employees into one of four award levels based on their job "
        "description. Here are the four levels:\n\n"
        f"{RULES_TEXT}\n\n"
        "Respond with ONLY a JSON object in this exact shape, no other text:\n"
        '{"level": "Level 2" or null, "confidence": "high" or "medium" or "low", '
        '"reasoning": "one sentence", "flag_for_review": true or false}\n\n'
        "Set flag_for_review to true, and level to null, if the job description does not "
        "give you enough information to confidently assign one specific level — for example "
        "if it's missing tenure/experience details, describes duties that span two levels, "
        "or is just a job title with no actual duties described. Do not guess when unsure — "
        "flagging for human review is the correct, safe answer in that case."
    )
    return {"system": system, "user": job_description}


STRATEGIES = {
    "zero_shot": zero_shot_prompt,
    "few_shot": few_shot_prompt,
    "structured_confidence": structured_confidence_prompt,
}