"""Build the taxonomy snapshot from the public API.

Everything a taxonomy pass needs is public: `/projects` enumerates the approved
projects, `/projects/by-category/{slug}` says which category each one is in
today, and `/projects/{identifier}` carries the copy you have to read to place
it. No database access, so this runs against localhost or production alike.

Standard library only — `python3 -m scripts.taxonomy` works without the Django
environment.
"""

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

DEFAULT_API_URL = "http://localhost:8000/api"
PAGE_SIZE = 100
TIMEOUT_SECONDS = 30

Fetch = Callable[[str], Any]


class ApiError(RuntimeError):
    pass


def fetch_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        msg = f"{url} returned HTTP {exc.code}"
        raise ApiError(msg) from exc
    except urllib.error.URLError as exc:
        msg = f"Could not reach {url}: {exc.reason}"
        raise ApiError(msg) from exc
    except json.JSONDecodeError as exc:
        msg = f"{url} did not return JSON: {exc}"
        raise ApiError(msg) from exc


def _categories(api_url: str, fetch: Fetch) -> list[dict[str, Any]]:
    return fetch(f"{api_url}/projects/categories")


def _category_membership(
    api_url: str, categories: list[dict[str, Any]], fetch: Fetch
) -> dict[str, dict[str, str]]:
    """Map project id -> the category it is filed under today."""
    membership: dict[str, dict[str, str]] = {}
    for category in categories:
        slug = urllib.parse.quote(str(category["slug"]))
        for project in fetch(f"{api_url}/projects/by-category/{slug}"):
            membership[str(project["id"])] = {
                "slug": category["slug"],
                "name": category["name"],
            }
    return membership


def _approved_projects(api_url: str, fetch: Fetch) -> list[dict[str, Any]]:
    projects: list[dict[str, Any]] = []
    page = 1
    while True:
        payload = fetch(f"{api_url}/projects?page={page}&per_page={PAGE_SIZE}")
        projects.extend(payload["projects"])
        if page >= payload.get("pages", 1):
            return projects
        page += 1


def _detail(api_url: str, listed: dict[str, Any], fetch: Fetch) -> dict[str, Any]:
    identifier = urllib.parse.quote(str(listed.get("slug") or listed["id"]))
    return fetch(f"{api_url}/projects/{identifier}")


def _project_row(
    detail: dict[str, Any], category: dict[str, str] | None
) -> dict[str, Any]:
    return {
        "id": str(detail["id"]),
        "slug": detail.get("slug"),
        "title": detail["title"],
        "tagline": detail.get("tagline", ""),
        "description": detail.get("description", ""),
        "long_description": detail.get("long_description") or "",
        "website_url": detail.get("website_url", ""),
        "github_url": detail.get("github_url"),
        "tech_stack": detail.get("tech_stack", []),
        "tags": sorted(tag["name"] for tag in detail.get("tags", [])),
        "status": detail.get("status", ""),
        "current_category_slug": category["slug"] if category else None,
        "current_category_name": category["name"] if category else None,
    }


def _current_categories(
    categories: list[dict[str, Any]], rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    counts: dict[str | None, int] = {}
    for row in rows:
        slug = row["current_category_slug"]
        counts[slug] = counts.get(slug, 0) + 1
    listed = [
        {
            "slug": category["slug"],
            "name": category["name"],
            "project_count": counts.get(category["slug"], 0),
        }
        for category in categories
    ]
    if None in counts:
        listed.append(
            {"slug": None, "name": "(uncategorised)", "project_count": counts[None]}
        )
    return listed


def fetch_snapshot(api_url: str, fetch: Fetch = fetch_json) -> dict[str, Any]:
    """The approved projects, their copy, and the category each is in today."""
    base = api_url.rstrip("/")
    categories = _categories(base, fetch)
    membership = _category_membership(base, categories, fetch)
    rows = [
        _project_row(_detail(base, listed, fetch), membership.get(str(listed["id"])))
        for listed in _approved_projects(base, fetch)
    ]
    rows.sort(key=lambda row: (row["title"].lower(), row["id"]))
    return {
        "source": {"api_url": base},
        "project_count": len(rows),
        "current_categories": _current_categories(categories, rows),
        "projects": rows,
    }
