"""Flask server: serves the page shells and the JSON API.

Runs are executed in background threads; progress is polled via /api/status.
Results are persisted per participant name under runs/ so people can leave and
return to the same data by re-entering their name.
"""

from __future__ import annotations

import json
import re
import threading
import uuid
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request

from app import data, runner

app = Flask(__name__)

RUNS_DIR = Path(__file__).resolve().parent.parent / "runs"
RUNS_DIR.mkdir(exist_ok=True)

# job_id -> {status, total, completed, result, error}
_JOBS: dict[str, dict] = {}
_JOBS_LOCK = threading.Lock()


# --------------------------------------------------------------------------- #
# Persistence
# --------------------------------------------------------------------------- #
def _safe_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "anon"


def _result_path(name: str, activity: str) -> Path:
    return RUNS_DIR / f"{_safe_name(name)}__{activity}.json"


def _save_result(name: str, activity: str, result: dict) -> None:
    _result_path(name, activity).write_text(json.dumps(result), encoding="utf-8")


def _load_result(name: str, activity: str) -> dict | None:
    path = _result_path(name, activity)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


# --------------------------------------------------------------------------- #
# Page routes (static shells; the frontend agent owns the templates)
# --------------------------------------------------------------------------- #
@app.get("/")
def page_name():
    return render_template("name.html")


@app.get("/home")
def page_home():
    return render_template("home.html")


@app.get("/preprocess")
def page_preprocess():
    return render_template("preprocess.html")


@app.get("/analysis")
def page_analysis():
    return render_template("analysis.html")


@app.get("/syllabi")
def page_syllabi():
    return render_template("syllabi.html")


@app.get("/syllabus/<syllabus_id>")
def page_syllabus(syllabus_id: str):
    return render_template("syllabus.html")


@app.get("/transcripts")
def page_transcripts():
    return render_template("transcripts.html")


@app.get("/transcript/<transcript_id>")
def page_transcript(transcript_id: str):
    return render_template("transcript.html")


# --------------------------------------------------------------------------- #
# Data API
# --------------------------------------------------------------------------- #
@app.get("/api/system_prompt")
def api_system_prompt():
    activity = request.args.get("activity", "preprocess")
    output_type = request.args.get("output_type", "boolean")
    return jsonify({"system_prompt": runner.system_prompt(activity, output_type)})


@app.get("/api/syllabi")
def api_syllabi():
    return jsonify({"items": data.syllabi_index()})


@app.get("/api/syllabi/<syllabus_id>")
def api_syllabus(syllabus_id: str):
    detail = data.syllabus_detail(syllabus_id)
    if detail is None:
        abort(404)
    return jsonify(detail)


@app.get("/api/transcripts")
def api_transcripts():
    return jsonify({"items": data.transcripts_index()})


@app.get("/api/transcripts/<transcript_id>")
def api_transcript(transcript_id: str):
    detail = data.transcript_detail(transcript_id)
    if detail is None:
        abort(404)
    return jsonify(detail)


# --------------------------------------------------------------------------- #
# Run API
# --------------------------------------------------------------------------- #
@app.post("/api/run")
def api_run():
    body = request.get_json(force=True, silent=True) or {}
    name = (body.get("name") or "").strip()
    activity = body.get("activity")
    user_prompt = (body.get("user_prompt") or "").strip()
    output_type = body.get("output_type", "boolean")

    if not name:
        return jsonify({"error": "name required"}), 400
    if activity not in ("preprocess", "analysis"):
        return jsonify({"error": "invalid activity"}), 400
    if not user_prompt:
        return jsonify({"error": "prompt required"}), 400

    total = len(data.syllabi_index()) if activity == "preprocess" else len(data.transcripts_index())
    job_id = uuid.uuid4().hex
    with _JOBS_LOCK:
        _JOBS[job_id] = {
            "status": "running",
            "total": total,
            "completed": 0,
            "result": None,
            "error": None,
        }

    thread = threading.Thread(
        target=_run_job,
        args=(job_id, name, activity, user_prompt, output_type),
        daemon=True,
    )
    thread.start()
    return jsonify({"job_id": job_id})


def _run_job(job_id: str, name: str, activity: str, user_prompt: str, output_type: str) -> None:
    def progress():
        with _JOBS_LOCK:
            _JOBS[job_id]["completed"] += 1

    try:
        if activity == "preprocess":
            result = runner.run_preprocess(user_prompt, output_type, progress)
        else:
            result = runner.run_analysis(user_prompt, progress)
        _save_result(name, activity, result)
        with _JOBS_LOCK:
            _JOBS[job_id]["status"] = "done"
            _JOBS[job_id]["result"] = result
    except Exception as exc:  # noqa: BLE001
        with _JOBS_LOCK:
            _JOBS[job_id]["status"] = "error"
            _JOBS[job_id]["error"] = str(exc)


@app.get("/api/status/<job_id>")
def api_status(job_id: str):
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            abort(404)
        payload = {
            "status": job["status"],
            "total": job["total"],
            "completed": job["completed"],
        }
        if job["status"] == "done":
            payload["result"] = job["result"]
        elif job["status"] == "error":
            payload["error"] = job["error"]
    return jsonify(payload)


@app.get("/api/result")
def api_result():
    name = request.args.get("name", "")
    activity = request.args.get("activity", "")
    if not name or activity not in ("preprocess", "analysis"):
        return jsonify({"result": None})
    return jsonify({"result": _load_result(name, activity)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
