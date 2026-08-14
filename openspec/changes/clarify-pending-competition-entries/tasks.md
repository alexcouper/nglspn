# Tasks: clarify pending competition entries

## 1. An entered round stops being an opportunity

- [x] 1.1 In `_standing` (`services/project/django_impl/query.py:458`), skip open
  competitions whose id is in the project's entries when building
  `opportunities`.
- [x] 1.2 Cover it in
  `services/project/django_impl/test_competition_standing.py`: an entered open
  round appears in `entries` and not in `opportunities`; a *different* open
  round of the same series still appears, blocked with `already_in_series`; the
  two lists never name the same competition.
- [x] 1.3 Check the existing standing tests for any that assumed one opportunity
  per open competition regardless of entries, and correct them rather than
  working around the new rule.
- [x] 1.4 Add an API-level assertion in `api/routers/test_my_projects.py`: after
  `POST /competition-entry`, the response moves that competition from
  `opportunities` into `entries`.
- [x] 1.5 Run `make extract-openapi` and commit `src/web-ui/backend-openapi.json`
  — no field changes, but `make extra-tests` diffs the whole file.

## 2. The post-publish dialog says what happened

- [x] 2.1 Reword `EnterCompetitionDialog`
  (`src/app/my-projects/[id]/EnterCompetitionDialog.tsx`): heading *"That's it
  sent. Enter it in a competition?"*, body *"It goes live once we've reviewed it.
  Entering now is fine — it joins the round on approval."* Leave the choice list,
  footer and trailing note alone.
- [x] 2.2 Update `enter-competition-dialog.test.tsx` to assert the dialog does
  not claim the project is published and does say it goes live after review.

## 3. The chooser reports where the user already stands

- [x] 3.1 In `EnterProjectDialog`
  (`src/app/competitions/[id]/EnterProjectDialog.tsx`), derive the projects
  holding an entry in *this* competition from the `competition_standing.entries`
  already fetched, and render them above the choice list with a state label per
  `design.md`: approved → "Live in the round", pending → "Awaiting review",
  otherwise the status.
- [x] 3.2 Replace the single empty message with the four cases: something to
  enter; nothing to enter but something already in; nothing at all with projects;
  no projects. Keep the create route on every case that cannot enter.
- [x] 3.3 Extend `enter-project-dialog.test.tsx`: a pending entered project is
  listed as awaiting review and the refusal line is absent; an approved one is
  listed as live; already-in plus eligible shows both sections; already-in with
  nothing eligible shows the "nothing else" line and the create link; the two
  existing empty states still read as they did.

## 4. The Settings section stops repeating a round

- [x] 4.1 Retitle the opportunities heading in `ProjectCompetitions` to **Other
  rounds open now**.
- [x] 4.2 Split the empty line: with entries, "No other round is open right
  now."; with none, the existing "No round is currently open. This project can
  enter the next one."
- [x] 4.3 Cover both empty cases in `project-competitions.test.tsx`, and assert
  an entered open round is not repeated below.

## 5. Verify

- [x] 5.1 `make lint`, `make extra-tests`, `make test` in `src/django-backend/`.
- [x] 5.2 `make lint`, `make test`, `make build-app`, `make extra-tests` in
  `src/web-ui/`.
- [x] 5.3 Manual pass, publish: publish a draft and confirm the dialog says the
  project is under review rather than published, and that entering now still
  works.
- [x] 5.4 Manual pass, chooser: with a `PENDING` project already in the round,
  confirm the dialog lists it as awaiting review and does not claim nothing can
  enter; approve it and confirm it reads as live in the round.
- [x] 5.5 Manual pass, Settings: with a project in an open round, confirm that
  round appears once, under the entered rounds, and that the heading below reads
  "Other rounds open now". With the project in every open round, confirm the
  section says no *other* round is open.
