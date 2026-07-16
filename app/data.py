"""Data access for the workshop app.

Loads the OCW syllabi (Preprocessing activity) and the TalkMoves transcripts
(Analysis activity), taking a deterministic seeded sample of each so every
participant sees the same 50 syllabi / 30 transcripts.
"""

from __future__ import annotations

import csv
import functools
import random
import re
from pathlib import Path

import markdown as md

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = REPO_ROOT / "data"
SYLLABI_DIR = DATA_ROOT / "ocw" / "ocw_subset" / "syllabi"
MANIFEST_CSV = DATA_ROOT / "ocw" / "ocw_subset" / "manifest.csv"
TALKMOVES_CSV = DATA_ROOT / "talkmoves.csv"

N_SYLLABI = 50
N_TRANSCRIPTS = 30
SEED = 42

# Bump the CSV field-size limit: some transcript sentences are long.
csv.field_size_limit(10_000_000)


# --------------------------------------------------------------------------- #
# Syllabi
# --------------------------------------------------------------------------- #
def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


@functools.lru_cache(maxsize=1)
def _manifest() -> dict[str, dict[str, str]]:
    """repo_name -> manifest row (title, course number, year, ...)."""
    if not MANIFEST_CSV.exists():
        return {}
    with MANIFEST_CSV.open(newline="") as f:
        return {row["repo_name"]: row for row in csv.DictReader(f)}


@functools.lru_cache(maxsize=1)
def _syllabi() -> dict[str, dict]:
    """id -> {id, title, course_number, year, path}. Seeded sample of N_SYLLABI."""
    paths = sorted(SYLLABI_DIR.glob("*.md"))
    rng = random.Random(SEED)
    chosen = rng.sample(paths, k=min(N_SYLLABI, len(paths)))
    chosen.sort(key=lambda p: p.stem)

    manifest = _manifest()
    out: dict[str, dict] = {}
    for path in chosen:
        repo = path.stem
        meta = manifest.get(repo, {})
        out[repo] = {
            "id": repo,
            "title": meta.get("course_title") or repo,
            "course_number": meta.get("course_number") or "",
            "year": meta.get("year") or "",
            "path": path,
        }
    return out


def syllabi_index() -> list[dict]:
    return [
        {
            "id": s["id"],
            "title": s["title"],
            "course_number": s["course_number"],
            "year": s["year"],
        }
        for s in _syllabi().values()
    ]


def syllabus_text(syllabus_id: str) -> str | None:
    s = _syllabi().get(syllabus_id)
    if s is None:
        return None
    return s["path"].read_text(encoding="utf-8")


def syllabus_detail(syllabus_id: str) -> dict | None:
    s = _syllabi().get(syllabus_id)
    if s is None:
        return None
    raw = s["path"].read_text(encoding="utf-8")
    body = _strip_frontmatter(raw)
    html = md.markdown(body, extensions=["tables", "fenced_code"])
    return {"id": s["id"], "title": s["title"], "html": html}


def _strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].lstrip()
    return text


def all_syllabi_for_run() -> list[dict]:
    """[{id, title, text}] over the sampled syllabi, for the LLM runner."""
    return [
        {"id": s["id"], "title": s["title"], "text": s["path"].read_text(encoding="utf-8")}
        for s in _syllabi().values()
    ]


# --------------------------------------------------------------------------- #
# Transcripts
# --------------------------------------------------------------------------- #
@functools.lru_cache(maxsize=1)
def _transcripts() -> dict[str, dict]:
    """id -> {id, name, utterances:[{turn, speaker, text}]}. Seeded sample."""
    grouped: dict[str, list[dict]] = {}
    order: list[str] = []
    with TALKMOVES_CSV.open(newline="") as f:
        for row in csv.DictReader(f):
            name = row["Transcript"]
            if name not in grouped:
                grouped[name] = []
                order.append(name)
            grouped[name].append(
                {
                    "turn": row["Turn"],
                    "speaker": row["Speaker"],
                    "text": row["Sentence"],
                }
            )

    rng = random.Random(SEED)
    chosen = rng.sample(order, k=min(N_TRANSCRIPTS, len(order)))
    chosen.sort()

    out: dict[str, dict] = {}
    for name in chosen:
        tid = _slug(name)
        out[tid] = {"id": tid, "name": name, "utterances": grouped[name]}
    return out


def transcripts_index() -> list[dict]:
    return [
        {"id": t["id"], "name": t["name"], "num_utterances": len(t["utterances"])}
        for t in _transcripts().values()
    ]


def transcript_detail(transcript_id: str) -> dict | None:
    return _transcripts().get(transcript_id)


def all_transcripts_for_run() -> list[dict]:
    """[{id, name, utterances}] over the sampled transcripts, for the runner."""
    return list(_transcripts().values())
