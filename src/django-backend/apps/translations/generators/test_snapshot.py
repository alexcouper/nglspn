from pathlib import Path

from apps.translations.generators.snapshot import (
    Snapshot,
    read_snapshot,
    write_snapshot,
)


def test_read_missing_file_returns_empty(tmp_path: Path) -> None:
    snap = read_snapshot(tmp_path / "missing.json")
    assert snap.entries == {}


def test_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "snap.json"
    snap = Snapshot(entries={"nav.home": ("Home", "deadbeef12345678")})
    write_snapshot(path, snap)
    loaded = read_snapshot(path)
    assert loaded == snap


def test_from_en_json_computes_hashes() -> None:
    snap = Snapshot.from_en_json({"nav": {"home": "Home"}})
    assert set(snap.entries.keys()) == {"nav.home"}
    text, h = snap.entries["nav.home"]
    assert text == "Home"
    assert len(h) == 16
    assert all(c in "0123456789abcdef" for c in h)
