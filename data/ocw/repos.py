from __future__ import annotations

import csv
import json
import os
import random
import time
from pathlib import Path
from typing import Any

import requests


ORG = "mitocwcontent"
API_ROOT = "https://api.github.com"
RAW_ROOT = "https://raw.githubusercontent.com"

OUTPUT_DIR = Path("ocw_subset")
METADATA_DIR = OUTPUT_DIR / "metadata"
SYLLABUS_DIR = OUTPUT_DIR / "syllabi"

# Optional. Authentication greatly increases GitHub API limits.
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "mit-ocw-course-sampler",
        }
    )

    if GITHUB_TOKEN:
        session.headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    return session


def list_repositories(session: requests.Session) -> list[dict[str, Any]]:
    """List every public repository in the OCW content organization."""
    repositories: list[dict[str, Any]] = []
    page = 1

    while True:
        response = session.get(
            f"{API_ROOT}/orgs/{ORG}/repos",
            params={
                "type": "public",
                "sort": "full_name",
                "direction": "asc",
                "per_page": 100,
                "page": page,
            },
            timeout=60,
        )
        response.raise_for_status()

        batch = response.json()
        if not batch:
            break

        repositories.extend(batch)
        page += 1

    return repositories


def download_raw_json(
    session: requests.Session,
    repo: dict[str, Any],
    path: str,
) -> dict[str, Any] | None:
    url = (
        f"{RAW_ROOT}/{ORG}/{repo['name']}/"
        f"{repo['default_branch']}/{path}"
    )

    response = session.get(url, timeout=60)

    if response.status_code == 404:
        return None

    response.raise_for_status()
    return response.json()


def download_raw_text(
    session: requests.Session,
    repo: dict[str, Any],
    path: str,
) -> str | None:
    url = (
        f"{RAW_ROOT}/{ORG}/{repo['name']}/"
        f"{repo['default_branch']}/{path}"
    )

    response = session.get(url, timeout=60)

    if response.status_code == 404:
        return None

    response.raise_for_status()
    return response.text


def metadata_matches(metadata: dict[str, Any]) -> bool:
    """
    Edit this function to define the sampling frame.

    Current example:
    - EECS, economics, mathematics, or management
    - 2005 onward
    - either undergraduate or graduate
    """
    departments = set(metadata.get("department_numbers", []))
    year = int(metadata.get("year", 0))

    target_departments = {"6", "14", "15", "18"}

    return bool(departments & target_departments) and year >= 2005


def main() -> None:
    random.seed(42)

    OUTPUT_DIR.mkdir(exist_ok=True)
    METADATA_DIR.mkdir(exist_ok=True)
    SYLLABUS_DIR.mkdir(exist_ok=True)

    session = make_session()
    repositories = list_repositories(session)

    # Exclude the OCW website repository and other non-course repositories.
    repositories = [
        repo
        for repo in repositories
        if repo["name"] != "ocw-www"
        and not repo["archived"]
    ]

    eligible: list[tuple[dict[str, Any], dict[str, Any]]] = []

    for index, repo in enumerate(repositories, start=1):
        metadata = download_raw_json(session, repo, "data/course.json")

        if metadata is None:
            continue

        if metadata_matches(metadata):
            eligible.append((repo, metadata))

        # Be polite to GitHub's raw-content service.
        if index % 100 == 0:
            time.sleep(1)

    # Replace this with the desired sample size.
    sample_size = min(100, len(eligible))
    selected = random.sample(eligible, k=sample_size)

    manifest_rows: list[dict[str, Any]] = []

    for repo, metadata in selected:
        syllabus = download_raw_text(
            session,
            repo,
            "content/pages/syllabus.md",
        )

        # Skip repositories without a conventional syllabus page.
        if syllabus is None:
            continue

        repo_name = repo["name"]

        metadata_path = METADATA_DIR / f"{repo_name}.json"
        metadata_path.write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8",
        )

        syllabus_path = SYLLABUS_DIR / f"{repo_name}.md"
        syllabus_path.write_text(syllabus, encoding="utf-8")

        manifest_rows.append(
            {
                "repo_name": repo_name,
                "course_number": metadata.get("primary_course_number"),
                "course_title": metadata.get("course_title"),
                "term": metadata.get("term"),
                "year": metadata.get("year"),
                "levels": "|".join(metadata.get("level", [])),
                "departments": "|".join(
                    metadata.get("department_numbers", [])
                ),
                "topics": json.dumps(metadata.get("topics", [])),
                "syllabus_words": len(syllabus.split()),
                "github_url": repo["html_url"],
            }
        )

    manifest_path = OUTPUT_DIR / "manifest.csv"

    with manifest_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(manifest_rows[0]),
        )
        writer.writeheader()
        writer.writerows(manifest_rows)

    print(f"Found {len(eligible)} eligible courses.")
    print(f"Downloaded {len(manifest_rows)} syllabi.")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
