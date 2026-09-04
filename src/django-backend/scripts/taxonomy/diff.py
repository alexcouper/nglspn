"""Render a taxonomy report as a human-readable diff.

Works from the report alone — no API, no snapshot — because the report already
carries each project's current category. The output is Markdown, meant to be
pasted into an issue or a PR.

Lineage comes from each proposed category's `replaces`: a project whose current
category is claimed by the category it lands in has not moved, even when the
slug changed under it.
"""

from typing import Any

UNCHANGED = "unchanged"
RENAMED = "renamed"
MOVED = "moved"


def _phrase(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"


def _plural(count: int) -> str:
    return _phrase(count, "project", "projects")


def _category_names(report: dict[str, Any]) -> dict[str | None, str]:
    names = {
        row.get("slug"): row.get("name", row.get("slug"))
        for row in report.get("current_categories", [])
    }
    names[None] = names.get(None, "(uncategorised)")
    return names


def _proposed(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(c.get("slug")): c for c in report.get("proposed_taxonomy", [])}


def _lineage(category: dict[str, Any]) -> set[str | None]:
    """Current slugs this proposed category considers itself the successor of."""
    return {str(category.get("slug")), *[str(s) for s in category.get("replaces", [])]}


def _claimants(report: dict[str, Any]) -> dict[str | None, list[str]]:
    """Current slug -> the proposed categories claiming to succeed it."""
    claims: dict[str | None, list[str]] = {}
    for category in report.get("proposed_taxonomy", []):
        for slug in category.get("replaces", []):
            claims.setdefault(str(slug), []).append(str(category.get("slug")))
    return claims


def _movement(report: dict[str, Any]) -> dict[str, str]:
    """Project id -> unchanged, renamed under it, or re-filed.

    A split dissolves the old slug even for the projects the biggest shard
    keeps, so `replaces` only counts as continuity when one category claims the
    old slug on its own — and never when the old slug survives in the new
    taxonomy, because then leaving it is a re-filing like any other.
    """
    claims = _claimants(report)
    survives = set(_proposed(report))
    movement = {}
    for entry in report.get("projects", []):
        current = entry.get("current_category_slug")
        target = entry.get("proposed_category_slug")
        if target is not None and current == target:
            state = UNCHANGED
        elif claims.get(str(current)) == [str(target)] and str(current) not in survives:
            state = RENAMED
        else:
            state = MOVED
        movement[str(entry.get("id"))] = state
    return movement


def _members(report: dict[str, Any], slug: str) -> list[dict[str, Any]]:
    return [
        entry
        for entry in report.get("projects", [])
        if entry.get("proposed_category_slug") == slug
    ]


def _heading(report: dict[str, Any]) -> list[str]:
    source = report.get("source", {})
    return [
        f"# Taxonomy diff — {report.get('generated_at', 'undated')}",
        "",
        f"{_plural(len(report.get('projects', [])))} · "
        + _phrase(
            len(report.get("proposed_taxonomy", [])),
            "proposed category",
            "proposed categories",
        )
        + f" · API: {source.get('api_url', 'unknown')}",
    ]


def _category_lines(report: dict[str, Any]) -> list[str]:
    names = _category_names(report)
    lines = ["", "## Category changes"]
    by_status: dict[str, list[dict[str, Any]]] = {}
    for category in report.get("proposed_taxonomy", []):
        by_status.setdefault(str(category.get("status")), []).append(category)

    for status in ("new", "renamed", "split", "merged", "kept"):
        categories = by_status.get(status, [])
        if not categories:
            continue
        lines += ["", f"### {status.title()} ({len(categories)})"]
        for category in categories:
            replaces = ", ".join(
                f"`{names.get(slug, slug)}`" for slug in category.get("replaces", [])
            )
            from_part = f" ← {replaces}" if replaces else ""
            lines.append(
                f"- **{category.get('name')}** (`{category.get('slug')}`)"
                f"{from_part} — {_plural(len(_members(report, str(category.get('slug')))))}"
            )
            lines.append(f"  - {category.get('rationale', '')}")
            if category.get("future_example"):
                lines.append(f"  - Next one in: {category['future_example']}")
            for sub in category.get("subcategories", []):
                sized = [
                    e
                    for e in _members(report, str(category.get("slug")))
                    if e.get("proposed_subcategory_slug") == sub.get("slug")
                ]
                lines.append(
                    f"  - ↳ **{sub.get('name')}** (`{sub.get('slug')}`) — "
                    f"{_plural(len(sized))}"
                )

    claimed: set[str | None] = set()
    for category in report.get("proposed_taxonomy", []):
        claimed |= _lineage(category)
    retired = [
        row
        for row in report.get("current_categories", [])
        if row.get("slug") is not None and str(row["slug"]) not in claimed
    ]
    if retired:
        lines += ["", f"### Retired ({len(retired)})"]
        lines += [
            f"- **{row.get('name')}** (`{row.get('slug')}`) — "
            f"{_plural(row.get('project_count', 0))}, claimed by nothing"
            for row in retired
        ]
    return lines


def _fanout_lines(report: dict[str, Any]) -> list[str]:
    names = _category_names(report)
    proposed = _proposed(report)
    lines = ["", "## Where today's categories go"]
    for row in report.get("current_categories", []):
        current = row.get("slug")
        members = [
            e
            for e in report.get("projects", [])
            if e.get("current_category_slug") == current
        ]
        if not members:
            continue
        destinations: dict[str, int] = {}
        for entry in members:
            target = str(entry.get("proposed_category_slug"))
            destinations[target] = destinations.get(target, 0) + 1
        lines += ["", f"**{names.get(current, current)}** ({len(members)})"]
        lines += [
            f"- {count} → "
            + (proposed[slug].get("name", slug) if slug in proposed else "_unplaced_")
            for slug, count in sorted(
                destinations.items(), key=lambda item: (-item[1], item[0])
            )
        ]
    return lines


def _move_lines(report: dict[str, Any]) -> list[str]:
    names = _category_names(report)
    proposed = _proposed(report)
    movement = _movement(report)
    projects = report.get("projects", [])
    moved = [
        e
        for e in projects
        if movement[str(e.get("id"))] == MOVED
        and e.get("proposed_category_slug") is not None
    ]
    lines = ["", f"## Moves ({len(moved)} of {len(projects)})"]
    if not moved:
        lines += ["", "_Nothing is re-filed._"]
    for slug in sorted({str(e.get("proposed_category_slug")) for e in moved}):
        into = proposed[slug].get("name", slug) if slug in proposed else slug
        lines += ["", f"**Into {into}**"]
        lines += [
            f"- {entry.get('title')} — "
            f"{names.get(entry.get('current_category_slug'), '?')}"
            f" ({entry.get('confidence')})"
            for entry in moved
            if str(entry.get("proposed_category_slug")) == slug
        ]

    unchanged = [e for e in projects if movement[str(e.get("id"))] == UNCHANGED]
    renamed = [e for e in projects if movement[str(e.get("id"))] == RENAMED]
    lines += ["", "### Not re-filed", ""]
    lines.append(
        "- "
        + _phrase(
            len(unchanged),
            "project keeps its category and slug.",
            "projects keep their category and slug.",
        )
    )
    pairs: dict[tuple[str | None, str], int] = {}
    for entry in renamed:
        key = (
            entry.get("current_category_slug"),
            str(entry.get("proposed_category_slug")),
        )
        pairs[key] = pairs.get(key, 0) + 1
    lines += [
        f"- {_phrase(count, 'project follows', 'projects follow')} "
        f"`{old_slug}` → `{new_slug}`, renamed under "
        f"{'it' if count == 1 else 'them'}."
        for (old_slug, new_slug), count in sorted(pairs.items(), key=lambda i: -i[1])
    ]
    return lines


def _attention_lines(report: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    low = [e for e in report.get("projects", []) if e.get("confidence") == "low"]
    if low:
        lines += ["", f"## Low confidence ({len(low)})", ""]
        lines += [f"- {e.get('title')} — {e.get('rationale')}" for e in low]
    unplaced = report.get("unplaced", [])
    if unplaced:
        titles = {str(e.get("id")): e.get("title") for e in report.get("projects", [])}
        lines += ["", f"## Unplaced ({len(unplaced)})", ""]
        lines += [
            f"- {titles.get(str(item.get('id')), item.get('id'))} — {item.get('reason')}"
            for item in unplaced
        ]
    observations = report.get("observations", [])
    if observations:
        lines += ["", "## Observations", ""]
        lines += [f"- {observation}" for observation in observations]
    return lines


def render_diff(report: dict[str, Any]) -> str:
    lines = (
        _heading(report)
        + _category_lines(report)
        + _fanout_lines(report)
        + _move_lines(report)
        + _attention_lines(report)
    )
    return "\n".join(lines) + "\n"
