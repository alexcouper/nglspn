# Clarify pending competition entries

## Why

Walking the flow end to end,
[`refine-competition-entry-surfaces`](../refine-competition-entry-surfaces/proposal.md)
puts the right controls in the right places but tells the contributor the wrong
things about where their projects stand. Three findings, all from one session.

1. **"Published." is false.** `publish()` sets `status = PENDING`
   (`services/project/django_impl/handler.py:205`); the project is submitted for
   review and goes live only when an admin approves it. The post-publish dialog
   opens with *"Published. Enter it in a competition?"*, so the one moment the
   contributor is paying closest attention is the moment they are told something
   untrue.

2. **The chooser reports a lock-out where there is a queue.** With every project
   already entered, the competition dialog says *"None of your projects can enter
   this round. Anything already in this run of competitions can't enter again."*
   Both sentences are true and the impression is wrong: those projects **are**
   in the round, holding `CompetitionEntry` rows, waiting on review. They will
   appear in the round's list the moment they are approved, because that list
   filters to `status = APPROVED` (`api/schemas/competition.py:71`). The dialog
   has the data to say so — `GET /api/my/projects` already carries every
   project's entries and status — and instead says "no".

3. **A round the project is in is listed twice, blocked by itself.** The Settings
   tab shows the round under entered rounds, then again under **Open now** with
   *"Already in this run of competitions with \<that same round\>."* The
   standing emits one opportunity per open competition regardless of whether the
   project is already in it, so a round it has entered comes back as a round it
   cannot enter.

## What Changes

- **The post-publish dialog says what happened.** *"That's it sent. Enter it in
  a competition?"*, with a line explaining the project goes live once reviewed
  and that entering now is fine — it joins the round on approval. Everything
  below the copy is unchanged.
- **The chooser shows the projects already in this round**, split into those
  awaiting review and those live in the round, above whatever can still be
  entered. The blunt "none of your projects can enter" line survives only for a
  user who genuinely has nothing in the round and nothing to enter.
- **BREAKING: a competition the project already holds an entry in is no longer
  an opportunity.** The entry is the answer for that round; reporting it a
  second time as an ineligible opportunity is the duplicate above. This narrows
  `opportunities` from "one per open competition" to "one per open competition
  the project is not already in".
- **The Settings heading becomes "Other rounds open now"**, which is what the
  list holds once entered rounds are excluded from it.
- The section's empty line learns the difference between *no round is open* and
  *no **other** round is open* — with entered rounds excluded, a project in
  every open round would otherwise be told no round is open while sitting in
  three of them.
- **Regenerate `backend-openapi.json`** — no schema field changes, but
  `make extra-tests` compares the whole file.

### Explicitly out of scope

- **The round's project count disagreeing with its list.** A competition header
  reads `competition.projects.count()` (every entry) above a list filtered to
  `status = APPROVED`, so an open round can read "1 project" over "All Projects
  (0)". Real, found in the same session, and filed rather than fixed here at the
  reviewer's direction.
- **Approving projects.** Review stays manual and unscheduled; this change only
  stops the UI misdescribing the wait.
- **Showing unapproved projects on the public competition page.** The list keeps
  filtering to `APPROVED`.
- **Entry rules.** Who may enter what is unchanged.

## Capabilities

### Modified Capabilities

- `competition-entry`: what the surfaces say about a project that is entered but
  not yet approved, and the removal of already-entered rounds from a project's
  opportunities.

## Impact

**Backend** (`src/django-backend/`):

- `services/project/django_impl/query.py` — `_standing` skips open competitions
  the project already holds an entry in.
- `services/project/django_impl/test_competition_standing.py`,
  `api/routers/test_my_projects.py` — coverage for the narrowed list.
- **Regenerate `backend-openapi.json`**.

**Frontend** (`src/web-ui/`):

- `src/app/my-projects/[id]/EnterCompetitionDialog.tsx` — copy.
- `src/app/competitions/[id]/EnterProjectDialog.tsx` — the two buckets.
- `src/components/ProjectCompetitions.tsx` — heading and empty line.

**Not affected**: the entry endpoint, the eligibility rules, the admin, the
`/create` route, and `CompetitionSummary`.
