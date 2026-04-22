from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .snapshot import Snapshot


@dataclass(frozen=True)
class Diff:
    # key -> (new_text, new_hash)
    added: dict[str, tuple[str, str]] = field(default_factory=dict)
    changed: dict[str, tuple[str, str]] = field(default_factory=dict)
    removed: set[str] = field(default_factory=set)


def diff_snapshots(old: Snapshot, new: Snapshot) -> Diff:
    added: dict[str, tuple[str, str]] = {}
    changed: dict[str, tuple[str, str]] = {}
    removed: set[str] = set()

    old_keys = set(old.entries)
    new_keys = set(new.entries)

    for key in new_keys - old_keys:
        added[key] = new.entries[key]
    for key in old_keys - new_keys:
        removed.add(key)
    for key in old_keys & new_keys:
        old_text, _old_hash = old.entries[key]
        new_text, new_hash = new.entries[key]
        if old_text != new_text:
            changed[key] = (new_text, new_hash)

    return Diff(added=added, changed=changed, removed=removed)
