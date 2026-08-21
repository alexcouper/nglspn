"""Deterministic checks on a taxonomy report.

Errors are facts the report gets wrong about the site: a missing project, an
invented one, a project filed under a category it isn't in, a placement
pointing at a category the report never defines. Warnings are shape heuristics
— the report is consistent but the grouping looks off. Only errors fail.

Pure: it compares a report to a snapshot (see `api.fetch_snapshot`) and touches
nothing else.
"""

import re
from dataclasses import dataclass, field
from typing import Any

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
CONFIDENCE_VALUES = {"high", "medium", "low"}
CATEGORY_STATUSES = {"kept", "renamed", "merged", "split", "new"}
REQUIRED_KEYS = (
    "generated_at",
    "source",
    "current_categories",
    "proposed_taxonomy",
    "projects",
)
MIN_CATEGORY_SIZE = 3
MAX_CATEGORY_SHARE = 0.30
MIN_SUBCATEGORY_SIZE = 2


@dataclass
class Result:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    project_count: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors


def _plural(count: int) -> str:
    return f"{count} project" if count == 1 else f"{count} projects"


def _structure_errors(report: dict[str, Any]) -> list[str]:
    errors = [
        f"report is missing top-level key {key!r}"
        for key in REQUIRED_KEYS
        if key not in report
    ]
    if errors:
        return errors
    if not isinstance(report["source"], dict):
        errors.append("source must be an object")
    if not isinstance(report["projects"], list):
        errors.append("projects must be a list")
    if not isinstance(report["proposed_taxonomy"], list):
        errors.append("proposed_taxonomy must be a list")
    if not isinstance(report["current_categories"], list):
        errors.append("current_categories must be a list")
    return errors


def _taxonomy_index(report: dict[str, Any], errors: list[str]) -> dict[str, set[str]]:
    """Map category slug -> its subcategory slugs, collecting definition errors."""
    index: dict[str, set[str]] = {}
    for category in report["proposed_taxonomy"]:
        slug = category.get("slug", "")
        if not SLUG_PATTERN.match(str(slug)):
            errors.append(f"proposed category slug {slug!r} is not kebab-case")
        if slug in index:
            errors.append(f"proposed category slug {slug!r} is defined twice")
        if not str(category.get("name", "")).strip():
            errors.append(f"proposed category {slug!r} has no name")
        if not str(category.get("rationale", "")).strip():
            errors.append(f"proposed category {slug!r} has no rationale")
        if category.get("status") not in CATEGORY_STATUSES:
            allowed = sorted(CATEGORY_STATUSES)
            errors.append(f"proposed category {slug!r} needs status in {allowed}")
        subs: set[str] = set()
        for sub in category.get("subcategories", []):
            sub_slug = sub.get("slug", "")
            if not SLUG_PATTERN.match(str(sub_slug)):
                errors.append(f"subcategory slug {sub_slug!r} is not kebab-case")
            if sub_slug in subs:
                errors.append(f"subcategory slug {sub_slug!r} is defined twice")
            subs.add(str(sub_slug))
        index[str(slug)] = subs
    return index


def _coverage_errors(report: dict[str, Any], truth: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for entry in report["projects"]:
        project_id = str(entry.get("id", ""))
        if project_id in seen:
            errors.append(f"project {project_id} appears more than once in the report")
            continue
        seen.add(project_id)
        actual = truth.get(project_id)
        if actual is None:
            errors.append(
                f"report lists project {project_id} "
                f"({entry.get('title', '?')!r}) which the API does not return"
            )
            continue
        if entry.get("title") != actual["title"]:
            errors.append(
                f"project {project_id}: report says title {entry.get('title')!r}, "
                f"the API says {actual['title']!r}"
            )
        expected = actual["current_category_slug"]
        if entry.get("current_category_slug") != expected:
            errors.append(
                f"project {project_id} ({actual['title']!r}): report says current "
                f"category {entry.get('current_category_slug')!r}, "
                f"the API says {expected!r}"
            )
    errors.extend(
        f"project {project_id} ({project['title']!r}) is missing from the report"
        for project_id, project in truth.items()
        if project_id not in seen
    )
    return errors


def _placement_errors(report: dict[str, Any], index: dict[str, set[str]]) -> list[str]:
    errors: list[str] = []
    unplaced = {str(item.get("id")): item for item in report.get("unplaced", [])}
    for entry in report["projects"]:
        project_id = str(entry.get("id", ""))
        label = f"project {project_id} ({entry.get('title', '?')!r})"
        category = entry.get("proposed_category_slug")
        if category is None:
            reason = str(unplaced.get(project_id, {}).get("reason", "")).strip()
            if not reason:
                errors.append(
                    f"{label} has no proposed category and no entry in "
                    f"unplaced[] explaining why"
                )
        elif category not in index:
            errors.append(f"{label} is placed in undefined category {category!r}")
        elif entry.get("proposed_subcategory_slug") is not None and (
            entry["proposed_subcategory_slug"] not in index[category]
        ):
            errors.append(
                f"{label} is placed in subcategory "
                f"{entry['proposed_subcategory_slug']!r}, which is not under "
                f"{category!r}"
            )
        alternative = entry.get("alternative_category_slug")
        if alternative is not None and alternative not in index:
            errors.append(f"{label} names undefined alternative {alternative!r}")
        if entry.get("confidence") not in CONFIDENCE_VALUES:
            errors.append(f"{label} needs confidence in {sorted(CONFIDENCE_VALUES)}")
        if not str(entry.get("rationale", "")).strip():
            errors.append(f"{label} has no rationale")
    reported_ids = {str(entry.get("id")) for entry in report["projects"]}
    errors.extend(
        f"unplaced[] lists project {project_id}, which is not in the report"
        for project_id in unplaced
        if project_id not in reported_ids
    )
    return errors


def _current_category_errors(
    report: dict[str, Any], snapshot: dict[str, Any]
) -> list[str]:
    actual = {row["slug"]: row for row in snapshot["current_categories"]}
    reported = {row.get("slug"): row for row in report["current_categories"]}
    errors = [
        f"current_categories lists {slug!r}, which the API does not return"
        for slug in reported
        if slug not in actual
    ]
    for slug, row in actual.items():
        if slug not in reported:
            errors.append(
                f"current_categories omits {slug!r} ({_plural(row['project_count'])})"
            )
        elif reported[slug].get("project_count") != row["project_count"]:
            errors.append(
                f"current_categories says {slug!r} holds "
                f"{reported[slug].get('project_count')!r} projects, "
                f"the API says {row['project_count']}"
            )
    return errors


def _shape_warnings(report: dict[str, Any], index: dict[str, set[str]]) -> list[str]:
    placed = [
        entry
        for entry in report["projects"]
        if entry.get("proposed_category_slug") in index
    ]
    total = len(placed) or 1
    warnings: list[str] = []
    for slug, subs in index.items():
        members = [e for e in placed if e["proposed_category_slug"] == slug]
        if not members:
            warnings.append(f"proposed category {slug!r} holds no projects")
        elif len(members) < MIN_CATEGORY_SIZE:
            warnings.append(
                f"proposed category {slug!r} holds only {_plural(len(members))}"
            )
        if len(members) / total > MAX_CATEGORY_SHARE:
            warnings.append(
                f"proposed category {slug!r} holds "
                f"{len(members) / total:.0%} of all projects"
            )
        for sub in subs:
            sized = [e for e in members if e.get("proposed_subcategory_slug") == sub]
            if len(sized) < MIN_SUBCATEGORY_SIZE:
                warnings.append(f"subcategory {slug}/{sub} holds {_plural(len(sized))}")
    return warnings


def _source_warnings(report: dict[str, Any], snapshot: dict[str, Any]) -> list[str]:
    reported = str(report["source"].get("api_url", "")).rstrip("/")
    checked = str(snapshot["source"]["api_url"]).rstrip("/")
    if reported and reported != checked:
        return [f"report was built against {reported}, checked against {checked}"]
    return []


def verify_report(report: dict[str, Any], snapshot: dict[str, Any]) -> Result:
    structure = _structure_errors(report)
    if structure:
        return Result(errors=structure)

    truth = {str(project["id"]): project for project in snapshot["projects"]}
    result = Result(project_count=len(truth))

    index = _taxonomy_index(report, result.errors)
    result.errors.extend(_coverage_errors(report, truth))
    result.errors.extend(_placement_errors(report, index))
    result.errors.extend(_current_category_errors(report, snapshot))
    result.warnings.extend(_source_warnings(report, snapshot))
    result.warnings.extend(_shape_warnings(report, index))
    return result
