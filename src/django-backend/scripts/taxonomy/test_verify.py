import pytest

from scripts.taxonomy.verify import verify_report

CATEGORY = {
    "slug": "everything",
    "name": "Everything",
    "status": "new",
    "replaces": [],
    "rationale": "One bucket, for the sake of the test.",
    "future_example": "Anything at all.",
    "subcategories": [],
}


def snapshot_of(*projects):
    counts = {}
    for project in projects:
        slug = project["current_category_slug"]
        counts[slug] = counts.get(slug, 0) + 1
    return {
        "source": {"api_url": "https://example.test/api"},
        "project_count": len(projects),
        "current_categories": [
            {"slug": slug, "name": slug or "(uncategorised)", "project_count": count}
            for slug, count in counts.items()
        ],
        "projects": list(projects),
    }


def known_project(id_, title, category="apps"):
    return {"id": id_, "title": title, "current_category_slug": category}


def report_matching(snapshot, **overrides):
    report = {
        "generated_at": "2026-08-21",
        "source": {"api_url": snapshot["source"]["api_url"]},
        "current_categories": snapshot["current_categories"],
        "proposed_taxonomy": [CATEGORY],
        "projects": [
            {
                "id": project["id"],
                "title": project["title"],
                "current_category_slug": project["current_category_slug"],
                "proposed_category_slug": "everything",
                "proposed_subcategory_slug": None,
                "alternative_category_slug": None,
                "confidence": "high",
                "rationale": "It is a project.",
            }
            for project in snapshot["projects"]
        ],
        "unplaced": [],
    }
    return {**report, **overrides}


@pytest.fixture
def snapshot():
    return snapshot_of(
        known_project("1", "Keep"),
        known_project("2", "Smakk"),
        known_project("3", "Yrda", category="civic"),
    )


def assert_error_mentioning(result, fragment):
    assert not result.ok
    assert any(fragment in error for error in result.errors), result.errors


def assert_warning_mentioning(result, fragment):
    assert any(fragment in warning for warning in result.warnings), result.warnings


def test_accepts_a_report_that_matches_the_api(snapshot):
    assert verify_report(report_matching(snapshot), snapshot).ok


def test_rejects_a_report_that_omits_a_project(snapshot):
    report = report_matching(snapshot)
    report["projects"] = [e for e in report["projects"] if e["title"] != "Smakk"]

    assert_error_mentioning(
        verify_report(report, snapshot), "'Smakk') is missing from the report"
    )


def test_rejects_a_project_the_api_does_not_return(snapshot):
    report = report_matching(snapshot)
    report["projects"].append(
        {**report["projects"][0], "id": "999", "title": "Invented"}
    )

    assert_error_mentioning(
        verify_report(report, snapshot), "which the API does not return"
    )


def test_rejects_a_project_listed_twice(snapshot):
    report = report_matching(snapshot)
    report["projects"].append(dict(report["projects"][0]))

    assert_error_mentioning(verify_report(report, snapshot), "appears more than once")


def test_rejects_a_wrong_current_category(snapshot):
    report = report_matching(snapshot)
    report["projects"][0]["current_category_slug"] = "civic"

    assert_error_mentioning(verify_report(report, snapshot), "the API says 'apps'")


def test_rejects_a_retitled_project(snapshot):
    report = report_matching(snapshot)
    report["projects"][0]["title"] = "Something Else"

    assert_error_mentioning(verify_report(report, snapshot), "the API says 'Keep'")


def test_rejects_a_wrong_current_category_count(snapshot):
    report = report_matching(snapshot)
    report["current_categories"] = [
        {**row, "project_count": 99} for row in snapshot["current_categories"]
    ]

    assert_error_mentioning(verify_report(report, snapshot), "the API says 2")


def test_rejects_a_placement_into_an_undefined_category(snapshot):
    report = report_matching(snapshot)
    report["projects"][0]["proposed_category_slug"] = "imaginary"

    assert_error_mentioning(
        verify_report(report, snapshot), "undefined category 'imaginary'"
    )


def test_rejects_a_subcategory_from_another_parent(snapshot):
    report = report_matching(snapshot)
    report["proposed_taxonomy"] = [
        CATEGORY,
        {**CATEGORY, "slug": "elsewhere", "subcategories": [{"slug": "nested"}]},
    ]
    report["projects"][0]["proposed_subcategory_slug"] = "nested"

    assert_error_mentioning(verify_report(report, snapshot), "not under 'everything'")


def test_rejects_an_unplaced_project_without_a_reason(snapshot):
    report = report_matching(snapshot)
    report["projects"][0]["proposed_category_slug"] = None

    assert_error_mentioning(verify_report(report, snapshot), "no entry in unplaced[]")


def test_accepts_an_unplaced_project_with_a_reason(snapshot):
    report = report_matching(snapshot)
    report["projects"][0]["proposed_category_slug"] = None
    report["unplaced"] = [{"id": "1", "reason": "Description is empty."}]

    assert verify_report(report, snapshot).ok


def test_rejects_a_missing_rationale(snapshot):
    report = report_matching(snapshot)
    report["projects"][0]["rationale"] = "   "

    assert_error_mentioning(verify_report(report, snapshot), "has no rationale")


def test_rejects_an_unknown_confidence(snapshot):
    report = report_matching(snapshot)
    report["projects"][0]["confidence"] = "quite sure"

    assert_error_mentioning(verify_report(report, snapshot), "needs confidence in")


def test_rejects_a_category_without_a_status(snapshot):
    report = report_matching(snapshot)
    report["proposed_taxonomy"] = [{**CATEGORY, "status": "improved"}]

    assert_error_mentioning(verify_report(report, snapshot), "needs status in")


def test_rejects_a_report_missing_a_top_level_key(snapshot):
    report = report_matching(snapshot)
    del report["proposed_taxonomy"]

    assert_error_mentioning(
        verify_report(report, snapshot), "missing top-level key 'proposed_taxonomy'"
    )


def test_warns_about_an_empty_proposed_category_without_failing(snapshot):
    report = report_matching(snapshot)
    report["proposed_taxonomy"] = [CATEGORY, {**CATEGORY, "slug": "empty"}]

    result = verify_report(report, snapshot)

    assert result.ok
    assert_warning_mentioning(result, "'empty' holds no projects")


def test_warns_when_the_report_was_built_against_another_api(snapshot):
    report = report_matching(snapshot)
    report["source"]["api_url"] = "http://localhost:8000/api"

    result = verify_report(report, snapshot)

    assert result.ok
    assert_warning_mentioning(result, "built against http://localhost:8000/api")
