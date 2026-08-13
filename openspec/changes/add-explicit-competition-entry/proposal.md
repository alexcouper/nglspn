# Add explicit competition entry

## Why

Entering a competition is invisible. It happens as a side effect of publishing:
`publish()` (`services/project/django_impl/handler.py:215-224`) adds the project
to the newest round with `status = ACCEPTING_APPLICATIONS` and tells nobody. The
word "competition" appears nowhere in `/my-projects`, in the project detail page,
or in the publish flow.

Two things follow, and a user hit both:

1. **Publishing between rounds silently loses the submission.** `publish()` only
   accepts `status = DRAFT` and is one-way, so if no round is open at that
   moment the project is never entered and no in-app path can ever enter it.
   Only an admin editing the M2M can fix it.
2. **The only "enter a competition" affordance creates a new project.** The
   competition page's CTA (`CompetitionReveal.tsx:136`) is a **Submit a Project**
   button pointing at `/submit`, a page headed *Start a New Project* with an
   empty URL field. A user who already has the project in their portfolio is
   offered nothing but starting over.

Reported on Discord as: *"I should be able to submit to naglasúpan competition
from my portfolio. Add project to portfolio first, not have to do it all over
again for submitting a candidate to competition. Create then submit."*

## What Changes

- **Entry becomes a first-class record.** A `CompetitionEntry` through-model on
  `Competition.projects` carries `entered_at`, `entered_via`
  (`publish` / `manual` / `admin` / `backfill`) and `entered_by`. Existing M2M
  rows are backfilled. `project.competitions` and `competition.projects` keep
  working, so no read path changes.
- **Publishing asks instead of assuming.** `POST /api/my-projects/{id}/publish`
  accepts an optional body `{ "enter_competition": bool }`, default `true`. The
  web UI gains a publish confirmation dialog that names the round and its
  deadline, or says plainly that no round is open.
- **A published project can enter a later round.** New endpoint
  `POST /api/my-projects/{id}/competition-entry`, surfaced as an **Enter in
  \<round\>** button on `/my-projects/[id]`. Eligible from the day this ships,
  including every project published before it — the backlog is deliberately let
  in, because those are exactly the users the current behaviour stranded.
- **A project shows where it stands.** `ProjectResponse` gains a
  `competition_entry` field with a server-computed state — `entered`,
  `eligible`, `no_open_round` or `not_eligible` — rendered as a badge on the
  project detail page and on each card in `/my-projects`.
- **The dead end gets an exit.** `/submit` and the competition CTA offer
  "already have a project?" routing to the eligible project rather than only to
  a blank form.
- **One entry per project, ever.** Fairness over volume: a project that has been
  in a round cannot enter another. Enforced in the handler, not by a database
  constraint, so admins can still override.
- **BREAKING (admin only)**: `CompetitionAdmin`'s `filter_horizontal` picker and
  its **Projects** fieldset are removed — Django forbids both on a M2M with a
  `through` model (system check `admin.E013`), so `manage.py check` fails
  otherwise. Replaced by a `CompetitionEntry` inline with project autocomplete.
- Removes `CreateProjectInput.competition_id`
  (`services/project/handler_interface.py:16`), which `create()` never reads.

Not breaking for API clients: the publish body is optional and its default
reproduces today's behaviour.

### Explicitly out of scope

- **Re-entering a project into a second round.** Asked about and declined: the
  round set stays fresh rather than accumulating past entrants.
- **Leaving a round once entered.** No withdraw endpoint. Admin only.
- **Community tipoffs entering competitions.** They stay excluded, as today —
  the submitter did not make the project.
- **Automatic round status transitions.** `ACCEPTING_APPLICATIONS` is still set
  by hand in the admin. The gaps between rounds are what made this bug possible,
  but closing them is a separate change.

## Capabilities

### New Capabilities

- `competition-entry`: how a project enters a competition — the entry record and
  its audit fields, the eligibility rules, the entry state exposed on a project,
  the explicit entry endpoint, and the UI surfaces that show entry status.

### Modified Capabilities

- `project-draft-publish`: the **Publishing validates preconditions and is
  authoritative** requirement changes — competition entry on publish becomes
  caller-controlled via an optional request body rather than unconditional, and
  the resulting entry is recorded as a `CompetitionEntry` with
  `entered_via = publish`.

## Impact

**Backend** (`src/django-backend/`):

- `apps/projects/models.py` — new `CompetitionEntry` and `EntrySource`;
  `Competition.projects` gains `through=`.
- Three migrations: create the model, backfill from
  `projects_competition_projects`, swap the M2M to the through-model.
- `apps/projects/admin.py` — `CompetitionEntryInline` replaces the
  `filter_horizontal` picker.
- `services/project/` — `publish()` gains `enter_competition`; new
  `enter_competition()` handler method; new `competition_entry_state()` query;
  `CreateProjectInput.competition_id` removed.
- `api/routers/my_projects.py`, `api/schemas/project.py` — publish request body,
  new entry endpoint, `competition_entry` on `ProjectResponse`.
- **Regenerate `backend-openapi.json`** (`make extract-openapi`) — the API
  surface changes, so `make extra-tests` fails without it.

**Frontend** (`src/web-ui/`):

- New `PublishConfirmDialog`; `ProjectDetail.tsx` publish path; a
  `CompetitionEntryBadge` used by `ProjectDetail` and `ProjectsList`;
  `/submit` and `CompetitionReveal.tsx` CTA copy.
- `src/lib/api/my-projects.ts` — publish body and the new entry call.

**Not affected**: voting, reviewer assignment, `RankedProject`, the public
competition page's project list, and every existing reader of
`project.competitions` / `competition.projects`.
