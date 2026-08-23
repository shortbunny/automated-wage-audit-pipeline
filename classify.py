"""
classify.py

Sends one job description through one of the three strategies and parses
the result into a consistent shape:

    {"predicted_level": "Level 2" or None,
     "confidence": "high"/"medium"/"low" or None,
     "flagged_for_review": bool,
     "raw": the model's raw response}

zero_shot and few_shot have no concept of confidence, so
flagged_for_review is always False for them — that's not a bug, it's the
finding: those two approaches are structurally incapable of saying "I'm
not sure," which is exactly why they need to be tested against ambiguous
cases, not just clear ones.

MOCK MODE: if --mock is used, no real API calls are made. A simple
keyword-based stand-in plays the role of "a naive classifier that always
guesses confidently." This exists ONLY to let you run the full pipeline
before wiring up a real API key — it is not a real evaluation of anything,
and the code says so loudly wherever it's used.
"""

import os
import json
import re

from dotenv import load_dotenv
from strategies import STRATEGIES, zero_shot_prompt, few_shot_prompt, structured_confidence_prompt

load_dotenv()  # reads GROQ_API_KEY from a local .env file, if present

VALID_LEVELS = {"Level 1", "Level 2", "Level 3", "Level 4"}


def _extract_level(text: str) -> str | None:
    match = re.search(r"Level [1-4]", text)
    return match.group(0) if match else None


def _mock_call(system: str, user: str) -> str:
    """A dumb keyword-based stand-in — NOT a real model. See module docstring."""
    text = user.lower()
    duty_keywords = ["manages", "department", "qualified", "schedules", "reconcil",
                      "supervis", "count", "reorder", "register", "customer",
                      "unsupervised", "on their own", "stack", "clean", "restock"]
    has_duty_info = any(kw in text for kw in duty_keywords)

    if "manages" in text or "department" in text or "qualified" in text or "schedules" in text:
        level = "Level 4"
    elif "reconcil" in text or "supervis" in text or "count" in text or "reorder" in text:
        level = "Level 3"
    elif "register" in text or "customer" in text or "unsupervised" in text or "on their own" in text:
        level = "Level 2"
    elif has_duty_info:
        level = "Level 1"
    else:
        level = None  # no duty information at all — e.g. a bare job title

    if '"flag_for_review"' in system:
        return json.dumps({
            "level": level,
            "confidence": "medium" if level else "low",
            "reasoning": "(mock) keyword match" if level else "(mock) no duty information found",
            "flag_for_review": level is None,
        })
    return level or "Level 1"  # zero_shot/few_shot have no way to abstain, so mock still guesses


def _real_call(client, system: str, user: str, model: str = "openai/gpt-oss-120b") -> str:
    response = client.chat.completions.create(
        model=model,
        max_tokens=300,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content


def classify(job_description: str, strategy: str, client=None, mock: bool = False) -> dict:
    if strategy not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {strategy}")

    prompt = STRATEGIES[strategy](job_description)

    if mock:
        raw = _mock_call(prompt["system"], prompt["user"])
    else:
        raw = _real_call(client, prompt["system"], prompt["user"])

    if strategy == "structured_confidence":
        try:
            parsed = json.loads(raw.strip())
            level = parsed.get("level")
            level = level if level in VALID_LEVELS else None
            return {
                "predicted_level": level,
                "confidence": parsed.get("confidence"),
                "flagged_for_review": bool(parsed.get("flag_for_review", False)) or level is None,
                "raw": raw,
            }
        except (json.JSONDecodeError, AttributeError):
            # Model didn't return valid JSON — treat as a failure to classify,
            # not as a guess. This itself is a reliability data point worth tracking.
            return {"predicted_level": None, "confidence": None, "flagged_for_review": True, "raw": raw}

    # zero_shot / few_shot: plain text, no way to express uncertainty
    level = _extract_level(raw)
    return {"predicted_level": level, "confidence": None, "flagged_for_review": False, "raw": raw}


def get_client(mock: bool):
    if mock:
        return None
    import groq
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise SystemExit("GROQ_API_KEY not set. Use --mock to test the pipeline without a real API key.")
    return groq.Groq(api_key=api_key)