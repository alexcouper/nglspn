## Why

The introduction of a voting phase exposed ambiguity in the competition date model. `end_date` previously meant "when the competition ends" but now there are two distinct deadlines: when submissions close and when voting ends. The current single `end_date` field can't represent both, making "days remaining" calculations wrong during the voting phase and "time since closed" misleading after completion. The homepage API also needs restructuring to support multiple active competitions (accepting + voting) displayed in a carousel.

## What Changes

- **Rename `end_date` to `submission_deadline`** on the Competition model to clarify its meaning as the final date for project submissions. **BREAKING**: API field rename across all competition response schemas.
- **Add `voting_end_date` field** (nullable DateField) to Competition, representing when the voting phase ends and the competition closes.
- **Data migration** to backfill `voting_end_date = submission_deadline` for all existing competitions.
- **Reshape `active-or-most-recent` API endpoint** from returning `{ active, recent }` (one of each) to returning `{ competitions: [] }` — all active competitions (accepting_applications + voting) sorted newest-first, followed by the 1 most recently closed competition.
- **Replace homepage `CompetitionHighlight`** from a 2-card layout to a carousel that handles N competitions, ordered active-first then most recently closed.
- **Context-aware "days remaining"** across all frontend components: show days until `submission_deadline` when accepting applications, days until `voting_end_date` when voting, and time since `voting_end_date` when closed.

## Capabilities

### New Capabilities

- `competition-lifecycle-dates`: Date model for competition phases — submission deadline, voting end date, and context-aware deadline computation across API and frontend.
- `competition-highlights-carousel`: Homepage carousel component displaying multiple active competitions plus the most recently closed, replacing the current 2-card layout.

### Modified Capabilities

## Impact

- **Backend model + migration**: `apps/projects/models.py`, new migration
- **API schemas**: `api/schemas/competition.py`, `api/schemas/my_review.py`, `api/schemas/project.py` — field rename + new field
- **API routers**: `api/routers/competitions.py`, `api/routers/my_review.py`, `api/routers/projects.py` — field rename + endpoint reshape
- **Query services**: `services/project/django_impl/query.py`, `services/project/query_interface.py` — field rename
- **Admin**: `apps/projects/admin.py` — field rename + new field
- **Tests**: `api/routers/test_competitions.py`, `api/routers/test_my_projects.py`
- **Frontend types**: auto-regenerated from OpenAPI
- **Frontend components**: `CompetitionHighlight.tsx` (carousel rewrite), `CompetitionReveal.tsx`, `CompetitionsList.tsx`, `my-reviews/CompetitionsList.tsx`, competition detail page — date field updates
- **Seed scripts**: `seed_db.py`, `seed_prod_copy.py`, `seed_discover_data.py`
- **Factory**: `tests/factories.py`
