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
  (`manual` / `admin` / `backfill`) and `entered_by`. Existing M2M rows are
  backfilled. `project.competitions` and `competition.projects` keep working, so
  no read path changes.
- **Competitions belong to a series.** `Competition.entry_series` is a slug
  defaulting to `monthly`. Exclusivity is per series: a project that ran in a
  monthly round can never enter another monthly round, but is free to enter an
  occasional one-off, which carries its own slug and excludes nothing.
- **BREAKING: publishing no longer enters a competition.** The ten lines that
  entered the newest open round are deleted. `POST /api/my-projects/{id}/publish`
  publishes and nothing else. Entering is always a separate, explicit request.
- **Entry is an endpoint that names its target.**
  `POST /api/my-projects/{id}/competition-entry` takes a required
  `{ "competition_id": … }` and refuses anything that is not currently on offer
  for that project. Eligibility does not depend on when a project was published,
  so a project stranded between rounds can enter the next one. Production has no
  such project today; this closes the hole rather than clearing a backlog.
- **A project reports its whole competition history and every open door.**
  `ProjectResponse` gains `competition_standing`: the list of competitions the
  project is or was in, and one entry *opportunity* per competition with
  `status = ACCEPTING_APPLICATIONS`, each marked eligible or carrying a reason
  (`already_in_series`, `community_project`, `project_status`). No open rounds
  means an empty opportunity list, not a special state.
- **The project page grows a competitions section.** One `ProjectCompetitions`
  component renders both halves: rounds entered (with dates, status and the
  existing `won_competitions` marker) and rounds open now, each open row
  carrying an **Enter** control or the reason there isn't one.
- **Publishing asks afterwards.** A successful publish opens a dialog listing the
  rounds now on offer; the contributor enters one or dismisses it. Dismissing
  costs nothing — the same rounds stay on the project page.
- **The dead end gets an exit.** `/submit` becomes enter-or-create: the user's
  eligible projects listed above the new-project form, each with an Enter
  control, headed by the round when reached as `/submit?competition=<id>`. The
  competition CTA points there for authenticated users.
- **BREAKING (admin only)**: `CompetitionAdmin`'s `filter_horizontal` picker and
  its **Projects** fieldset are removed — Django forbids both on a M2M with a
  `through` model (system check `admin.E013`), so `manage.py check` fails
  otherwise. Replaced by a `CompetitionEntry` inline with project autocomplete.
- Removes `CreateProjectInput.competition_id`
  (`services/project/handler_interface.py:16`), which `create()` never reads.

### Explicitly out of scope

- **Re-entering the same series.** A project gets one shot per series; the
  monthly round's entrant set stays fresh rather than accumulating past
  entrants. Entering a *different* series is the point of this change.
- **Leaving a round once entered.** No withdraw endpoint. Admin only.
- **Community tipoffs entering competitions.** They stay excluded, as today —
  the submitter did not make the project.
- **Automatic round status transitions.** `ACCEPTING_APPLICATIONS` is still set
  by hand in the admin. The gaps between rounds are what made this bug possible,
  but closing them is a separate change.
- **Per-series rules beyond exclusivity.** `entry_series` is a grouping slug, not
  a model. Shared branding, per-series prizes or a series landing page are not
  part of this.

## Capabilities

### New Capabilities

- `competition-entry`: how a project enters a competition — the entry record and
  its audit fields, the series a competition belongs to, the per-competition
  eligibility rules, the standing exposed on a project, the explicit entry
  endpoint, and the UI surfaces that show and offer entry.

### Modified Capabilities

- `project-draft-publish`: the **Publishing validates preconditions and is
  authoritative** requirement changes — publishing no longer enters a
  competition under any circumstances, and the web UI prompts for entry after a
  successful publish rather than confirming it beforehand.

## Impact

**Backend** (`src/django-backend/`):

- `apps/projects/models.py` — new `CompetitionEntry` and `EntrySource`;
  `Competition.projects` gains `through=`; `Competition.entry_series` added.
- Four migrations: add `entry_series`, create the entry model, backfill from
  `competitions_projects`, swap the M2M to the through-model.
- `apps/projects/admin.py` — `CompetitionEntryInline` replaces the
  `filter_horizontal` picker; `entry_series` on the competition form.
- `services/project/` — competition entry removed from `publish()`; new
  `enter_competition()` handler method; new `competition_standing()` query;
  `CreateProjectInput.competition_id` removed.
- `api/routers/my_projects.py`, `api/schemas/project.py` — new entry endpoint,
  `competition_standing` on `ProjectResponse`.
- **Regenerate `backend-openapi.json`** (`make extract-openapi`) — the API
  surface changes, so `make extra-tests` fails without it.

**Frontend** (`src/web-ui/`):

- New `ProjectCompetitions` used by `ProjectDetail.tsx`, a compressed variant on
  `ProjectsList` cards, and a new post-publish `EnterCompetitionDialog`.
- `/submit` gains the eligible-project chooser and reads `?competition=`;
  `CompetitionReveal.tsx` CTA points at it.
- `src/lib/api/my-projects.ts` — the new entry call.

**Not affected**: voting, reviewer assignment, `RankedProject`, the public
competition page's project list, and every existing reader of
`project.competitions` / `competition.projects`.
