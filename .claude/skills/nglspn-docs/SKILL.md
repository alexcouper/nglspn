---
name: nglspn-docs
description: >-
  Documentation authoring for the Naglasúpan (nglspn) repo. Use this whenever you
  write or update any documentation here — README, CONTRIBUTING, a design doc or
  investigation under docs/, an OpenSpec change (proposal/design/specs/tasks), a
  validated design spec, CLAUDE.md guidance, or another skill — and whenever the
  user says "document this", "write it up", "add a doc", "write a design doc",
  "update the README", or "open an openspec change" in this repository. It knows
  the repo's documentation taxonomy (where each kind of doc belongs), naming
  conventions, and the terse house style, so docs land in the right place and one
  fact has one home.
---

# Naglasúpan Documentation

You are writing or updating documentation in this repository. Your job is to put
the right content in the right place, in the repo's terse, concrete voice, so a
future reader (human or assistant) finds what they need and trusts it.

The full taxonomy and style rules live in [`docs.md`](../../../docs.md) at the
repo root — that file is the source of truth; this skill is how you apply it.
Read it when you need the complete table.

## The repo in one breath

- **Backend** `src/django-backend/` — Django 4.2 + Django Ninja, Python 3.12,
  `uv`, Ruff, pytest. Layered: routers → `HANDLERS`/`REPO` services → models.
- **Frontend** `src/web-ui/` — Next.js 16 App Router, React 19, TypeScript,
  generated API types.
- **Infra** `infra/prod/app/` — Terraform.
- The product is Icelandic (`naglasupan.is`); user-facing strings are Icelandic,
  docs and code are English.

## Step 1 — pick the home before you write

Match the intent to a doc. When two homes fit, choose the **more specific** one
and link from the general one — never copy.

| Intent | Home |
|--------|------|
| What the project is / how to start it | `README.md` |
| A setup step, command, or PR/branch convention | `CONTRIBUTING.md` |
| Plan a multi-step or architectural change | OpenSpec change: `openspec/changes/<name>/{proposal,design,specs,tasks}.md` |
| A validated design from brainstorming | `docs/superpowers/specs/<date>-<topic>-design.md` |
| Rationale for one decision, an investigation, a post-mortem | `docs/<date>-<topic>.md` |
| A command/fact every assistant session needs | `CLAUDE.md` |
| A reusable procedure for assistants | `.claude/skills/<name>/SKILL.md` |
| Why a specific line is the way it is | Inline comment / docstring |

If the user asks for "documentation" without saying which, infer from the intent
above and say which home you chose and why before writing.

## Step 2 — match the conventions

- **Naming.** Dated docs lead with an ISO date written *the day you write it*
  (`2026-06-12-…`) — do not invent or guess a date; if you don't have today's
  date, ask or check the environment rather than fabricating one. OpenSpec
  changes use a verb-led kebab name (`add-article-authoring`). Skills are
  `nglspn-`-prefixed.
- **OpenSpec shape.** A change is four files: `proposal.md` (Why / What Changes,
  with `BREAKING` markers), `design.md` (rationale), `specs/` (capability specs),
  `tasks.md` (ordered breakdown). Follow an existing change under
  `openspec/changes/` as the template, and run `openspec validate <name>` when
  done.
- **PRs** follow `.github/PULL_REQUEST_TEMPLATE.md`: Summary / Where this fits →
  What's in this PR → Out of scope → Test plan → Verification line.

## Step 3 — write in the house voice

- **Lead with the consequence**, not the abstraction.
- **One fact, one home** — link (`[label](path)`) instead of restating.
- **Concrete** — name the file, command, function; cite `path:line` where it helps.
- **Scale to the topic** — a sentence where a sentence does; no filler headings.
- **Mark sharp edges** — `BREAKING` markers, and the repo foot-guns by name
  (OpenAPI regen, migrations, IP trust, kennitala PII).
- **No performative padding.** The value is in being right and findable.

## Step 4 — keep the rest current

A doc change rarely stands alone. Before you finish:

- Touched a **command or workflow**? Update `CONTRIBUTING.md` and `CLAUDE.md` too.
- Documented an **API change**? The contract (`backend-openapi.json`) is
  regenerated separately — see `CONTRIBUTING.md`; don't let docs imply otherwise.
- **Landed an OpenSpec change**? Move its intent out of `openspec/changes/` so a
  completed plan doesn't read as future work.
- Found a doc that's now **wrong**? Fix or delete it — a wrong doc is worse than
  none.

## Don't

- Don't create a new top-level doc when an existing one is the right home.
- Don't duplicate setup/command content into multiple files — link to
  `CONTRIBUTING.md`.
- Don't fabricate dates, test counts, or "lint clean" claims — state only what
  you can stand behind.
- Don't write English user-facing product strings, or Icelandic docs/code.
