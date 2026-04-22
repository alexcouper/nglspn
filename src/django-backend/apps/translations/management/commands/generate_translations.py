from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.translations.generators.diff import Diff, diff_snapshots
from apps.translations.generators.migration_writer import render_migration
from apps.translations.generators.snapshot import (
    Snapshot,
    read_snapshot,
    write_snapshot,
)
from apps.translations.generators.translator import (
    DeepLTranslator,
    MissingCredentialsError,
    StubTranslator,
    Translator,
)
from apps.translations.models import Translation


@dataclass
class Buckets:
    added: dict[str, tuple[str, str]]
    retranslated: dict[str, tuple[str, str]]
    source_hash_bumped: dict[str, str]
    retired: list[str]


class Command(BaseCommand):
    help = "Diff en.json against the snapshot and write a Django data migration."

    def add_arguments(self, parser: object) -> None:
        parser.add_argument("--en-json", required=True, type=Path)
        parser.add_argument("--snapshot", required=True, type=Path)
        parser.add_argument("--migrations-dir", required=True, type=Path)
        parser.add_argument("--previous-migration", required=True, type=str)
        parser.add_argument(
            "--translator",
            choices=["deepl", "stub"],
            default="deepl",
        )
        parser.add_argument("--target-locale", default="is")

    def handle(self, *args, **opts) -> None:
        en_path: Path = opts["en_json"]
        snap_path: Path = opts["snapshot"]
        mig_dir: Path = opts["migrations_dir"]
        prev_mig: str = opts["previous_migration"]
        target_locale: str = opts["target_locale"]

        if not en_path.exists():
            msg = f"en.json not found: {en_path}"
            raise CommandError(msg)

        old_snap = read_snapshot(snap_path)
        new_snap = Snapshot.from_en_json(
            json.loads(en_path.read_text(encoding="utf-8"))
        )
        diff = diff_snapshots(old_snap, new_snap)

        if not (diff.added or diff.changed or diff.removed):
            self.stdout.write("No translation changes to generate.")
            write_snapshot(snap_path, new_snap)
            return

        translator = self._get_translator(opts["translator"])
        buckets = self._bucket_changes(
            diff, target_locale=target_locale, translator=translator
        )

        if not (
            buckets.added
            or buckets.retranslated
            or buckets.source_hash_bumped
            or buckets.retired
        ):
            self.stdout.write("No migration needed.")
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
