# Refine competition entry surfaces

## Why

[`add-explicit-competition-entry`](../add-explicit-competition-entry/proposal.md)
landed the model, the eligibility rules and the entry endpoint, and they are
right. Reviewing what it built on top of them found four surfaces that are not.

1. **The post-publish dialog is hand-rolled.**
   `EnterCompetitionDialog.tsx:40` builds its own `fixed inset-0` overlay
   instead of using the repo's `Dialog` component, so it inherits none of the
   house dialog shape. The result: **Enter** is a solid button on a list row,
   **Not now** is a bare text link two blocks below it, and the two never line
   up. Every other dialog in the repo — `DeleteConfirmationDialog`,
   `SubmitRankingDialog`, the article `PublishDialog` — ends in one right-aligned
   `btn-secondary` / `btn-primary` pair.

2. **`/submit` promises submission and delivers creation.** The page does two
   unrelated jobs, and the competition CTA lands on the wrong one:
   - Its *Start a new project* half offers a **Tipoff** radio
     (`submit/page.tsx:109-122`). A tipoff can never enter a competition —
     `community_project` is the first eligibility rule. So the page reached by
     **Submit a Project** on a competition offers, prominently, the one choice
     guaranteed not to do that.
   - Creating from there enters nothing anyway. The draft is created, and entry
     is offered later, by the publish dialog. Nothing carries the competition
     through, and nothing should.

   So the competition CTA navigates away from the competition to a page whose
   larger half cannot serve the intent that sent the user there.

3. **Competition entries have no changelist.** `CompetitionEntryInline` on
   `CompetitionAdmin` can add and remove, but it is the only view of an entry
   there is. Nothing answers "which competitions is this project in?", and
   `ProjectAdmin` says nothing about competitions at all. `CompetitionReviewer`
   and `ProjectRanking` — both far less central — have full changelists with
   filters (`apps/projects/admin.py:938,952`). Entries do not.

4. **The competitions section floats outside the page.**
   `ProjectDetail.tsx:481-495` renders `ProjectCompetitions` as its own white
   card below whichever of edit or preview is showing, outside
   `ProjectPageLayout`'s banner/sidebar/tabs structure. It reads as an
   afterthought bolted under the page rather than part of it.

## What Changes

- **Both entry dialogs are built from the same two pieces.** A new `ChoiceList`
  renders icon/title/subtitle rows with single selection and knows nothing about
  competitions or projects; `Dialog` supplies the shell. The post-publish dialog
  and the new competition-page dialog each keep their own copy, wording, empty
  state and success behaviour. See [`design.md`](design.md) for what is shared
  and what deliberately is not.
- **The post-publish dialog gets the house shape.** Rounds become selectable
  rows carrying the competition's image, name and deadline; the footer holds
  **Not now** and **Enter** as an aligned pair. A single open round renders
  without a radio, already selected.
- **BREAKING: `/submit` is deleted.** It is replaced by `/create`, which holds
  only the new-project form and knows nothing about competitions. The route
  404s; no redirect. `EligibleProjectChooser` and its test go with it.
- **"Submit a project" becomes "Create a project"** on `/projects`
  (`CategoryTabs.tsx:31`, `ProjectsPage.tsx:63`) and `/my-projects`
  (`ProjectsList.tsx:212`), pointing at `/create`. The label now describes what
  the button does.
- **The competition CTA stops navigating.** For an authenticated user it opens a
  dialog listing that competition's eligible projects, entered in place. With
  nothing eligible the dialog says why and offers **Create a project**. An
  anonymous user still gets a link, to `/create`.
- **The competitions section moves into the Settings tab** of the project page's
  edit mode, losing its card chrome to sit as a section among the others. It is
  reachable only in edit mode; preview mode renders the public view, which has
  never carried standing.
- **The compressed strip on `/my-projects` cards is removed**
  (`ProjectsList.tsx:32-54`). One home for a project's standing, and it is the
  project page.
- **Admin gains a `CompetitionEntry` changelist**, filterable by competition,
  series and source, plus a read-only entries inline on `ProjectAdmin`.
  `CompetitionEntryInline` stays on `CompetitionAdmin` for quick edits.
- **BREAKING: a `DRAFT` project is no longer eligible for anything.** The base
  change had drafts evaluated like any other project, with the entry endpoint
  separately refusing them — so every surface offered an **Enter** control that
  returned `400`. Reproduced in the running app on both the competition chooser
  and the project page. A new `project_draft` reason makes the standing agree
  with the endpoint. It is distinct from `project_status` because a draft is one
  publish away from entering, where a rejected project is not. Nothing reads a
  draft's opportunities any more: the post-publish dialog reads the *publish
  response*, by which point the project is `PENDING`.
- `CompetitionSummary` gains `image_url` so a round can be rendered with its
  image. **Regenerate `backend-openapi.json`** — `make extra-tests` fails
  without it.
- `NotificationProjectIcon` is renamed `EntityIcon`. It already takes only
  `imageUrl`/`title`/`size` and has nothing to do with notifications; the name
  is the only thing stopping it being reused.

### Explicitly out of scope

- **The model and the entry endpoint.** `CompetitionEntry`, `entry_series`,
  `competition_standing`'s shape and
  `POST /api/my-projects/{id}/competition-entry` are unchanged. The eligibility
  rules gain one entry — drafts — because the surfaces this change reshapes
  cannot be made correct without it; everything else about them stands.
- **Carrying a competition through project creation.** `/create` takes no
  `?competition=`. A user who creates a project from the competition dialog is
  offered that round by the publish dialog, if it is still open — which is the
  behaviour they would get anyway.
- **Entering from `/my-projects` cards.** Still the project page's job; the
  round has to be picked per project.
- **A shared `DialogActions` component.** Seven dialogs already write the footer
  inline. Extracting it is a repo-wide refactor, not part of this.
- **Icelandic copy.** Every string here is English, as the surrounding UI is.

## Capabilities

### Modified Capabilities

- `competition-entry`: where entry is offered and how it is presented. The
  project page section moves into the Settings tab and off the project cards;
  both entry dialogs take a select-then-confirm shape; the competition page
  offers entry in a dialog instead of routing to `/submit`; project creation
  gets its own route; competition summaries carry an image; admin gains a way to
  view and manage entries.

## Impact

**Backend** (`src/django-backend/`):

- `api/schemas/project.py` — `CompetitionSummary.image_url`.
- `apps/projects/admin.py` — `CompetitionEntryAdmin`; a read-only
  `CompetitionEntry` inline on `ProjectAdmin`.
- **Regenerate `backend-openapi.json`** (`make extract-openapi`).

**Frontend** (`src/web-ui/`):

- New `src/app/create/page.tsx`; `src/app/submit/` deleted.
- New `src/components/ChoiceList.tsx`; `NotificationProjectIcon` renamed
  `EntityIcon` (call site: `NotificationGroupItem.tsx:42`).
- `EnterCompetitionDialog` reworked; new `EnterProjectDialog` under
  `src/app/competitions/[id]/`.
- `CompetitionReveal.tsx` — CTA opens the dialog.
- `ProjectDetail.tsx` / `EditProjectContent.tsx` — the section moves into the
  Settings tab; `ProjectCompetitions` loses its card chrome.
- `ProjectsList.tsx` — `CompetitionSummaryLine` removed.
- `CategoryTabs.tsx`, `ProjectsPage.tsx` — CTA copy and target.

**Not affected**: the entry endpoint, eligibility, `competition_standing`'s
shape beyond the added image, the migrations, and every backend test the base
change added. `GET /api/my-projects` keeps `with_competition_standing` — the
cards no longer read it, but the competition dialog does.
