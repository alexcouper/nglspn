"""Taxonomy tooling, driven off the public API.

    python -m scripts.taxonomy export --output /tmp/taxonomy-projects.json
    python -m scripts.taxonomy check ../../docs/taxonomy/2026-08-21-report.json
    python -m scripts.taxonomy diff ../../docs/taxonomy/2026-08-21-report.json

Both default to a local backend; pass --api-url https://api.naglasupan.is/api
to work against production. Standard library only: no database, no Django.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from scripts.taxonomy.api import DEFAULT_API_URL, ApiError, fetch_snapshot
from scripts.taxonomy.diff import render_diff
from scripts.taxonomy.verify import verify_report


def _add_api_url(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"Backend API base URL (default: {DEFAULT_API_URL})",
    )


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m scripts.taxonomy")
    commands = parser.add_subparsers(dest="command", required=True)

    export = commands.add_parser("export", help="Dump approved projects as JSON")
    _add_api_url(export)
    export.add_argument("--output", help="Write here instead of stdout")

    check = commands.add_parser("check", help="Verify a taxonomy report")
    _add_api_url(check)
    check.add_argument("report", help="Path to the report JSON")
    check.add_argument(
        "--snapshot",
        help="Check against this export file instead of re-fetching from the API",
    )
    diff = commands.add_parser(
        "diff", help="Render a report as a human-readable Markdown diff"
    )
    diff.add_argument("report", help="Path to the report JSON")
    diff.add_argument("--output", help="Write here instead of stdout")

    return parser.parse_args(argv)


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"error: no file at {path}", file=sys.stderr)
        raise SystemExit(2) from None
    except json.JSONDecodeError as exc:
        print(f"error: {path} is not valid JSON: {exc}", file=sys.stderr)
        raise SystemExit(2) from None


def _run_export(args: argparse.Namespace) -> int:
    snapshot = fetch_snapshot(args.api_url)
    text = json.dumps(snapshot, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(f"Wrote {snapshot['project_count']} projects to {args.output}")
    else:
        print(text)
    return 0


def _run_check(args: argparse.Namespace) -> int:
    report_path = Path(args.report)
    report = _load_json(report_path)
    if args.snapshot:
        snapshot = _load_json(Path(args.snapshot))
    else:
        snapshot = fetch_snapshot(args.api_url)

    result = verify_report(report, snapshot)
    for warning in result.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if not result.ok:
        for error in result.errors:
            print(f"error: {error}", file=sys.stderr)
        print(f"{report_path}: {len(result.errors)} error(s)", file=sys.stderr)
        return 1
    print(
        f"{report_path}: OK - {result.project_count} projects covered, "
        f"{len(result.warnings)} warning(s)"
    )
    return 0


def _run_diff(args: argparse.Namespace) -> int:
    markdown = render_diff(_load_json(Path(args.report)))
    if args.output:
        Path(args.output).write_text(markdown, encoding="utf-8")
        print(f"Wrote the diff to {args.output}")
    else:
        print(markdown, end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        if args.command == "export":
            return _run_export(args)
        if args.command == "diff":
            return _run_diff(args)
        return _run_check(args)
    except ApiError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
