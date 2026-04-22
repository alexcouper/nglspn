from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .flatten import flatten_en
from .hashing import source_hash

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class Snapshot:
    # key -> (english_text, source_hash)
    entries: dict[str, tuple[str, str]] = field(default_factory=dict)

    @classmethod
    def from_en_json(cls, en: dict) -> Snapshot:
        flat = flatten_en(en)
        return cls(entries={k: (v, source_hash(v)) for k, v in flat.items()})


def read_snapshot(path: Path) -> Snapshot:
    if not path.exists():
        return Snapshot()
    raw = json.loads(path.read_text(encoding="utf-8"))
    return Snapshot(
        entries={
            k: (v["text"], v["source_hash"]) for k, v in raw.get("keys", {}).items()
        }
    )


def write_snapshot(path: Path, snap: Snapshot) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "keys": {
            k: {"text": t, "source_hash": h}
            for k, (t, h) in sorted(snap.entries.items())
        },
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
