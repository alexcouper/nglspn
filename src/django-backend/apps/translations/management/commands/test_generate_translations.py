import json
from pathlib import Path

import pytest
from django.core.management import call_command

from apps.translations.models import Translation


@pytest.fixture
def workspace(tmp_path: Path) -> dict[str, Path]:
    en = tmp_path / "en.json"
    snap = tmp_path / "en-snapshot.json"
    mig_dir = tmp_path / "migrations"
    mig_dir.mkdir()
    (mig_dir / "0099_baseline.py").write_text("# placeholder\n", encoding="utf-8")
    return {"en_json": en, "snapshot": snap, "migrations": mig_dir}


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


@pytest.mark.django_db
def test_new_keys_are_translated_and_written_to_migration(workspace) -> None:
    write_json(workspace["en_json"], {"nav": {"home": "Home"}})

    call_command(
        "generate_translations",
        "--en-json",
        str(workspace["en_json"]),
        "--snapshot",
        str(workspace["snapshot"]),
        "--migrations-dir",
        str(workspace["migrations"]),
        "--previous-migration",
        "0099_baseline",
        "--translator",
        "stub",
    )

    generated = sorted(workspace["migrations"].glob("01*_translate_new_keys.py"))
    assert len(generated) == 1, list(workspace["migrations"].iterdir())
    content = generated[0].read_text(encoding="utf-8")
    assert "nav.home" in content
    assert "[is] Home" in content
    assert (
        json.loads(workspace["snapshot"].read_text(encoding="utf-8"))["keys"][
            "nav.home"
        ]["text"]
        == "Home"
    )


@pytest.mark.django_db
def test_no_changes_writes_no_migration_and_exits_zero(workspace) -> None:
    write_json(workspace["en_json"], {"nav": {"home": "Home"}})
    write_json(
        workspace["snapshot"],
        {"keys": {"nav.home": {"text": "Home", "source_hash": "0" * 16}}},
    )

    call_command(
        "generate_translations",
        "--en-json",
        str(workspace["en_json"]),
        "--snapshot",
        str(workspace["snapshot"]),
        "--migrations-dir",
        str(workspace["migrations"]),
        "--previous-migration",
        "0099_baseline",
        "--translator",
        "stub",
    )

    assert not list(workspace["migrations"].glob("01*_translate_new_keys.py"))


@pytest.mark.django_db
def test_changed_source_with_human_edited_is_bumps_hash_only(workspace) -> None:
    write_json(
        workspace["snapshot"],
        {"keys": {"nav.home": {"text": "Home OLD", "source_hash": "h_old"}}},
    )
    write_json(workspace["en_json"], {"nav": {"home": "Home NEW"}})
    Translation.objects.create(
        locale="is",
        key="nav.home",
        text="Heim (manually edited)",
        source_hash="h_old",
        is_machine_translated=False,
    )

    call_command(
        "generate_translations",
        "--en-json",
        str(workspace["en_json"]),
        "--snapshot",
        str(workspace["snapshot"]),
        "--migrations-dir",
        str(workspace["migrations"]),
        "--previous-migration",
        "0099_baseline",
        "--translator",
        "stub",
    )

    generated = sorted(workspace["migrations"].glob("01*_translate_new_keys.py"))
    assert len(generated) == 1
    content = generated[0].read_text(encoding="utf-8")
    assert "SOURCE_HASH_BUMPED" in content
    assert "nav.home" in content
    assert "[is] Home NEW" not in content


@pytest.mark.django_db
def test_changed_source_with_mt_row_is_retranslated(workspace) -> None:
    write_json(
        workspace["snapshot"],
        {"keys": {"nav.home": {"text": "Home OLD", "source_hash": "h_old"}}},
    )
    write_json(workspace["en_json"], {"nav": {"home": "Home NEW"}})
    Translation.objects.create(
        locale="is",
        key="nav.home",
        text="Heim",
        source_hash="h_old",
        is_machine_translated=True,
    )

    call_command(
        "generate_translations",
        "--en-json",
        str(workspace["en_json"]),
        "--snapshot",
        str(workspace["snapshot"]),
        "--migrations-dir",
        str(workspace["migrations"]),
        "--previous-migration",
        "0099_baseline",
        "--translator",
        "stub",
    )

    generated = sorted(workspace["migrations"].glob("01*_translate_new_keys.py"))
    content = generated[0].read_text(encoding="utf-8")
    assert "RETRANSLATED" in content
    assert "[is] Home NEW" in content


@pytest.mark.django_db
def test_removed_keys_are_retired(workspace) -> None:
    write_json(
        workspace["snapshot"],
        {"keys": {"gone.key": {"text": "Gone", "source_hash": "h"}}},
    )
    write_json(workspace["en_json"], {})

    call_command(
        "generate_translations",
        "--en-json",
        str(workspace["en_json"]),
        "--snapshot",
        str(workspace["snapshot"]),
        "--migrations-dir",
        str(workspace["migrations"]),
        "--previous-migration",
        "0099_baseline",
        "--translator",
        "stub",
    )

    generated = sorted(workspace["migrations"].glob("01*_translate_new_keys.py"))
    content = generated[0].read_text(encoding="utf-8")
    assert "'gone.key'" in content
    assert "RETIRED" in content
