from scripts.taxonomy.diff import render_diff


def report_with(taxonomy, projects, **overrides):
    current = {}
    for project in projects:
        slug = project["current_category_slug"]
        current[slug] = current.get(slug, 0) + 1
    report = {
        "generated_at": "2026-08-21",
        "source": {"api_url": "https://example.test/api"},
        "current_categories": [
            {
                "slug": slug,
                "name": (slug or "uncategorised").title(),
                "project_count": count,
            }
            for slug, count in current.items()
        ],
        "proposed_taxonomy": taxonomy,
        "projects": projects,
        "unplaced": [],
    }
    return {**report, **overrides}


def category(slug, name, status, replaces=(), **kwargs):
    return {
        "slug": slug,
        "name": name,
        "status": status,
        "replaces": list(replaces),
        "rationale": kwargs.pop("rationale", "Because."),
        "future_example": kwargs.pop("future_example", ""),
        "subcategories": kwargs.pop("subcategories", []),
        **kwargs,
    }


def project(id_, title, current, proposed, **kwargs):
    return {
        "id": id_,
        "title": title,
        "current_category_slug": current,
        "proposed_category_slug": proposed,
        "proposed_subcategory_slug": kwargs.pop("subcategory", None),
        "alternative_category_slug": None,
        "confidence": kwargs.pop("confidence", "high"),
        "rationale": kwargs.pop("rationale", "It fits."),
    }


def test_lists_new_categories_with_their_rationale():
    diff = render_diff(
        report_with(
            [
                category(
                    "games", "Games & Fun", "new", rationale="Games were scattered."
                )
            ],
            [project("1", "Broadside", "apps", "games")],
        )
    )

    assert "### New (1)" in diff
    assert "**Games & Fun** (`games`)" in diff
    assert "Games were scattered." in diff


def test_shows_what_a_renamed_category_replaces():
    diff = render_diff(
        report_with(
            [category("civic", "Civic Tech", "renamed", replaces=["community"])],
            [project("1", "Yrda", "community", "civic")],
        )
    )

    assert "**Civic Tech** (`civic`) ← `Community`" in diff


def test_a_renamed_category_does_not_count_as_a_move():
    diff = render_diff(
        report_with(
            [category("civic", "Civic Tech", "renamed", replaces=["community"])],
            [project("1", "Yrda", "community", "civic")],
        )
    )

    assert "## Moves (0 of 1)" in diff
    assert "- 1 project follows `community` → `civic`, renamed under it." in diff


def test_a_split_counts_as_a_move_even_for_the_biggest_shard():
    """Two categories claim `apps`, so the slug is gone for everyone in it."""
    diff = render_diff(
        report_with(
            [
                category("consumer", "Consumer Apps", "split", replaces=["apps"]),
                category("games", "Games", "split", replaces=["apps"]),
            ],
            [
                project("1", "One", "apps", "consumer"),
                project("2", "Two", "apps", "games"),
            ],
        )
    )

    assert "## Moves (2 of 2)" in diff


def test_leaving_a_category_that_survives_is_a_move_not_a_rename():
    """Developer Tools stays; the two projects leaving it are being re-filed."""
    diff = render_diff(
        report_with(
            [
                category("dev-tools", "Developer Tools", "kept"),
                category(
                    "language", "Icelandic Language", "new", replaces=["dev-tools"]
                ),
            ],
            [
                project("1", "Lemmatiser", "dev-tools", "language"),
                project("2", "CLI", "dev-tools", "dev-tools"),
            ],
        )
    )

    assert "## Moves (1 of 2)" in diff
    assert "- 1 project keeps its category and slug." in diff


def test_lists_a_project_that_changes_category():
    diff = render_diff(
        report_with(
            [
                category("apps", "Apps", "kept"),
                category("games", "Games", "new"),
            ],
            [
                project("1", "Broadside", "apps", "games"),
                project("2", "Keep", "apps", "apps"),
            ],
        )
    )

    assert "## Moves (1 of 2)" in diff
    assert "**Into Games**" in diff
    assert "- Broadside — Apps (high)" in diff
    assert "- 1 project keeps its category and slug." in diff


def test_shows_where_each_current_category_ends_up():
    diff = render_diff(
        report_with(
            [
                category("consumer", "Consumer Apps", "split", replaces=["apps"]),
                category("games", "Games", "new"),
            ],
            [
                project("1", "One", "apps", "consumer"),
                project("2", "Two", "apps", "consumer"),
                project("3", "Three", "apps", "games"),
            ],
        )
    )

    assert "**Apps** (3)" in diff
    assert "- 2 → Consumer Apps" in diff
    assert "- 1 → Games" in diff


def test_names_categories_that_nothing_claims_as_retired():
    diff = render_diff(
        report_with(
            [category("games", "Games", "new")],
            [project("1", "Broadside", "apps", "games")],
        )
    )

    assert "### Retired (1)" in diff
    assert "**Apps** (`apps`) — 1 project, claimed by nothing" in diff


def test_counts_subcategory_members():
    taxonomy = [
        category(
            "consumer",
            "Consumer Apps",
            "new",
            subcategories=[{"slug": "sport", "name": "Sport", "rationale": "…"}],
        )
    ]
    projects = [
        project("1", "One", "apps", "consumer", subcategory="sport"),
        project("2", "Two", "apps", "consumer"),
    ]

    assert "↳ **Sport** (`sport`) — 1 project" in render_diff(
        report_with(taxonomy, projects)
    )


def test_unplaced_projects_are_reported_once_not_as_a_move():
    report = report_with(
        [category("games", "Games", "new")],
        [project("1", "Ghost", "apps", None)],
        unplaced=[{"id": "1", "reason": "Site is offline."}],
    )

    diff = render_diff(report)

    assert "## Moves (0 of 1)" in diff
    assert "## Unplaced (1)" in diff
    assert "- Ghost — Site is offline." in diff
    assert "- 1 → _unplaced_" in diff


def test_low_confidence_placements_get_their_own_section():
    diff = render_diff(
        report_with(
            [category("games", "Games", "new")],
            [
                project(
                    "1",
                    "Mystery",
                    "apps",
                    "games",
                    confidence="low",
                    rationale="Description is two words.",
                )
            ],
        )
    )

    assert "## Low confidence (1)" in diff
    assert "- Mystery — Description is two words." in diff


def test_observations_are_carried_through():
    report = report_with(
        [category("games", "Games", "new")],
        [project("1", "Broadside", "apps", "games")],
        observations=["Games is the thinnest of the five."],
    )

    assert "- Games is the thinnest of the five." in render_diff(report)


def test_survives_a_report_with_nothing_in_it():
    render_diff({"generated_at": "2026-08-21"})
