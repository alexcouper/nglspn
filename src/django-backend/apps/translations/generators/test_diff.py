from apps.translations.generators.diff import Diff, diff_snapshots
from apps.translations.generators.snapshot import Snapshot


def snap(entries: dict[str, tuple[str, str]]) -> Snapshot:
    return Snapshot(entries=entries)


def test_no_changes() -> None:
    a = snap({"k": ("v", "h1")})
    assert diff_snapshots(a, a) == Diff()


def test_added_key() -> None:
    old = snap({})
    new = snap({"nav.home": ("Home", "h1")})
    assert diff_snapshots(old, new) == Diff(added={"nav.home": ("Home", "h1")})


def test_removed_key() -> None:
    old = snap({"old.key": ("Old", "h0")})
    new = snap({})
    assert diff_snapshots(old, new) == Diff(removed={"old.key"})


def test_changed_source_text() -> None:
    old = snap({"k": ("Old text", "h_old")})
    new = snap({"k": ("New text", "h_new")})
    assert diff_snapshots(old, new) == Diff(changed={"k": ("New text", "h_new")})


def test_only_same_text_with_different_hash_is_not_a_change() -> None:
    old = snap({"k": ("Same", "h_a")})
    new = snap({"k": ("Same", "h_b")})
    assert diff_snapshots(old, new) == Diff()
