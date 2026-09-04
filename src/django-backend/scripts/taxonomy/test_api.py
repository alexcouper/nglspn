import json
from urllib.parse import unquote

import pytest

from scripts.taxonomy.api import ApiError, fetch_snapshot

API = "https://example.test/api"


class FakeApi:
    """Serves the handful of endpoints the snapshot walks."""

    def __init__(self, categories=(), projects=(), page_size=100):
        self.categories = list(categories)
        self.projects = list(projects)
        self.page_size = page_size
        self.calls = []

    def __call__(self, url):
        self.calls.append(url)
        path = unquote(url[len(API) :])
        if path == "/projects/categories":
            return [
                {
                    "id": f"cat-{c['slug']}",
                    **{k: c[k] for k in ("name", "slug")},
                    "project_count": len(self._in_category(c["slug"])),
                }
                for c in self.categories
            ]
        if path.startswith("/projects/by-category/"):
            slug = path.rsplit("/", 1)[1]
            return [
                {
                    "id": p["id"],
                    "slug": p["slug"],
                    "title": p["title"],
                    "tagline": p.get("tagline", ""),
                    "category_slug": slug,
                }
                for p in self._in_category(slug)
            ]
        if path.startswith("/projects?"):
            return self._page(int(path.split("page=")[1].split("&")[0]))
        if path.startswith("/projects/"):
            return self._detail(path.rsplit("/", 1)[1])
        msg = f"unexpected request: {url}"
        raise AssertionError(msg)

    def _in_category(self, slug):
        return [p for p in self.projects if p.get("category") == slug]

    def _page(self, page):
        start = (page - 1) * self.page_size
        window = self.projects[start : start + self.page_size]
        pages = max(1, -(-len(self.projects) // self.page_size))
        return {
            "projects": [
                {"id": p["id"], "slug": p["slug"], "title": p["title"]} for p in window
            ],
            "total": len(self.projects),
            "page": page,
            "per_page": self.page_size,
            "pages": pages,
        }

    def _detail(self, identifier):
        for project in self.projects:
            if identifier in {project["id"], project["slug"]}:
                return {
                    "id": project["id"],
                    "slug": project["slug"],
                    "title": project["title"],
                    "tagline": project.get("tagline", ""),
                    "description": project.get("description", ""),
                    "long_description": None,
                    "website_url": project.get("website_url", ""),
                    "github_url": None,
                    "tech_stack": project.get("tech_stack", []),
                    "status": "approved",
                    "tags": [{"name": name} for name in project.get("tags", [])],
                }
        msg = f"no project {identifier}"
        raise AssertionError(msg)


def project(id_, title, **kwargs):
    return {
        "id": id_,
        "slug": kwargs.pop("slug", title.lower()),
        "title": title,
        **kwargs,
    }


def rows_by_title(snapshot):
    return {row["title"]: row for row in snapshot["projects"]}


def test_project_carries_the_category_it_is_filed_under():
    api = FakeApi(
        categories=[{"name": "Dev Tools", "slug": "dev-tools"}],
        projects=[project("1", "Grep", category="dev-tools", tags=["cli"])],
    )

    row = rows_by_title(fetch_snapshot(API, fetch=api))["Grep"]

    assert row["current_category_slug"] == "dev-tools"
    assert row["current_category_name"] == "Dev Tools"
    assert row["tags"] == ["cli"]


def test_uncategorised_project_is_reported_as_such():
    api = FakeApi(projects=[project("1", "Homeless")])

    snapshot = fetch_snapshot(API, fetch=api)

    assert snapshot["projects"][0]["current_category_slug"] is None
    assert snapshot["current_categories"] == [
        {"slug": None, "name": "(uncategorised)", "project_count": 1}
    ]


def test_counts_categories_from_the_projects_actually_returned():
    api = FakeApi(
        categories=[
            {"name": "Apps", "slug": "apps"},
            {"name": "Tools", "slug": "tools"},
        ],
        projects=[
            project("1", "One", category="apps"),
            project("2", "Two", category="apps"),
        ],
    )

    assert fetch_snapshot(API, fetch=api)["current_categories"] == [
        {"slug": "apps", "name": "Apps", "project_count": 2},
        {"slug": "tools", "name": "Tools", "project_count": 0},
    ]


def test_walks_every_page_of_the_project_list():
    api = FakeApi(
        projects=[project(str(n), f"Project {n:02d}") for n in range(25)],
        page_size=10,
    )

    snapshot = fetch_snapshot(API, fetch=api)

    assert snapshot["project_count"] == 25


def test_fetches_detail_by_id_when_a_project_has_no_slug():
    api = FakeApi(projects=[project("abc-123", "Sluggless", slug=None)])

    fetch_snapshot(API, fetch=api)

    assert f"{API}/projects/abc-123" in api.calls


def test_description_reaches_the_snapshot():
    api = FakeApi(
        projects=[project("1", "Smakk", description="Wine discovery for consumers.")]
    )

    row = rows_by_title(fetch_snapshot(API, fetch=api))["Smakk"]

    assert row["description"] == "Wine discovery for consumers."


def test_snapshot_records_the_api_it_came_from():
    api = FakeApi(projects=[project("1", "One")])

    snapshot = fetch_snapshot(f"{API}/", fetch=api)

    assert snapshot["source"]["api_url"] == API


def test_snapshot_is_json_serialisable():
    api = FakeApi(projects=[project("1", "One")])

    json.dumps(fetch_snapshot(API, fetch=api))


def test_api_errors_surface_as_api_error():
    def explode(url):
        msg = f"{url} returned HTTP 502"
        raise ApiError(msg)

    with pytest.raises(ApiError):
        fetch_snapshot(API, fetch=explode)
