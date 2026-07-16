"""Simulate N concurrent workshop participants against a running server.

Each simulated user submits a run and polls to completion, exactly like the
browser does. Reports per-user wall-clock, failures, and (for preprocess) how
many items came back null (parse misses).

Free plumbing test (no API cost) — start the server with a fake LLM:
    LLMS4EDU_FAKE_LLM=1 uv run flask --app app.server run --port 5000
    uv run python scripts/loadtest.py --users 12 --activity preprocess

Real end-to-end test (spends money, hits OpenRouter):
    OPENROUTER_API_KEY=... uv run flask --app app.server run --port 5000
    uv run python scripts/loadtest.py --users 12 --activity analysis --live
"""

from __future__ import annotations

import argparse
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from json import dumps, loads

PROMPTS = {
    "preprocess": "Does this syllabus list a required textbook?",
    "analysis": "Utterances where the teacher asks a student to explain their reasoning.",
}


def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=120) as r:
        return loads(r.read())


def _post(url: str, body: dict) -> dict:
    req = urllib.request.Request(
        url, data=dumps(body).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return loads(r.read())


def simulate_user(base: str, idx: int, activity: str, output_type: str) -> dict:
    name = f"loadtest-user-{idx:02d}"
    started = time.time()
    body = {"name": name, "activity": activity, "user_prompt": PROMPTS[activity]}
    if activity == "preprocess":
        body["output_type"] = output_type
    try:
        job = _post(f"{base}/api/run", body)
        job_id = job["job_id"]
    except Exception as exc:  # noqa: BLE001
        return {"idx": idx, "ok": False, "error": f"run: {exc}", "seconds": 0}

    while True:
        try:
            status = _get(f"{base}/api/status/{job_id}")
        except (urllib.error.URLError, TimeoutError) as exc:
            return {"idx": idx, "ok": False, "error": f"poll: {exc}", "seconds": time.time() - started}
        if status["status"] == "done":
            result = status["result"]
            nulls = None
            if activity == "preprocess":
                nulls = sum(1 for it in result["items"] if it["value"] is None)
            else:
                nulls = result["total_matches"]
            return {
                "idx": idx,
                "ok": True,
                "seconds": time.time() - started,
                "total": status["total"],
                "detail": nulls,
            }
        if status["status"] == "error":
            return {"idx": idx, "ok": False, "error": status.get("error"), "seconds": time.time() - started}
        time.sleep(0.5)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:5000")
    ap.add_argument("--users", type=int, default=12)
    ap.add_argument("--activity", choices=["preprocess", "analysis"], default="preprocess")
    ap.add_argument("--output-type", choices=["boolean", "number"], default="boolean")
    ap.add_argument("--live", action="store_true", help="just a label; server decides fake vs real")
    args = ap.parse_args()

    label = "LIVE (real OpenRouter)" if args.live else "server-controlled"
    print(f"Firing {args.users} concurrent users -> {args.activity} @ {args.base}  [{label}]\n")

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.users) as pool:
        futures = [
            pool.submit(simulate_user, args.base, i, args.activity, args.output_type)
            for i in range(args.users)
        ]
        results = [f.result() for f in as_completed(futures)]
    wall = time.time() - t0

    results.sort(key=lambda r: r["idx"])
    ok = [r for r in results if r["ok"]]
    bad = [r for r in results if not r["ok"]]
    for r in results:
        if r["ok"]:
            unit = "null-items" if args.activity == "preprocess" else "matches"
            print(f"  user {r['idx']:02d}: OK   {r['seconds']:6.1f}s   {r['detail']} {unit}")
        else:
            print(f"  user {r['idx']:02d}: FAIL {r['seconds']:6.1f}s   {r['error']}")

    print(f"\n{'='*52}")
    print(f"users: {args.users}   ok: {len(ok)}   failed: {len(bad)}")
    if ok:
        secs = [r["seconds"] for r in ok]
        print(f"per-user: min {min(secs):.1f}s  median {statistics.median(secs):.1f}s  max {max(secs):.1f}s")
    print(f"total wall clock: {wall:.1f}s")


if __name__ == "__main__":
    main()
