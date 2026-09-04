# Documentation map & conventions

How documentation is organised in this repo, and how to decide where a new piece
of writing belongs. The goal is that every fact has **one** home, and you can
find it. This file is the source of truth the `nglspn-docs` skill is built from.

## Where each kind of doc lives

| Doc | Path | Holds |
|-----|------|-------|
| **README** | `README.md` | The pitch and getting-started. The "why" and the first five minutes — not reference detail. |
| **Contributing** | `CONTRIBUTING.md` | How to set up, run, test, and ship a change. Branch/PR conventions, the workflows that bite. |
| **This map** | `docs.md` | The documentation taxonomy and house style. Meta-doc. |
| **Design rationale / investigations** | `docs/<date>-<topic>.md` | One-off design write-ups, performance analyses, bug post-mortems. Dated, topic-named. |
| **Brainstormed specs** | `docs/superpowers/specs/<date>-<topic>-design.md` | Validated designs produced through the brainstorming flow, before they become OpenSpec changes. |
| **OpenSpec changes** | `openspec/changes/<name>/` | Multi-step / architectural change plans: `proposal.md`, `design.md`, `specs/`, `tasks.md`. The plan of record while work is in flight. |
| **OpenSpec specs** | `openspec/specs/` | Capability specs that have landed — the current intended behaviour. |
| **Taxonomy reports** | `docs/taxonomy/<date>-report.json` | Proposals for regrouping projects into categories: every project, its current category and the proposed one. Written by the `nglspn-taxonomy` skill, checked by `python3 -m scripts.taxonomy check`, applied by `manage.py apply_taxonomy`. |
| **Taxonomy charts** | `docs/taxonomy/charts/` | Sankey diagrams of a taxonomy report, for explaining a re-categorisation publicly. Generated from the newest report by `make_charts.py` — see [its README](docs/taxonomy/charts/README.md). |
| **Assistant guidance** | `CLAUDE.md` | Repo facts and commands an AI assistant needs every session. Keep it current and short. |
| **Skills** | `.claude/skills/<name>/SKILL.md` | Procedural knowledge an assistant invokes on demand (code review, docs). |
| **Inline** | docstrings, code comments | The "why" next to non-obvious code. The "what" should be the code itself. |

## Which doc am I about to write?

| You're about to… | Write it as… |
|------------------|--------------|
| Explain what the project is or how to start it | `README.md` |
| Document a setup step, command, or PR convention | `CONTRIBUTING.md` |
| Plan a multi-step or architectural change | An **OpenSpec change** under `openspec/changes/<name>/` |
| Capture a validated design from brainstorming | `docs/superpowers/specs/<date>-<topic>-design.md` |
| Write up the rationale behind one decision, an investigation, or a post-mortem | `docs/<date>-<topic>.md` |
| Propose a new grouping of projects into categories | A **taxonomy report** under `docs/taxonomy/` (the `nglspn-taxonomy` skill) |
| Record a command or fact every assistant session needs | `CLAUDE.md` |
| Capture a reusable procedure an assistant should follow | A skill under `.claude/skills/` |
| Explain why a specific line is the way it is | An inline comment or docstring |

When two homes seem plausible, prefer the **more specific** one and link to it
from the more general one, rather than copying the content.

## Naming conventions

- **Dated docs** (`docs/`, `docs/superpowers/specs/`) lead with an ISO date:
  `2026-05-11-rework-voting-ux.md`. The date is when the doc was written, not a
  deadline.
- **OpenSpec changes** use a verb-led kebab name describing the change:
  `add-article-authoring`, `simplify-follow-and-cadence`.
- **Skills** are prefixed `nglspn-` to mark them as repo-local:
  `nglspn-code-review`, `nglspn-docs`, `nglspn-taxonomy`.

## House style

The same bar as the code-review skill — readers trust terse, concrete docs and
skim padded ones.

- **Lead with the consequence, not the abstraction.** "Forgetting this leaves the
  frontend on a stale contract" beats "type synchronisation is important."
- **One fact, one home.** Link (`[label](path)`) instead of restating. A fact in
  two places drifts in one.
- **Concrete over hand-wavy.** Name the file, the command, the function. Cite
  `path:line` where it helps.
- **Scale to the topic.** A sentence where a sentence does; a section where the
  nuance earns it. No filler headings.
- **Mark the sharp edges.** Use `BREAKING` markers in OpenSpec proposals, and
  call out the foot-guns (OpenAPI regen, migrations, IP trust, kennitala PII)
  explicitly — those are what bite.
- **Icelandic product, English docs.** User-facing strings are Icelandic; the
  docs and code are in English.

## Keeping docs current

- A change that alters a **command or workflow** updates `CONTRIBUTING.md` and
  `CLAUDE.md` in the same PR.
- A change that touches the **API contract** regenerates `backend-openapi.json`
  (see `CONTRIBUTING.md` → "The API contract").
- When an OpenSpec change **lands**, its intent moves from `openspec/changes/`
  into the archived/landed specs — don't leave a completed plan describing the
  current state as if it were still future work.
- Delete docs that have gone stale rather than leaving them to mislead. A wrong
  doc is worse than no doc.
