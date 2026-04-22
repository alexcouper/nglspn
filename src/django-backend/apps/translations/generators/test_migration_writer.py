from apps.translations.generators.migration_writer import render_migration


def test_rendered_migration_has_expected_structure() -> None:
    text = render_migration(
        previous_migration="0003_seed_phase2_ui_chrome",
        added={"nav.new": ("Nýtt", "h_new")},
        retranslated={"nav.changed": ("Breytt", "h_changed")},
        source_hash_bumped={"nav.human_edited": "h_bumped"},
        retired=["old.key"],
    )

    assert '("translations", "0003_seed_phase2_ui_chrome")' in text
    assert "'nav.new': ('Nýtt', 'h_new')" in text
    assert "'nav.changed': ('Breytt', 'h_changed')" in text
    assert "'nav.human_edited': 'h_bumped'" in text
    assert "'old.key'" in text
    compile(text, "<generated>", "exec")


def test_empty_diff_renders_but_is_a_no_op_migration() -> None:
    text = render_migration(
        previous_migration="0003_prior",
        added={},
        retranslated={},
        source_hash_bumped={},
        retired=[],
    )
    compile(text, "<generated>", "exec")
    assert "NEW_IS: dict" in text
