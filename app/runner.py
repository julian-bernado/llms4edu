"""LLM runner + result computation for both activities.

Uses the `inference` package (OpenRouter, gpt-oss-120b pinned to Cerebras).
Preprocessing: one call per syllabus -> boolean or number. Analysis: one call
per transcript -> list of matching utterances with context.
"""

from __future__ import annotations

import json
import os
import random
import re
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from inference import Prompt, llm

from app import data

MODEL_NAME = "openrouter_gpt_5_4_nano"
MAX_WORKERS = 8
MAX_RETRIES = 3

# Global cap on concurrent LLM calls across ALL participants' runs at once, so 12
# simultaneous runs don't multiply into a rate-limit storm. Tune via env.
GLOBAL_MAX_CONCURRENCY = int(os.environ.get("LLMS4EDU_MAX_CONCURRENCY", "24"))
_LLM_GATE = threading.BoundedSemaphore(GLOBAL_MAX_CONCURRENCY)

# Fake-LLM mode for load testing: skip real network calls, return canned answers
# with realistic latency. Enable with LLMS4EDU_FAKE_LLM=1.
FAKE_LLM = os.environ.get("LLMS4EDU_FAKE_LLM") == "1"

# --------------------------------------------------------------------------- #
# System prompts (shown greyed-out in the UI; used verbatim by the runner)
# --------------------------------------------------------------------------- #
SYSTEM_PREPROCESS_BOOLEAN = """\
You are a careful research assistant analyzing university course syllabi.
These syllabi come from MIT Open Courseware and have inconsistent formats.
You will be given the full text of ONE syllabus and a QUESTION from the researcher.
Answer the question for THIS syllabus only, based solely on its text.
Respond with exactly one word on a single line: TRUE or FALSE. Do not explain."""

SYSTEM_PREPROCESS_NUMBER = """\
You are a careful research assistant analyzing university course syllabi.
These syllabi come from MIT Open Courseware and have inconsistent formats.
You will be given the full text of ONE syllabus and a QUESTION from the researcher
that asks for a numeric value. Answer for THIS syllabus only, based solely on its text.
Respond with exactly one number on a single line and nothing else. If the value cannot
be determined from the syllabus, respond with the single word: UNKNOWN."""

SYSTEM_ANALYSIS = """\
You are a careful research assistant analyzing classroom discussion transcripts.
You will be given a full transcript. Each line is formatted as:
  [turn <N> | T or S] <utterance text>
where <N> is the turn number, T marks a teacher turn and S a student turn.
You are also given a DESCRIPTION of a kind of utterance the researcher is looking for.
Identify every utterance in the transcript that matches the description.
Respond ONLY with a JSON array. Each element is an object with keys:
  "turn"      - the turn number (the <N> value) where the utterance occurs
  "speaker"   - "T" or "S"
  "utterance" - the exact matching utterance text
  "context"   - a brief note on the surrounding context (one sentence)
If no utterance matches, respond with an empty array: []
Do not include any text outside the JSON array."""


def system_prompt(activity: str, output_type: str | None = None) -> str:
    if activity == "analysis":
        return SYSTEM_ANALYSIS
    if output_type == "number":
        return SYSTEM_PREPROCESS_NUMBER
    return SYSTEM_PREPROCESS_BOOLEAN


# --------------------------------------------------------------------------- #
# Low-level call with retry
# --------------------------------------------------------------------------- #
def _ask(model, system: str, user: str) -> str:
    if FAKE_LLM:
        return _fake_ask(system)
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            with _LLM_GATE:
                resp = model.ask(Prompt(system_prompt=system, model_prompt=user))
            return str(resp).strip()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            time.sleep(0.5 * (2**attempt) + random.random() * 0.4)
    raise last_exc  # type: ignore[misc]


def _fake_ask(system: str) -> str:
    """Canned response with realistic latency, for load testing the server."""
    with _LLM_GATE:
        time.sleep(random.uniform(0.3, 1.5))
    if "TRUE or FALSE" in system:
        return random.choice(["TRUE", "FALSE"])
    if "UNKNOWN" in system:
        return str(random.randint(1, 40))
    # analysis: sometimes a match, sometimes none
    if random.random() < 0.4:
        return '[{"turn": 5, "speaker": "T", "utterance": "load test", "context": "n/a"}]'
    return "[]"


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #
def _parse_boolean(text: str) -> bool | None:
    t = text.strip().lower().strip('".,!')
    # look at the last non-empty line to skip any stray reasoning
    for line in reversed(text.strip().splitlines()):
        w = line.strip().lower().strip('".,!*`')
        if w in ("true", "yes"):
            return True
        if w in ("false", "no"):
            return False
    if "true" in t and "false" not in t:
        return True
    if "false" in t and "true" not in t:
        return False
    return None


def _parse_number(text: str) -> float | None:
    if "unknown" in text.lower():
        return None
    matches = re.findall(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    if not matches:
        return None
    val = float(matches[-1])
    return int(val) if val.is_integer() else val


def _parse_matches(text: str) -> list[dict]:
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end < start:
        return []
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return []
    out: list[dict] = []
    if isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, dict) and item.get("utterance"):
                out.append(
                    {
                        "turn": item.get("turn"),
                        "speaker": str(item.get("speaker", "")),
                        "utterance": str(item.get("utterance", "")),
                        "context": str(item.get("context", "")),
                    }
                )
    return out


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _resolve_turns(matches: list[dict], utterances: list[dict]) -> list[dict]:
    """Correct each match's turn by locating its utterance text in the transcript.

    Falls back to the model-reported turn (coerced to str) when no text match is
    found, and to None if neither is available.
    """
    exact: dict[str, str] = {}
    normed: list[tuple[str, str]] = []
    for u in utterances:
        key = _normalize(u["text"])
        if key:
            exact.setdefault(key, u["turn"])
            normed.append((key, u["turn"]))

    for m in matches:
        key = _normalize(m["utterance"])
        turn = exact.get(key)
        if turn is None and key:
            # substring match either direction (model may trim/expand slightly)
            for utext, uturn in normed:
                if key in utext or utext in key:
                    turn = uturn
                    break
        if turn is None and m.get("turn") is not None:
            turn = str(m["turn"])
        m["turn"] = turn
    return matches


# --------------------------------------------------------------------------- #
# Prompt bodies
# --------------------------------------------------------------------------- #
def _syllabus_user_prompt(user_prompt: str, title: str, text: str) -> str:
    return (
        f"QUESTION: {user_prompt}\n\n"
        f"SYLLABUS ({title}):\n"
        f"----------------------------------------\n"
        f"{text}\n"
        f"----------------------------------------"
    )


def _transcript_user_prompt(user_prompt: str, name: str, utterances: list[dict]) -> str:
    lines = [f"[turn {u['turn']} | {u['speaker']}] {u['text']}" for u in utterances]
    body = "\n".join(lines)
    return (
        f"DESCRIPTION: {user_prompt}\n\n"
        f"TRANSCRIPT ({name}):\n"
        f"----------------------------------------\n"
        f"{body}\n"
        f"----------------------------------------"
    )


# --------------------------------------------------------------------------- #
# Runs. progress_cb() is called once per completed item.
# --------------------------------------------------------------------------- #
def run_preprocess(user_prompt: str, output_type: str, progress_cb) -> dict:
    model = llm.from_name(MODEL_NAME)
    system = system_prompt("preprocess", output_type)
    syllabi = data.all_syllabi_for_run()

    def one(s: dict) -> dict:
        try:
            raw = _ask(model, system, _syllabus_user_prompt(user_prompt, s["title"], s["text"]))
            value = _parse_boolean(raw) if output_type == "boolean" else _parse_number(raw)
        except Exception:  # noqa: BLE001
            value = None
        return {"id": s["id"], "title": s["title"], "value": value}

    items = _run_pool(syllabi, one, progress_cb)
    # stable order matching the sampled index
    order = {s["id"]: i for i, s in enumerate(syllabi)}
    items.sort(key=lambda it: order[it["id"]])

    summary = _summarize_boolean(items) if output_type == "boolean" else _summarize_number(items)
    return {
        "activity": "preprocess",
        "output_type": output_type,
        "user_prompt": user_prompt,
        "items": items,
        "summary": summary,
    }


def run_analysis(user_prompt: str, progress_cb) -> dict:
    model = llm.from_name(MODEL_NAME)
    system = system_prompt("analysis")
    transcripts = data.all_transcripts_for_run()

    def one(t: dict) -> dict:
        try:
            raw = _ask(
                model, system, _transcript_user_prompt(user_prompt, t["name"], t["utterances"])
            )
            matches = _resolve_turns(_parse_matches(raw), t["utterances"])
        except Exception:  # noqa: BLE001
            matches = []
        return {"id": t["id"], "name": t["name"], "matches": matches}

    results = _run_pool(transcripts, one, progress_cb)
    order = {t["id"]: i for i, t in enumerate(transcripts)}
    results.sort(key=lambda r: order[r["id"]])
    total = sum(len(r["matches"]) for r in results)
    return {
        "activity": "analysis",
        "user_prompt": user_prompt,
        "transcripts": results,
        "total_matches": total,
    }


def _run_pool(inputs: list[dict], fn, progress_cb) -> list[dict]:
    out: list[dict] = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(fn, x) for x in inputs]
        for fut in as_completed(futures):
            out.append(fut.result())
            progress_cb()
    return out


# --------------------------------------------------------------------------- #
# Summaries
# --------------------------------------------------------------------------- #
def _summarize_boolean(items: list[dict]) -> dict:
    true_count = sum(1 for it in items if it["value"] is True)
    false_count = sum(1 for it in items if it["value"] is False)
    null_count = sum(1 for it in items if it["value"] is None)
    return {"true_count": true_count, "false_count": false_count, "null_count": null_count}


def _summarize_number(items: list[dict]) -> dict:
    values = [float(it["value"]) for it in items if isinstance(it["value"], (int, float))]
    null_count = sum(1 for it in items if not isinstance(it["value"], (int, float)))
    if not values:
        return {
            "count": 0,
            "min": None,
            "q1": None,
            "median": None,
            "q3": None,
            "max": None,
            "mean": None,
            "values": [],
            "null_count": null_count,
        }
    q1, median, q3 = _quartiles(values)
    return {
        "count": len(values),
        "min": min(values),
        "q1": q1,
        "median": median,
        "q3": q3,
        "max": max(values),
        "mean": statistics.fmean(values),
        "values": values,
        "null_count": null_count,
    }


def _quartiles(values: list[float]) -> tuple[float, float, float]:
    s = sorted(values)
    median = statistics.median(s)
    if len(s) < 2:
        return s[0], median, s[0]
    mid = len(s) // 2
    lower = s[:mid]
    upper = s[mid + 1 :] if len(s) % 2 else s[mid:]
    q1 = statistics.median(lower) if lower else median
    q3 = statistics.median(upper) if upper else median
    return q1, median, q3
