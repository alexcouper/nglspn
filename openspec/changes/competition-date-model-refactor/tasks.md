## 1. Database Model & Migration

- [x] 1.1 Rename `end_date` to `submission_deadline` on Competition model (`apps/projects/models.py`)
- [x] 1.2 Add `voting_end_date` nullable DateField to Competition model
- [x] 1.3 Generate migration: `RenameField` for `end_date` -> `submission_deadline`, `AddField` for `voting_end_date`
- [x] 1.4 Add data migration to backfill `voting_end_date = submission_deadline` for all existing rows
- [x] 1.5 Update admin (`apps/projects/admin.py`) to use `submission_deadline` and add `voting_end_date` field

## 2. Backend API Schemas

- [x] 2.1 Rename `end_date` to `submission_deadline` and add `voting_end_date` in `CompetitionResponse` (`api/schemas/competition.py`)
- [x] 2.2 Rename `end_date` to `submission_deadline` and add `voting_end_date` in `CompetitionOverviewResponse`
- [x] 2.3 Rename `end_date` to `submission_deadline` and add `voting_end_date` in `CompetitionSummaryResponse`
- [x] 2.4 Rename `end_date` to `submission_deadline` in `ReviewCompetitionResponse` and `ReviewCompetitionDetailResponse` (`api/schemas/my_review.py`)
- [x] 2.5 Rename `competition_end_date` to `competition_submission_deadline` in `WinnerItem` (`services/project/query_interface.py`) and `WinnerResponse` (`api/schemas/project.py`)

## 3. Backend API Routers & Services

- [x] 3.1 Reshape `active-or-most-recent` endpoint to return `{ competitions: CompetitionSummary[] }` — all active (accepting + voting) sorted by `start_date` desc, plus 1 most recently closed sorted by `voting_end_date` desc (`api/routers/competitions.py`)
- [x] 3.2 Update `from_competition` methods in all schemas to map the new field names
- [x] 3.3 Update `api/routers/my_review.py` to use `submission_deadline`
- [x] 3.4 Update `api/routers/projects.py` to use renamed `competition_submission_deadline`
- [x] 3.5 Update `services/project/django_impl/query.py` to use `submission_deadline` and `voting_end_date` for ordering

## 4. Backend Tests & Seeds

- [x] 4.1 Update `tests/factories.py` — rename `end_date` to `submission_deadline`, add `voting_end_date`
- [x] 4.2 Update `api/routers/test_competitions.py` — all `end_date` references, add tests for new endpoint shape and `voting_end_date` in responses
- [x] 4.3 Update seed scripts (`seed_db.py`, `seed_prod_copy.py`, `seed_discover_data.py`) to use `submission_deadline` and set `voting_end_date`
- [x] 4.4 Run backend linting and full test suite

## 5. Frontend Types & Date Utilities

- [x] 5.1 Regenerate OpenAPI spec and TypeScript types (`make extract-openapi`, `npm run generate-types`)
- [x] 5.2 Update API client types/aliases if needed (`lib/api/competitions.ts`, `lib/api/server.ts`)

## 6. Frontend Components — Date Field Updates

- [x] 6.1 Create a shared `getCompetitionDeadline(status, submission_deadline, voting_end_date)` utility that returns the relevant date based on status: `submission_deadline` when accepting applications, `voting_end_date` (falling back to `submission_deadline` if null) when voting or closed
- [x] 6.2 Update `CompetitionReveal.tsx` — use `submission_deadline` for date range display, use deadline utility for any "days remaining" or time-since display
- [x] 6.3 Update `CompetitionsList.tsx` — use `submission_deadline` for date range, use deadline utility for status-aware countdown in grid cards
- [x] 6.4 Update `my-reviews/CompetitionsList.tsx` — use `submission_deadline` for date range display
- [x] 6.5 Update competition detail page (`competitions/[id]/page.tsx`) — use `submission_deadline` for OG metadata

## 7. Homepage Competition Highlights

- [x] 7.1 Move `HorizontalScroll` from `app/projects/HorizontalScroll.tsx` to `components/HorizontalScroll.tsx` and update imports in discover page sections
- [x] 7.2 Rewrite `CompetitionHighlight.tsx` to accept `competitions: CompetitionSummary[]` and render cards inside `HorizontalScroll` with fixed-width cards
- [x] 7.3 Update homepage `page.tsx` to call reshaped endpoint and pass competitions list
- [x] 7.4 Update `CompetitionHighlight` context-aware deadline display using the shared deadline utility from 6.1

## 8. Verification

- [x] 8.1 Run backend linting and full test suite (`make lint && make test`)
- [x] 8.2 Run frontend linting (`npm run lint`)
- [x] 8.3 Browser test: verify carousel with multiple competitions, single card fallback, correct days remaining per status
