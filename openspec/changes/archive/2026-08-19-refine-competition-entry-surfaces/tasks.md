# Tasks: refine competition entry surfaces

## 1. Competition summaries carry an image

- [x] 1.1 Add `image_url: str | None = None` to `CompetitionSummary`
  (`api/schemas/project.py:64`), resolved from the existing
  `Competition.image_url` property (`apps/projects/models.py:444`).
- [x] 1.2 Extend the standing tests in `api/routers/test_my_projects.py`: a
  competition with an image reports its URL in both `entries` and
  `opportunities`; one without reports null.
- [x] 1.3 Confirm the query-count test added by the base change
  (`add-explicit-competition-entry/tasks.md:49`) still passes — `image_url`
  reads a field already loaded, and must not introduce a per-row fetch.
- [x] 1.4 Run `make extract-openapi` in `src/django-backend/` and commit
  `src/web-ui/backend-openapi.json`; `make extra-tests` fails without it.

## 1b. A draft is ineligible

Found during the manual pass in section 8 — both entry surfaces offered a draft
an **Enter** control that returned `400`. See `design.md`.

- [x] 1b.1 Add `PROJECT_DRAFT = "project_draft"` to `IneligibleReason`
  (`services/project/query_interface.py`) and a `DRAFT` rule to `_opportunity`
  (`services/project/django_impl/query.py`), after the `REJECTED`/`ICE_BOX` rule
  and before the series check.
- [x] 1b.2 Add `"project_draft"` to `CompetitionOpportunityResponse.reason`
  (`api/schemas/project.py`) and regenerate the OpenAPI spec and TS types.
- [x] 1b.3 Replace the base change's
  `test_draft_is_evaluated_like_any_other_project` with one asserting
  `project_draft`, and add a tipoff-draft case pinning the rule order.
- [x] 1b.4 Map `project_draft` in `ProjectCompetitions`'s
  `PROJECT_WIDE_REASONS` so a draft states it once and shows no controls, and
  cover it in `project-competitions.test.tsx`.
- [x] 1b.5 Confirm `enter_competition` still checks `DRAFT` before the
  opportunity lookup, so the specific message survives.

## 2. Admin

- [x] 2.1 Register `CompetitionEntryAdmin` in `apps/projects/admin.py`, modelled
  on `CompetitionReviewerAdmin` (`admin.py:938`): `list_display` of competition,
  project, `entered_at`, `entered_via`, `entered_by`; `list_filter` on
  `competition`, `competition__entry_series`, `entered_via`; `search_fields`
  over `project__title` and `competition__name`; `autocomplete_fields` for
  competition and project; `ordering = ("-entered_at",)`; `select_related` in
  `get_queryset`.
- [x] 2.2 Make `entered_via` and `entered_by` readonly on it and stamp
  `EntrySource.ADMIN` / `request.user` in `save_model` when adding, matching
  what `CompetitionAdmin.save_formset` does for the inline (`admin.py:727-751`).
- [x] 2.3 Add a read-only `CompetitionEntry` inline to `ProjectAdmin`
  (`admin.py:182`): `extra = 0`, `can_delete = False`,
  `has_add_permission` returning `False`, every field readonly.
- [x] 2.4 Leave `CompetitionEntryInline` on `CompetitionAdmin` as it is.
- [x] 2.5 Run `uv run python manage.py check` — the new admin's
  `autocomplete_fields` need `search_fields` on both target admins.
- [x] 2.6 Cover the admin behaviour in `tests/`: adding an entry from the
  changelist stamps `entered_via = admin` and `entered_by`; filtering by
  competition narrows the list; searching by project title finds its entries;
  the `ProjectAdmin` change form renders a project's entries and offers no add
  or delete. `tests/test_admin_search.py` picks up the new search fields
  automatically.

## 3. Shared frontend pieces

- [x] 3.1 Rename `NotificationProjectIcon` to `EntityIcon`
  (`src/components/NotificationProjectIcon.tsx` → `EntityIcon.tsx`), unchanged
  otherwise, and update its one call site (`NotificationGroupItem.tsx:42`).
- [x] 3.2 Add `src/components/ChoiceList.tsx`: `{ name, choices, selectedId,
  onSelect }` over `Choice = { id, title, subtitle?, imageUrl? }`, rendering
  radio rows with `EntityIcon`. A single choice renders as a plain row with no
  radio. It SHALL know nothing about competitions or projects.
- [x] 3.3 Vitest cover `ChoiceList`: several choices render radios and selection
  calls `onSelect`; one choice renders no radio; a choice with no `imageUrl`
  falls back to the initial.

## 4. The post-publish dialog

- [x] 4.1 Rewrite `EnterCompetitionDialog`
  (`src/app/my-projects/[id]/EnterCompetitionDialog.tsx`) on `Dialog` and
  `ChoiceList`: rounds mapped to choices (name, deadline as subtitle,
  `competition.image_url`), first pre-selected, footer holding **Not now**
  (`btn-secondary`) and **Enter** (`btn-primary`) as one right-aligned pair.
- [x] 4.2 Keep the existing helper line and the "renders nothing with no
  eligible opportunities" behaviour.
- [x] 4.3 Update `enter-competition-dialog.test.tsx`: one round enters without a
  selection step; two rounds enter the *selected* one, not the first; dismissing
  calls neither; the footer controls are siblings.

## 5. The competition page chooser

- [x] 5.1 Add `EnterProjectDialog` under `src/app/competitions/[id]/`, on
  `Dialog` and `ChoiceList`. It fetches `api.myProjects.list()` when opened,
  filters to projects holding an eligible opportunity for this competition,
  maps them to choices (title, tagline, the project's icon image or its main
  image thumbnail via `pickVariant`), first pre-selected, and confirms through
  `api.myProjects.enterCompetition`.
- [x] 5.2 Give it the two empty states: no projects at all, and projects but
  none eligible. Both offer **Create a project** linking to `/create` and say
  publishing will offer this round. Handle loading and fetch failure.
- [x] 5.3 Change `CompetitionReveal.tsx:136-150` so the authenticated CTA opens
  the dialog instead of linking, and reword the banner copy for it. Leave the
  anonymous CTA a link, pointed at `/create`. Call `router.refresh()` after a
  successful entry so the round's project count updates.
- [x] 5.4 Vitest cover: the CTA opens the dialog and does not navigate; only
  projects eligible for *this* competition are listed; confirming calls the
  endpoint with the selected project and this competition; both empty states
  render their own message and the create link; dismissing enters nothing.

## 6. `/create` replaces `/submit`

- [x] 6.1 Add `src/app/create/page.tsx` — `src/app/submit/page.tsx` with
  `EligibleProjectChooser` removed, headed "Create a project".
- [x] 6.2 Delete `src/app/submit/` entirely: `page.tsx`,
  `EligibleProjectChooser.tsx`, `eligible-project-chooser.test.tsx`. No
  redirect.
- [x] 6.3 Repoint and reword the creation CTAs to **Create a project** →
  `/create`: `app/projects/CategoryTabs.tsx:31`,
  `app/projects/ProjectsPage.tsx:63`, `app/my-projects/ProjectsList.tsx:212`
  (keeping its first-project wording).
- [x] 6.4 `grep -rn "/submit" src/` and confirm nothing in the app still points
  there.

## 7. Competitions moves into Settings

- [x] 7.1 Strip `ProjectCompetitions`'s own card chrome and `<h2>`
  (`src/components/ProjectCompetitions.tsx:69-70`) so it renders as a section
  inside a tab panel rather than a card inside a card.
- [x] 7.2 Remove the floating block from `ProjectDetail.tsx:481-495` and pass
  the standing, the enter handler and the entry error into `EditProjectContent`
  instead.
- [x] 7.3 Render `ProjectCompetitions` in `EditProjectContent`'s **Settings**
  tab (`EditProjectContent.tsx:212-231`), under status and submission date.
  Tipoffs still render nothing.
- [x] 7.4 Remove `CompetitionSummaryLine` from `ProjectsList.tsx:30-54` and its
  use on the card, along with any test asserting it.
- [x] 7.5 Update `project-competitions.test.tsx` for the chrome change, and add
  coverage that the section appears under Settings in edit mode and nowhere in
  preview mode.

## 8. Verify

- [x] 8.1 `make lint`, `make extra-tests`, `make test` in `src/django-backend/`.
- [x] 8.2 `make lint`, `make test`, `make build-app`, `make extra-tests` in
  `src/web-ui/`.
- [x] 8.3 Manual pass, publish flow: with one round open, publish a draft and
  confirm the dialog shows the round with its image, no radio, and an aligned
  **Not now** / **Enter** pair; enter it. With two rounds open, confirm the
  second is selectable and entering enters the one selected.
- [x] 8.4 Manual pass, competition page: as a user with an eligible project,
  press **Submit a Project** and confirm a dialog opens without navigating,
  lists only eligible projects, and enters the selected one; confirm the round's
  project count updates. Repeat as a user with no eligible project and as one
  with no projects, confirming each message and that **Create a project** lands
  on `/create`. Confirm the anonymous CTA still links.
- [x] 8.5 Manual pass, project page: confirm competitions appear under
  **Settings** in edit mode, not below the content, not in preview, and not on
  `/my-projects` cards; enter a round from there.
- [x] 8.6 Manual pass, admin: add an entry from the changelist and confirm it
  records `admin` and the acting user; filter by competition; search by project
  title; open a project and confirm its competitions are listed read only.
- [x] 8.7 Confirm `/submit` 404s.
