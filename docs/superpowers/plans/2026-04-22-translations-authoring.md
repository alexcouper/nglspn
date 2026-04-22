# Phase 3 — Translations Authoring Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the developer authoring loop. Adding a new string becomes: add `t('new.key')` + an entry in `en.json`, run `make translate-new-keys`, commit the generated Django data migration alongside the code. Lint ensures every `t('...')` references a key that actually exists in `en.json`.

**Architecture:** A Django management command `generate_translations` diffs the current `en.json` against a committed snapshot file. For new keys it calls DeepL; for keys whose English source changed it either re-translates (when the current IS row is still machine-translated) or only bumps `source_hash` (when a human has edited the IS row); for removed keys it retires the row. The command writes the result as a conventional Django data migration file and rewrites the snapshot. A standalone web-ui lint script verifies every `t('...')` call points at a key that actually exists in `en.json`. Both are wired into `make ci`.

**Tech Stack:** Python 3.12, Django, DeepL REST API (via `requests`), Node 20+, plain TypeScript AST parsing via `@typescript-eslint/typescript-estree` (already a transitive dep through Next's ESLint config), Makefile, jj.

**Design reference:** `docs/superpowers/specs/2026-04-22-dynamic-translations-design.md` (§Authoring flow).
**Phase 2 output:** `docs/superpowers/plans/2026-04-22-translations-web-ui.md`.

---

## Scope

**In scope (Phase 3):**
- `make translate-new-keys` that produces a ready-to-commit Django data migration.
- DeepL client with pluggable interface (so it can be swapped / stubbed in tests).
- Snapshot state file tracking the last-seen `en.json` shape.
- Migration writer that produces idempotent `update_or_create`-style data migrations.
- Handling of: new keys, changed-source keys (re-translate or source_hash bump depending on MT flag), removed keys (retire).
- Web-UI lint script: every `t('key')` (and `useTranslations('ns')`'s subsequent `t('sub')`) resolves against `en.json`. Fails the build on a miss.
- Hook into Makefile + `make ci`.
- A minimal developer doc section.

**Out of scope (later phases):**
- Inline edit UI (`<Translatable>`, pencil, popover) — Phase 4.
- Editor worklist — Phase 5.
- Auto pre-push git hook — explicitly not done; it's brittle. Docs will say "run `make translate-new-keys` before pushing."
- Forbidding **hardcoded strings** in JSX globally. Scope Phase 3's lint only to verifying `t()` keys exist. The broader "no hardcoded strings" rule is scoped in Phase 4 once every surface has been migrated.
- Automatic rate-limit / abuse mitigation on the PATCH endpoint beyond "logged-in user" — the design defers this.
- Webhook secret rotation — deferred.

## File structure

**Create:**
- `src/django-backend/apps/translations/generators/__init__.py` — package marker.
- `src/django-backend/apps/translations/generators/snapshot.py` — read/write/compare `en-snapshot.json`.
- `src/django-backend/apps/translations/generators/flatten.py` — tiny helper: nested `en.json` → `{"ns.key": "text"}`.
- `src/django-backend/apps/translations/generators/hashing.py` — stable content-addressed hash of an English source string (SHA-256, first 16 hex chars).
- `src/django-backend/apps/translations/generators/diff.py` — compute `{added, changed, removed}` between old and new snapshots.
- `src/django-backend/apps/translations/generators/translator.py` — abstract `Translator` protocol + `DeepLTranslator` implementation.
- `src/django-backend/apps/translations/generators/migration_writer.py` — renders a Django migration file.
- `src/django-backend/apps/translations/generators/state/en-snapshot.json` — committed snapshot, updated by the command.
- `src/django-backend/apps/translations/management/__init__.py` — package marker.
- `src/django-backend/apps/translations/management/commands/__init__.py` — package marker.
- `src/django-backend/apps/translations/management/commands/generate_translations.py` — Django management command.
- `src/django-backend/apps/translations/generators/test_snapshot.py` — tests for snapshot helpers.
- `src/django-backend/apps/translations/generators/test_flatten.py` — tests for flatten helper.
- `src/django-backend/apps/translations/generators/test_diff.py` — tests for diff logic.
- `src/django-backend/apps/translations/generators/test_migration_writer.py` — tests for migration rendering.
- `src/django-backend/apps/translations/management/commands/test_generate_translations.py` — end-to-end test of the command with a stub `Translator`.
- `src/web-ui/scripts/lint-i18n.mjs` — web-ui lint script verifying `t()` keys exist in `en.json`.

**Modify:**
- `src/django-backend/Makefile` — add `translate-new-keys` target + wire check into `lint` or a new `lint-translations` target.
- `src/django-backend/pyproject.toml` — add `deepl` or keep using `requests` directly (plan uses `requests` which is already installed).
- `src/web-ui/package.json` — add `lint:i18n` script; change `"lint"` to run `lint:i18n` after eslint+tsc.
- `Makefile` at repo root (if it orchestrates `make ci`) — include the new lint gate.

(The design mentions a "system pseudo-user" for MT-seed audits, but because generated migrations use `apps.get_model(...)` — which bypasses model `save()` hooks — no audit rows are written at migration time anyway. Seeds intentionally have `updated_by=NULL` and produce no `TranslationAudit` rows. This is consistent with the design's "seeded rows have null" note on the `Translation.updated_by` field. No system-user row needed in Phase 3.)

**Config / env:**
- `DEEPL_AUTH_KEY` — set locally by developers; not present in CI. The command exits with a clear error when missing.

---

## Data contracts

### Snapshot file format

`apps/translations/generators/state/en-snapshot.json`:

```json
{
  "keys": {
    "nav.projects": {
      "text": "Projects",
      "source_hash": "b4a8d5e2f0c13a47"
    },
    "footer.about": {
      "text": "About",
      "source_hash": "7c1b90a2e5d6f3a1"
    }
  }
}
```

`source_hash` is `sha256(text).hexdigest()[:16]`. Keys match the flattened dotted form. The snapshot is rewritten by every successful `make translate-new-keys` run and committed alongside the generated migration.

### Migration file shape

Each generated migration is a `RunPython`-only migration with forward + reverse functions:

```python
from django.db import migrations


NEW_IS = {
    "new.key": "<MT output>",
}

CHANGED_SOURCE_HASH_ONLY = {
    # Keys whose English changed but the IS row was human-edited.
    # We bump source_hash so the "stale translation" worklist picks them up.
    "some.key": "<new-source-hash>",
}

CHANGED_RETRANSLATED = {
    # Keys whose English changed and IS was still MT — re-translated here.
    "other.key": ("<new MT>", "<new-source-hash>"),
}

RETIRED_KEYS = ["removed.key"]


def forward(apps, schema_editor):
    Translation = apps.get_model("translations", "Translation")
    for key, text in NEW_IS.items():
        Translation.objects.update_or_create(
            locale="is", key=key,
            defaults={"text": text, "source_hash": _hash_for(key), "is_machine_translated": True, "retired": False},
        )
    for key, new_hash in CHANGED_SOURCE_HASH_ONLY.items():
        Translation.objects.filter(locale="is", key=key).update(source_hash=new_hash)
    for key, (text, new_hash) in CHANGED_RETRANSLATED.items():
        Translation.objects.update_or_create(
            locale="is", key=key,
            defaults={"text": text, "source_hash": new_hash, "is_machine_translated": True, "retired": False},
        )
    for key in RETIRED_KEYS:
        Translation.objects.filter(locale="is", key=key).update(retired=True)


def backward(apps, schema_editor):
    Translation = apps.get_model("translations", "Translation")
    for key in RETIRED_KEYS:
        Translation.objects.filter(locale="is", key=key).update(retired=False)
    for key in CHANGED_SOURCE_HASH_ONLY:
        # No record of the old hash — reverse is a best-effort no-op.
        pass
    for key in NEW_IS:
        Translation.objects.filter(locale="is", key=key).delete()
```

The migration writer generates the actual `_hash_for` literal dict rather than a function call — each migration is self-contained and does not import the generator package (the generator is a dev-time tool, not a runtime dependency of migrations).

### `Translator` protocol

```python
from typing import Protocol

class Translator(Protocol):
    def translate(self, text: str, *, target_locale: str, source_locale: str = "en") -> str: ...
```

`DeepLTranslator(Translator)` wraps `https://api-free.deepl.com/v2/translate`. `StubTranslator(Translator)` (used in tests) returns `f"[{target_locale}] {text}"`.

---

## Task 1: Snapshot helpers (TDD)

**Files:**
- Create: `src/django-backend/apps/translations/generators/__init__.py`
- Create: `src/django-backend/apps/translations/generators/flatten.py`
- Create: `src/django-backend/apps/translations/generators/hashing.py`
- Create: `src/django-backend/apps/translations/generators/snapshot.py`
- Test: `src/django-backend/apps/translations/generators/test_flatten.py`
- Test: `src/django-backend/apps/translations/generators/test_snapshot.py`

- [ ] **Step 1: Start a changeset**

```bash
cd /Users/alex/Work/codalens/nglspn/nglspn-w1
jj new -m "feat(translations): snapshot + flatten + hashing helpers"
```

- [ ] **Step 2: Create package marker**

`src/django-backend/apps/translations/generators/__init__.py`:
```python
```

(Empty file. Package marker only.)

- [ ] **Step 3: Write failing test for flatten**

`src/django-backend/apps/translations/generators/test_flatten.py`:
```python
from apps.translations.generators.flatten import flatten_en


def test_flatten_flat_dict_is_unchanged() -> None:
    assert flatten_en({"a": "1", "b": "2"}) == {"a": "1", "b": "2"}


def test_flatten_nested_dict_uses_dotted_keys() -> None:
    assert flatten_en({"nav": {"home": "Home", "profile": "Profile"}}) == {
        "nav.home": "Home",
        "nav.profile": "Profile",
    }


def test_flatten_deep_nesting() -> None:
    assert flatten_en({"a": {"b": {"c": "deep"}}}) == {"a.b.c": "deep"}


def test_flatten_rejects_non_string_leaves() -> None:
    import pytest
    with pytest.raises(ValueError):
        flatten_en({"nav": {"home": 42}})  # type: ignore[dict-item]
```

- [ ] **Step 4: Run — expect ImportError**

Run: `cd src/django-backend && uv run pytest apps/translations/generators/test_flatten.py -v`
Expected: FAIL — module not found.

- [ ] **Step 5: Implement `flatten.py`**

`src/django-backend/apps/translations/generators/flatten.py`:
```python
from __future__ import annotations


def flatten_en(obj: dict) -> dict[str, str]:
    """Convert a nested en.json (dict of dicts of strings) into a flat dotted-key map."""
    out: dict[str, str] = {}
    _walk(obj, prefix="", out=out)
    return out


def _walk(node: dict, prefix: str, out: dict[str, str]) -> None:
    for key, value in node.items():
        full = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            _walk(value, prefix=full, out=out)
        elif isinstance(value, str):
            out[full] = value
        else:
            raise ValueError(f"en.json leaf at {full!r} is not a string: {value!r}")
```

- [ ] **Step 6: Run — expect PASS**

Run: `uv run pytest apps/translations/generators/test_flatten.py -v`
Expected: 4 passed.

- [ ] **Step 7: Implement `hashing.py`**

`src/django-backend/apps/translations/generators/hashing.py`:
```python
import hashlib


def source_hash(text: str) -> str:
    """Stable short hash of an English source string. Used to detect source drift."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
```

No separate test file; behavior is exercised through `test_snapshot.py`.

- [ ] **Step 8: Write failing test for snapshot read/write**

`src/django-backend/apps/translations/generators/test_snapshot.py`:
```python
from pathlib import Path

from apps.translations.generators.snapshot import Snapshot, read_snapshot, write_snapshot


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
    assert len(h) == 16 and all(c in "0123456789abcdef" for c in h)
```

- [ ] **Step 9: Run — expect ImportError**

Run: `uv run pytest apps/translations/generators/test_snapshot.py -v`
Expected: FAIL — module not found.

- [ ] **Step 10: Implement `snapshot.py`**

`src/django-backend/apps/translations/generators/snapshot.py`:
```python
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .flatten import flatten_en
from .hashing import source_hash


@dataclass(frozen=True)
class Snapshot:
    # key -> (english_text, source_hash)
    entries: dict[str, tuple[str, str]] = field(default_factory=dict)

    @classmethod
    def from_en_json(cls, en: dict) -> "Snapshot":
        flat = flatten_en(en)
        return cls(entries={k: (v, source_hash(v)) for k, v in flat.items()})


def read_snapshot(path: Path) -> Snapshot:
    if not path.exists():
        return Snapshot()
    raw = json.loads(path.read_text(encoding="utf-8"))
    return Snapshot(
        entries={k: (v["text"], v["source_hash"]) for k, v in raw.get("keys", {}).items()}
    )


def write_snapshot(path: Path, snap: Snapshot) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"keys": {k: {"text": t, "source_hash": h} for k, (t, h) in sorted(snap.entries.items())}}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
```

- [ ] **Step 11: Run — expect PASS**

Run: `uv run pytest apps/translations/generators/test_snapshot.py -v`
Expected: 3 passed.

- [ ] **Step 12: Commit**

```bash
jj commit -m "feat(translations): snapshot + flatten + hashing helpers"
```

---

## Task 2: Diff logic (TDD)

**Files:**
- Create: `src/django-backend/apps/translations/generators/diff.py`
- Test: `src/django-backend/apps/translations/generators/test_diff.py`

- [ ] **Step 1: Start a changeset**

```bash
jj new -m "feat(translations): en.json diff logic"
```

- [ ] **Step 2: Write failing test**

`src/django-backend/apps/translations/generators/test_diff.py`:
```python
from apps.translations.generators.diff import diff_snapshots, Diff
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
    assert diff_snapshots(old, new) == Diff(
        changed={"k": ("New text", "h_new")}
    )


def test_only_same_text_with_different_hash_is_not_a_change() -> None:
    # Defensive: same text -> same hash, so this can't normally happen. If it
    # does (corrupt snapshot), we don't treat it as a change.
    old = snap({"k": ("Same", "h_a")})
    new = snap({"k": ("Same", "h_b")})
    assert diff_snapshots(old, new) == Diff()
```

- [ ] **Step 3: Run — expect FAIL**

Run: `uv run pytest apps/translations/generators/test_diff.py -v`
Expected: ImportError.

- [ ] **Step 4: Implement `diff.py`**

`src/django-backend/apps/translations/generators/diff.py`:
```python
from __future__ import annotations

from dataclasses import dataclass, field

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
```

- [ ] **Step 5: Run — expect PASS**

Run: `uv run pytest apps/translations/generators/test_diff.py -v`
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
jj commit -m "feat(translations): en.json diff logic"
```

---

## Task 3: Translator protocol + DeepL client

**Files:**
- Create: `src/django-backend/apps/translations/generators/translator.py`

- [ ] **Step 1: Start a changeset**

```bash
jj new -m "feat(translations): Translator protocol + DeepL client"
```

- [ ] **Step 2: Write `translator.py`**

`src/django-backend/apps/translations/generators/translator.py`:
```python
from __future__ import annotations

import os
from typing import Protocol

import requests


class Translator(Protocol):
    def translate(self, text: str, *, target_locale: str, source_locale: str = "en") -> str: ...


class MissingCredentialsError(RuntimeError):
    pass


class DeepLTranslator:
    """Thin wrapper around the DeepL REST API.

    Uses DEEPL_AUTH_KEY from the environment. DeepL free tier lives at
    api-free.deepl.com; pro at api.deepl.com. The key's suffix (":fx") tells
    us which endpoint to use.
    """

    TIMEOUT_SECONDS = 30

    def __init__(self, auth_key: str | None = None) -> None:
        key = auth_key or os.environ.get("DEEPL_AUTH_KEY")
        if not key:
            raise MissingCredentialsError(
                "DEEPL_AUTH_KEY is not set. Get one at https://www.deepl.com/pro-api "
                "and export it before running `make translate-new-keys`."
            )
        self._key = key
        self._base = "https://api-free.deepl.com/v2" if key.endswith(":fx") else "https://api.deepl.com/v2"

    def translate(self, text: str, *, target_locale: str, source_locale: str = "en") -> str:
        response = requests.post(
            f"{self._base}/translate",
            data={
                "text": text,
                "source_lang": source_locale.upper(),
                "target_lang": target_locale.upper(),
                "preserve_formatting": "1",
                # Preserve ICU-style {placeholders} verbatim.
                "tag_handling": "xml",
                "ignore_tags": "icu",
            },
            headers={"Authorization": f"DeepL-Auth-Key {self._key}"},
            timeout=self.TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        return data["translations"][0]["text"]


class StubTranslator:
    """Deterministic translator used in tests. Returns f'[TARGET] text'."""

    def translate(self, text: str, *, target_locale: str, source_locale: str = "en") -> str:
        return f"[{target_locale}] {text}"
```

No unit test for `DeepLTranslator.translate` — it is thin glue around `requests`; integration is exercised manually in Task 10. `StubTranslator` is used across the rest of the tests.

- [ ] **Step 3: Commit**

```bash
jj commit -m "feat(translations): Translator protocol + DeepL client"
```

---

## Task 4: Migration writer (TDD)

**Files:**
- Create: `src/django-backend/apps/translations/generators/migration_writer.py`
- Test: `src/django-backend/apps/translations/generators/test_migration_writer.py`

- [ ] **Step 1: Start a changeset**

```bash
jj new -m "feat(translations): data-migration writer"
```

- [ ] **Step 2: Write failing test**

`src/django-backend/apps/translations/generators/test_migration_writer.py`:
```python
from apps.translations.generators.migration_writer import render_migration


def test_rendered_migration_has_expected_structure() -> None:
    text = render_migration(
        previous_migration="0003_seed_phase2_ui_chrome",
        added={"nav.new": ("Nýtt", "h_new")},
        retranslated={"nav.changed": ("Breytt", "h_changed")},
        source_hash_bumped={"nav.human_edited": "h_bumped"},
        retired=["old.key"],
    )

    # Dependency on the previous migration.
    assert '("translations", "0003_seed_phase2_ui_chrome")' in text
    # Inlined dicts.
    assert '"nav.new": ("Nýtt", "h_new")' in text
    assert '"nav.changed": ("Breytt", "h_changed")' in text
    assert '"nav.human_edited": "h_bumped"' in text
    assert '"old.key"' in text
    # Must be a valid Python module.
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
```

- [ ] **Step 3: Run — expect FAIL**

Run: `uv run pytest apps/translations/generators/test_migration_writer.py -v`
Expected: ImportError.

- [ ] **Step 4: Implement `migration_writer.py`**

`src/django-backend/apps/translations/generators/migration_writer.py`:
```python
from __future__ import annotations

import textwrap


def render_migration(
    *,
    previous_migration: str,
    added: dict[str, tuple[str, str]],
    retranslated: dict[str, tuple[str, str]],
    source_hash_bumped: dict[str, str],
    retired: list[str],
) -> str:
    """Return the source text of a Django data-migration file.

    - `added`: key -> (text, hash) — brand-new keys, MT'd.
    - `retranslated`: key -> (text, hash) — source changed, IS was still MT, re-translated.
    - `source_hash_bumped`: key -> new_hash — source changed, IS was human-edited; keep text, bump hash.
    - `retired`: keys whose English source disappeared.
    """
    body = textwrap.dedent(f'''\
        from django.db import migrations


        NEW_IS: dict[str, tuple[str, str]] = {_fmt_tuple_dict(added)}

        RETRANSLATED: dict[str, tuple[str, str]] = {_fmt_tuple_dict(retranslated)}

        SOURCE_HASH_BUMPED: dict[str, str] = {_fmt_str_dict(source_hash_bumped)}

        RETIRED: list[str] = {_fmt_list(retired)}


        def forward(apps, schema_editor):
            Translation = apps.get_model("translations", "Translation")
            for key, (text, src_hash) in NEW_IS.items():
                Translation.objects.update_or_create(
                    locale="is", key=key,
                    defaults={{
                        "text": text,
                        "source_hash": src_hash,
                        "is_machine_translated": True,
                        "retired": False,
                    }},
                )
            for key, (text, src_hash) in RETRANSLATED.items():
                Translation.objects.update_or_create(
                    locale="is", key=key,
                    defaults={{
                        "text": text,
                        "source_hash": src_hash,
                        "is_machine_translated": True,
                        "retired": False,
                    }},
                )
            for key, src_hash in SOURCE_HASH_BUMPED.items():
                Translation.objects.filter(locale="is", key=key).update(source_hash=src_hash)
            for key in RETIRED:
                Translation.objects.filter(locale="is", key=key).update(retired=True)


        def backward(apps, schema_editor):
            Translation = apps.get_model("translations", "Translation")
            for key in RETIRED:
                Translation.objects.filter(locale="is", key=key).update(retired=False)
            for key in NEW_IS:
                Translation.objects.filter(locale="is", key=key).delete()


        class Migration(migrations.Migration):
            dependencies = [("translations", "{previous_migration}")]
            operations = [migrations.RunPython(forward, backward)]
    ''')
    return body


def _fmt_tuple_dict(d: dict[str, tuple[str, str]]) -> str:
    if not d:
        return "{}"
    lines = [f"    {_repr(k)}: ({_repr(a)}, {_repr(b)})," for k, (a, b) in sorted(d.items())]
    return "{\n" + "\n".join(lines) + "\n}"


def _fmt_str_dict(d: dict[str, str]) -> str:
    if not d:
        return "{}"
    lines = [f"    {_repr(k)}: {_repr(v)}," for k, v in sorted(d.items())]
    return "{\n" + "\n".join(lines) + "\n}"


def _fmt_list(items: list[str]) -> str:
    if not items:
        return "[]"
    lines = [f"    {_repr(k)}," for k in sorted(items)]
    return "[\n" + "\n".join(lines) + "\n]"


def _repr(s: str) -> str:
    # Use Python's repr to escape non-ASCII / quotes consistently.
    return repr(s)
```

- [ ] **Step 5: Run — expect PASS**

Run: `uv run pytest apps/translations/generators/test_migration_writer.py -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
jj commit -m "feat(translations): data-migration writer"
```

---

## Task 5: Management command (end-to-end with stub translator)

**Files:**
- Create: `src/django-backend/apps/translations/management/__init__.py` (empty)
- Create: `src/django-backend/apps/translations/management/commands/__init__.py` (empty)
- Create: `src/django-backend/apps/translations/management/commands/generate_translations.py`
- Test: `src/django-backend/apps/translations/management/commands/test_generate_translations.py`

- [ ] **Step 1: Start a changeset**

```bash
jj new -m "feat(translations): generate_translations management command"
```

- [ ] **Step 2: Create package markers**

Both `management/__init__.py` and `management/commands/__init__.py` are empty files.

- [ ] **Step 3: Write failing end-to-end test**

`src/django-backend/apps/translations/management/commands/test_generate_translations.py`:
```python
import json
from pathlib import Path

import pytest
from django.core.management import call_command

from apps.translations.generators.translator import StubTranslator
from apps.translations.models import Translation


@pytest.fixture
def workspace(tmp_path: Path) -> dict[str, Path]:
    en = tmp_path / "en.json"
    snap = tmp_path / "en-snapshot.json"
    mig_dir = tmp_path / "migrations"
    mig_dir.mkdir()
    # Create a baseline snapshot so the migration dependency resolves.
    (mig_dir / "0099_baseline.py").write_text("# placeholder\n", encoding="utf-8")
    return {"en_json": en, "snapshot": snap, "migrations": mig_dir}


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


@pytest.mark.django_db
def test_new_keys_are_translated_and_written_to_migration(workspace) -> None:
    write_json(workspace["en_json"], {"nav": {"home": "Home"}})

    call_command(
        "generate_translations",
        "--en-json", str(workspace["en_json"]),
        "--snapshot", str(workspace["snapshot"]),
        "--migrations-dir", str(workspace["migrations"]),
        "--previous-migration", "0099_baseline",
        "--translator", "stub",
    )

    # Generated migration file exists
    generated = sorted(workspace["migrations"].glob("01*_translate_new_keys.py"))
    assert len(generated) == 1, list(workspace["migrations"].iterdir())

    content = generated[0].read_text(encoding="utf-8")
    assert "nav.home" in content
    assert "[is] Home" in content  # StubTranslator output

    # Snapshot has been updated
    assert json.loads(workspace["snapshot"].read_text(encoding="utf-8"))["keys"]["nav.home"]["text"] == "Home"


@pytest.mark.django_db
def test_no_changes_writes_no_migration_and_exits_zero(workspace) -> None:
    write_json(workspace["en_json"], {"nav": {"home": "Home"}})
    # Pre-seed the snapshot to match so there's no diff.
    write_json(
        workspace["snapshot"],
        {"keys": {"nav.home": {"text": "Home", "source_hash": "0" * 16}}},
    )

    # Even with matching snapshot, the hash will differ (stale). First run will
    # detect no TEXT change and write no migration; snapshot still gets updated
    # to the canonical hash.
    call_command(
        "generate_translations",
        "--en-json", str(workspace["en_json"]),
        "--snapshot", str(workspace["snapshot"]),
        "--migrations-dir", str(workspace["migrations"]),
        "--previous-migration", "0099_baseline",
        "--translator", "stub",
    )

    assert not list(workspace["migrations"].glob("01*_translate_new_keys.py"))


@pytest.mark.django_db
def test_changed_source_with_human_edited_is_bumps_hash_only(workspace) -> None:
    # Previous snapshot had old English; the IS row is already human-edited.
    write_json(
        workspace["snapshot"],
        {"keys": {"nav.home": {"text": "Home OLD", "source_hash": "h_old"}}},
    )
    write_json(workspace["en_json"], {"nav": {"home": "Home NEW"}})
    Translation.objects.create(
        locale="is", key="nav.home", text="Heim (manually edited)",
        source_hash="h_old", is_machine_translated=False,
    )

    call_command(
        "generate_translations",
        "--en-json", str(workspace["en_json"]),
        "--snapshot", str(workspace["snapshot"]),
        "--migrations-dir", str(workspace["migrations"]),
        "--previous-migration", "0099_baseline",
        "--translator", "stub",
    )

    generated = sorted(workspace["migrations"].glob("01*_translate_new_keys.py"))
    assert len(generated) == 1
    content = generated[0].read_text(encoding="utf-8")
    # Only a hash bump, no retranslation.
    assert "SOURCE_HASH_BUMPED" in content
    assert "nav.home" in content
    assert "[is] Home NEW" not in content  # IS row NOT overwritten


@pytest.mark.django_db
def test_changed_source_with_mt_row_is_retranslated(workspace) -> None:
    write_json(
        workspace["snapshot"],
        {"keys": {"nav.home": {"text": "Home OLD", "source_hash": "h_old"}}},
    )
    write_json(workspace["en_json"], {"nav": {"home": "Home NEW"}})
    Translation.objects.create(
        locale="is", key="nav.home", text="Heim",
        source_hash="h_old", is_machine_translated=True,
    )

    call_command(
        "generate_translations",
        "--en-json", str(workspace["en_json"]),
        "--snapshot", str(workspace["snapshot"]),
        "--migrations-dir", str(workspace["migrations"]),
        "--previous-migration", "0099_baseline",
        "--translator", "stub",
    )

    content = (workspace["migrations"] / sorted(p.name for p in workspace["migrations"].glob("01*_translate_new_keys.py"))[0]).read_text(encoding="utf-8")
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
        "--en-json", str(workspace["en_json"]),
        "--snapshot", str(workspace["snapshot"]),
        "--migrations-dir", str(workspace["migrations"]),
        "--previous-migration", "0099_baseline",
        "--translator", "stub",
    )

    content = (workspace["migrations"] / sorted(p.name for p in workspace["migrations"].glob("01*_translate_new_keys.py"))[0]).read_text(encoding="utf-8")
    assert '"gone.key"' in content
    assert "RETIRED" in content
```

- [ ] **Step 4: Run — expect FAIL**

Run: `uv run pytest apps/translations/management/commands/test_generate_translations.py -v`
Expected: FAIL (no command defined).

- [ ] **Step 5: Implement `generate_translations.py`**

`src/django-backend/apps/translations/management/commands/generate_translations.py`:
```python
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.translations.generators.diff import Diff, diff_snapshots
from apps.translations.generators.migration_writer import render_migration
from apps.translations.generators.snapshot import Snapshot, read_snapshot, write_snapshot
from apps.translations.generators.translator import (
    DeepLTranslator,
    MissingCredentialsError,
    StubTranslator,
    Translator,
)
from apps.translations.models import Translation


@dataclass
class Buckets:
    added: dict[str, tuple[str, str]]           # key -> (is_text, source_hash)
    retranslated: dict[str, tuple[str, str]]    # key -> (is_text, source_hash)
    source_hash_bumped: dict[str, str]          # key -> source_hash
    retired: list[str]


class Command(BaseCommand):
    help = "Diff en.json against the committed snapshot and write a Django data migration."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--en-json", required=True, type=Path)
        parser.add_argument("--snapshot", required=True, type=Path)
        parser.add_argument("--migrations-dir", required=True, type=Path)
        parser.add_argument("--previous-migration", required=True, type=str)
        parser.add_argument(
            "--translator",
            choices=["deepl", "stub"],
            default="deepl",
            help="Which translator to use. 'stub' is used in tests.",
        )
        parser.add_argument("--target-locale", default="is")

    def handle(self, *args, **opts) -> None:
        en_path: Path = opts["en_json"]
        snap_path: Path = opts["snapshot"]
        mig_dir: Path = opts["migrations_dir"]
        prev_mig: str = opts["previous_migration"]
        target_locale: str = opts["target_locale"]

        if not en_path.exists():
            raise CommandError(f"en.json not found: {en_path}")

        old_snap = read_snapshot(snap_path)
        new_snap = Snapshot.from_en_json(json.loads(en_path.read_text(encoding="utf-8")))
        diff = diff_snapshots(old_snap, new_snap)

        if not (diff.added or diff.changed or diff.removed):
            self.stdout.write("No translation changes to generate.")
            write_snapshot(snap_path, new_snap)
            return

        translator = self._get_translator(opts["translator"])
        buckets = self._bucket_changes(diff, target_locale=target_locale, translator=translator)

        if not (buckets.added or buckets.retranslated or buckets.source_hash_bumped or buckets.retired):
            self.stdout.write("No migration needed (all changes were hash-equivalent).")
            write_snapshot(snap_path, new_snap)
            return

        next_num = self._next_migration_number(mig_dir)
        out_path = mig_dir / f"{next_num:04d}_translate_new_keys.py"
        out_path.write_text(
            render_migration(
                previous_migration=prev_mig,
                added=buckets.added,
                retranslated=buckets.retranslated,
                source_hash_bumped=buckets.source_hash_bumped,
                retired=buckets.retired,
            ),
            encoding="utf-8",
        )
        write_snapshot(snap_path, new_snap)
        self.stdout.write(f"Wrote {out_path} and updated {snap_path}.")

    def _get_translator(self, kind: str) -> Translator:
        if kind == "stub":
            return StubTranslator()
        try:
            return DeepLTranslator()
        except MissingCredentialsError as exc:
            raise CommandError(str(exc)) from exc

    def _bucket_changes(
        self, diff: Diff, *, target_locale: str, translator: Translator
    ) -> Buckets:
        added: dict[str, tuple[str, str]] = {}
        retranslated: dict[str, tuple[str, str]] = {}
        source_hash_bumped: dict[str, str] = {}

        for key, (en_text, new_hash) in diff.added.items():
            is_text = translator.translate(en_text, target_locale=target_locale)
            added[key] = (is_text, new_hash)

        # For changed keys, decide per-row based on whether the existing IS row was human-edited.
        existing_rows = {
            t.key: t
            for t in Translation.objects.filter(
                locale=target_locale, key__in=list(diff.changed)
            )
        }
        for key, (en_text, new_hash) in diff.changed.items():
            row = existing_rows.get(key)
            if row is None or row.is_machine_translated:
                is_text = translator.translate(en_text, target_locale=target_locale)
                retranslated[key] = (is_text, new_hash)
            else:
                source_hash_bumped[key] = new_hash

        return Buckets(
            added=added,
            retranslated=retranslated,
            source_hash_bumped=source_hash_bumped,
            retired=sorted(diff.removed),
        )

    def _next_migration_number(self, mig_dir: Path) -> int:
        nums: list[int] = []
        for p in mig_dir.glob("*.py"):
            stem = p.stem
            if stem == "__init__":
                continue
            prefix = stem.split("_", 1)[0]
            if prefix.isdigit():
                nums.append(int(prefix))
        return (max(nums) + 1) if nums else 1
```

- [ ] **Step 6: Run — expect PASS**

Run: `uv run pytest apps/translations/management/commands/test_generate_translations.py -v`
Expected: 5 passed.

- [ ] **Step 7: Full backend test run**

Run: `cd src/django-backend && make test`
Expected: all tests pass (baseline 530+ plus ~14 new).

- [ ] **Step 8: Commit**

```bash
jj commit -m "feat(translations): generate_translations management command"
```

---

## Task 6: Makefile target `translate-new-keys`

**Files:**
- Modify: `src/django-backend/Makefile`

- [ ] **Step 1: Start a changeset**

```bash
jj new -m "feat(translations): make translate-new-keys target"
```

- [ ] **Step 2: Edit Makefile**

Append to `.PHONY` list (find the existing `.PHONY:=` line at the top and add `translate-new-keys`):

```makefile
.PHONY: help install dev migrate makemigrations shell test createsuperuser clean extract-openapi lint bootstrap seed seed-prod-copy dev-services dev-services-down translate-new-keys lint-translations
```

Append these targets at the end of the file:

```makefile
# Regenerate Icelandic translations from the current web-ui en.json.
# Requires DEEPL_AUTH_KEY in the environment (see README).
translate-new-keys:
	@: $${DEEPL_AUTH_KEY?DEEPL_AUTH_KEY must be set. Get a free key at https://www.deepl.com/pro-api}
	uv run python manage.py generate_translations \
	  --en-json ../../src/web-ui/src/messages/en.json \
	  --snapshot apps/translations/generators/state/en-snapshot.json \
	  --migrations-dir apps/translations/migrations \
	  --previous-migration $$(ls apps/translations/migrations | grep -E '^[0-9]{4}_' | sort | tail -1 | sed 's/\.py$$//')

# Verify the web-ui en.json is in sync with the snapshot (no un-migrated changes).
lint-translations:
	uv run python manage.py generate_translations \
	  --en-json ../../src/web-ui/src/messages/en.json \
	  --snapshot apps/translations/generators/state/en-snapshot.json \
	  --migrations-dir /tmp/trans-lint-$$$$ \
	  --previous-migration dummy \
	  --translator stub >/tmp/trans-lint-out 2>&1; \
	if ls /tmp/trans-lint-$$$$/ 2>/dev/null | grep -q .; then \
	  echo "translate-new-keys has pending changes — run it locally and commit the migration."; \
	  cat /tmp/trans-lint-out; rm -rf /tmp/trans-lint-$$$$; exit 1; \
	fi; \
	rm -rf /tmp/trans-lint-$$$$
```

The `lint-translations` target uses the stub translator in a throwaway temp dir. It exits non-zero if the generator would have produced a migration — i.e. if the snapshot file is stale relative to `en.json`.

- [ ] **Step 3: Commit the Makefile change**

```bash
jj commit -m "feat(translations): make translate-new-keys + lint-translations"
```

---

## Task 7: Seed the snapshot from current en.json

**Files:**
- Create: `src/django-backend/apps/translations/generators/state/en-snapshot.json`

- [ ] **Step 1: Start a changeset**

```bash
jj new -m "chore(translations): seed en-snapshot.json from current en.json"
```

- [ ] **Step 2: Write the snapshot programmatically**

Run from `src/django-backend`:
```bash
uv run python -c "
import json, pathlib
from apps.translations.generators.snapshot import Snapshot, write_snapshot
en = json.loads(pathlib.Path('../../src/web-ui/src/messages/en.json').read_text())
write_snapshot(pathlib.Path('apps/translations/generators/state/en-snapshot.json'), Snapshot.from_en_json(en))
print('snapshot written')
"
```

Expected output: `snapshot written`.

- [ ] **Step 3: Verify `make lint-translations` passes**

```bash
make lint-translations
```
Expected: no output, exit 0. (If it prints "pending changes", the snapshot doesn't match en.json — regenerate.)

- [ ] **Step 4: Commit**

```bash
jj commit -m "chore(translations): seed en-snapshot.json from current en.json"
```

---

## Task 8: Web-UI lint script — every `t()` key must exist in en.json (TDD-ish)

**Files:**
- Create: `src/web-ui/scripts/lint-i18n.mjs`
- Modify: `src/web-ui/package.json`

- [ ] **Step 1: Start a changeset**

```bash
jj new -m "feat(web-ui): lint script verifies t() keys exist in en.json"
```

- [ ] **Step 2: Write `scripts/lint-i18n.mjs`**

```js
#!/usr/bin/env node
// Scan .ts/.tsx under src/ and verify every t("key") call references a key that
// exists in src/messages/en.json. Resolves namespaces from useTranslations("ns").

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const srcDir = path.join(root, "src");
const enJsonPath = path.join(srcDir, "messages", "en.json");

const en = JSON.parse(fs.readFileSync(enJsonPath, "utf-8"));

function flatten(obj, prefix = "") {
  const out = new Set();
  for (const [k, v] of Object.entries(obj)) {
    const full = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === "object" && !Array.isArray(v)) {
      for (const x of flatten(v, full)) out.add(x);
    } else if (typeof v === "string") {
      out.add(full);
    }
  }
  return out;
}

const knownKeys = flatten(en);

function walk(dir) {
  const results = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === "node_modules" || entry.name.startsWith(".")) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...walk(full));
    } else if (/\.(tsx?|mts|cts)$/.test(entry.name) && !entry.name.endsWith(".d.ts")) {
      results.push(full);
    }
  }
  return results;
}

// Match useTranslations("ns") declarations and t("key") calls. Regex-based;
// good enough because we control the codebase style and don't need to handle
// dynamic keys. Dynamic keys (t(variable)) are flagged as "unresolvable" below.
const useTranslationsRe = /useTranslations\(\s*["']([^"']+)["']\s*\)/g;
const tCallRe = /\bt\(\s*["']([^"']+)["']\s*/g;

const problems = [];

for (const file of walk(srcDir)) {
  const contents = fs.readFileSync(file, "utf-8");
  const namespaces = [];
  for (const m of contents.matchAll(useTranslationsRe)) {
    namespaces.push(m[1]);
  }
  // If a file uses multiple useTranslations(), the most specific resolution
  // becomes ambiguous. Accept the key under ANY of the declared namespaces.
  for (const m of contents.matchAll(tCallRe)) {
    const sub = m[1];
    if (namespaces.length === 0) {
      // Bare t("ns.key") — resolve as a fully-qualified dotted key.
      if (!knownKeys.has(sub)) {
        problems.push({ file, key: sub, hint: "unknown key (no namespace in scope)" });
      }
      continue;
    }
    const resolvedForms = namespaces.map((ns) => `${ns}.${sub}`);
    if (!resolvedForms.some((k) => knownKeys.has(k))) {
      problems.push({
        file,
        key: sub,
        hint: `none of ${resolvedForms.join(", ")} exist in en.json`,
      });
    }
  }
}

if (problems.length === 0) {
  process.exit(0);
}

for (const p of problems) {
  console.error(`[i18n-lint] ${path.relative(root, p.file)}: ${p.key} — ${p.hint}`);
}
console.error(`\n${problems.length} i18n problem(s) found. Add the missing keys to src/messages/en.json or remove the t() call.`);
process.exit(1);
```

- [ ] **Step 3: Wire into `package.json`**

Read `src/web-ui/package.json`. Change the `"lint"` script from:

```json
"lint": "eslint && tsc --noEmit"
```

to:

```json
"lint": "eslint && tsc --noEmit && node scripts/lint-i18n.mjs",
"lint:i18n": "node scripts/lint-i18n.mjs"
```

Leave other scripts unchanged.

- [ ] **Step 4: Run — expect pass**

```bash
cd src/web-ui && npm run lint
```
Expected: 0 errors, the same 2 pre-existing `reset` warnings as before.

- [ ] **Step 5: Negative test — introduce a bad t() call, verify failure**

Temporarily edit `src/web-ui/src/components/Footer.tsx` and change one `{t("about")}` to `{t("doesNotExist")}`. Run:

```bash
cd src/web-ui && npm run lint:i18n
```
Expected: exits non-zero with a message naming `Footer.tsx` and key `doesNotExist`.

Revert the change. Run `npm run lint:i18n` again — exits 0.

- [ ] **Step 6: Commit**

```bash
jj commit -m "feat(web-ui): lint script verifies t() keys exist in en.json"
```

---

## Task 9: Wire both lints into `make ci`

**Files:**
- Modify: repo-root `Makefile` (or `scripts/ci/...` if `make ci` lives there — inspect first).

- [ ] **Step 1: Inspect the current CI gate**

Run:
```bash
cat /Users/alex/Work/codalens/nglspn/nglspn-w1/Makefile
ls /Users/alex/Work/codalens/nglspn/nglspn-w1/scripts/ci/
```

Identify the target that ties together `make lint` across subsystems. That target gets two additions: `make -C src/django-backend lint-translations` and the web-ui `npm run lint` call (already present; verify).

- [ ] **Step 2: Start a changeset**

```bash
jj new -m "ci: gate translation snapshot drift + t() key resolution"
```

- [ ] **Step 3: Add `lint-translations` to the CI gate**

If `make ci` calls `make -C src/django-backend lint` and `cd src/web-ui && npm run lint` (or similar) — add a call to `make -C src/django-backend lint-translations` right after the Django `lint`. Do NOT re-run the web-ui lint; `npm run lint` already invokes `lint-i18n.mjs` after Task 8's wiring.

Exact edit depends on the existing file shape. If the root Makefile has:

```makefile
ci: lint test
```

and `lint` is:

```makefile
lint:
	$(MAKE) -C src/django-backend lint
	cd src/web-ui && npm run lint
```

then change it to:

```makefile
lint:
	$(MAKE) -C src/django-backend lint
	$(MAKE) -C src/django-backend lint-translations
	cd src/web-ui && npm run lint
```

- [ ] **Step 4: Verify**

```bash
cd /Users/alex/Work/codalens/nglspn/nglspn-w1 && make ci
```
Expected: pass cleanly.

- [ ] **Step 5: Commit**

```bash
jj commit -m "ci: gate translation snapshot drift + t() key resolution"
```

---

## Task 10: Manual DeepL smoke test

**Files:**
- None (verification only).

This task exists because `DeepLTranslator` has no unit test; it is the integration point to a third-party service and we validate it once, by hand, with a real key.

- [ ] **Step 1: Get a DeepL API key**

Sign up at https://www.deepl.com/pro-api (free tier). Export locally:
```bash
export DEEPL_AUTH_KEY=<your-key>:fx
```

Free-tier keys end in `:fx`; `DeepLTranslator` auto-routes to the free endpoint on that suffix.

- [ ] **Step 2: Add a throwaway English string**

Edit `src/web-ui/src/messages/en.json` — add a temporary key like:
```json
"test": { "smoke": "Hello, this is a test string." }
```

- [ ] **Step 3: Run the generator against a real DeepL**

```bash
cd src/django-backend
make translate-new-keys
```
Expected:
- Exits 0.
- Prints `Wrote apps/translations/migrations/NNNN_translate_new_keys.py and updated ...`.
- The generated migration contains an Icelandic translation of the test string (not `[is] Hello...`).

- [ ] **Step 4: Inspect the output**

Open the generated migration file. Confirm the IS text looks like real Icelandic (e.g. starts with `Halló, þetta er...`). If it is obviously broken or empty, report and pause — pick a different provider or file a bug.

- [ ] **Step 5: Revert the throwaway change**

Delete the new migration, restore `en.json`, restore `en-snapshot.json`. Do NOT commit the smoke-test output.

```bash
jj abandon @  # if you happened to commit
```

- [ ] **Step 6: Document the outcome**

Write one sentence in the Phase 3 completion note in the terminal output of the verification agent: "DeepL smoke: `<sample IS translation>` — looks native / doesn't look native." No commit; the note is session-only.

---

## Task 11: Developer docs

**Files:**
- Modify: `/Users/alex/Work/codalens/nglspn/nglspn-w1/CLAUDE.md`
- Modify: `/Users/alex/Work/codalens/nglspn/nglspn-w1/src/web-ui/README.md` or create a short `docs/translations.md`

- [ ] **Step 1: Start a changeset**

```bash
jj new -m "docs(translations): authoring workflow"
```

- [ ] **Step 2: Add a short section to `CLAUDE.md`**

Under the existing structure (e.g. after "OpenAPI Workflow"), add:

```markdown
### Translations Workflow

When you add a `t('new.key')` call in the web-ui:

1. Add the key to `src/web-ui/src/messages/en.json`.
2. Export `DEEPL_AUTH_KEY` (get one free at https://www.deepl.com/pro-api — free-tier keys end in `:fx`).
3. From `src/django-backend`, run `make translate-new-keys`. This:
   - Diffs `en.json` against `apps/translations/generators/state/en-snapshot.json`.
   - Calls DeepL for new keys (and for changed keys whose IS row is still machine-translated).
   - Bumps `source_hash` only (no retranslation) for changed keys whose IS row has been human-edited.
   - Marks removed keys as `retired=True`.
   - Writes a new Django data migration + updates the snapshot.
4. Commit the generated migration + the updated snapshot in the same PR as your code change.

CI runs `make lint-translations` which fails if `en.json` and the snapshot have drifted — i.e. someone added a key without running `make translate-new-keys`.

CI also runs the web-ui's `npm run lint`, which now includes `scripts/lint-i18n.mjs`: every `t("key")` call in a `.ts`/`.tsx` file must resolve to a key in `en.json`.
```

- [ ] **Step 3: Commit**

```bash
jj commit -m "docs(translations): authoring workflow"
```

---

## Task 12: Full CI gate

- [ ] **Step 1: Run the full gate**

```bash
cd /Users/alex/Work/codalens/nglspn/nglspn-w1
make ci
```
Expected: pass.

- [ ] **Step 2: Confirm nothing else drifted**

- Web-ui dev server starts cleanly (`cd src/web-ui && npm run dev`, visit `/`, quit).
- `make test` in django-backend still prints `PASS` and the full count is ≥ prior baseline plus the ~17 new tests added in Tasks 1/2/4/5.

If anything fails, fix in place and commit as `chore: CI gate cleanup for Phase 3`. If nothing fails, do not add a commit.

---

## Done

At the end of Phase 3:
- A developer adds `t('foo.bar')` in the web-ui, adds `"foo": {"bar": "..."}` to `en.json`, runs `make translate-new-keys`, and gets a committable migration with an Icelandic translation.
- CI fails if anyone ships a `t()` call that references a non-existent key.
- CI fails if anyone changes `en.json` without running the generator.
- Human-edited IS text is never clobbered by re-running the generator; source-hash drift is flagged for the editor worklist (Phase 5 consumes this).

Next session: write Phase 4 plan (inline edit UX: `<Translatable>`, pencil-on-hover, popover, history, revert, optimistic update).
