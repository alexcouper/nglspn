# End Review Period for a Competition

## Problem

When a competition is marked completed, any `CompetitionReviewer` rows still in
`in_progress` linger in that state indefinitely. Reviewers keep seeing them as
outstanding work on the "My Reviews" page, even though the review window is
over.

We need a way for an admin to explicitly end the review period for a
competition. In-progress reviews transition to a new terminal state distinct
from `completed`, and the "My Reviews" page renders them as *not done* rather
than *done*.

## Goals

- Add a third `ReviewStatus` value, `ended`, to represent "review period closed
  before this reviewer finished".
- Provide an admin-only mechanism to sweep in-progress reviews for a
  competition into `ended`.
- Keep the ORM behind the services boundary: the admin calls a service handler
  via the `HANDLERS` registry (`services.HANDLERS.reviews`), and the Django
  implementation does the ORM work.
- Expose `ended` to the API so the front end can render it distinctly.

## Non-goals

- No automatic transition tied to `CompetitionStatus` changes. Ending the review
  period is an explicit, separate admin action.
- No public API endpoint for ending the review period. Admin-only for now.
- No migration of historical data. Only future admin-initiated ends produce
  `ended` rows; existing completed/in-progress rows are unchanged.

## Design

### Model change

`apps/projects/models.py`:

```python
class ReviewStatus(models.TextChoices):
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"
    ENDED = "ended", "Ended"
```

`CompetitionReviewer.status` is already `max_length=20`, so the migration only
updates the choices metadata.

### Service layer (new)

New package `services/review/` mirroring the `services/project/` pattern.

`services/review/handler_interface.py`:

```python
class ReviewHandlerInterface(ABC):
    @abstractmethod
    def end_review_period(self, competition_id: UUID) -> int: ...
```

Returns the number of reviews transitioned from `in_progress` to `ended`.

`services/review/django_impl/handler.py` implements it:

```python
class DjangoReviewHandler(ReviewHandlerInterface):
    def end_review_period(self, competition_id: UUID) -> int:
        return CompetitionReviewer.objects.filter(
            competition_id=competition_id,
            status=ReviewStatus.IN_PROGRESS,
        ).update(status=ReviewStatus.ENDED)
```

Rows already `completed` or `ended` are untouched. Unrelated competitions are
untouched.

### Services registry wiring

`services/__init__.py`: register the new handler on `HandlerServices` following
the existing pattern:

```python
from services.review.django_impl import DjangoReviewHandler
from services.review.handler_interface import ReviewHandlerInterface

@dataclass(frozen=True)
class HandlerServices:
    ...
    reviews: ReviewHandlerInterface = field(default_factory=DjangoReviewHandler)
```

Call sites access the handler via `HANDLERS.reviews.end_review_period(...)`;
they never instantiate `DjangoReviewHandler` directly.

### Admin action

`apps/projects/admin.py`, on `CompetitionAdmin`: add an admin action labelled
"End review period for selected".

- Iterates selected competitions.
- Calls `HANDLERS.reviews.end_review_period(comp.id)` per competition, summing
  the counts.
- Reports via `message_user`: e.g. "Ended review period for 2 competitions; 7
  reviews marked as ended."

Decoupled from winner selection and from `CompetitionStatus` — the admin
decides when to run it.

### API surface

`api/schemas/my_review.py`:

```python
class ReviewStatusEnum(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ENDED = "ended"
```

`api/routers/my_review.py`:

- List and detail endpoints already pass `my_review_status=assignment.status`
  through untouched — no logic change needed; the new enum value flows
  naturally.
- `update_review_status` endpoint (`POST /competitions/{id}/status`): add an
  explicit guard that rejects an `ended` payload. A reviewer can only toggle
  between `in_progress` and `completed`. Returns 400 on `ended`. The test suite
  verifies this.

### Front-end rendering

In the Next.js "My Reviews" page, render `ended` distinctly from `completed`:

- Visually groups with *not done* (same column / section as in-progress).
- Label: "Review period ended" (or similar — finalize during implementation
  once the exact component is located).
- Non-actionable: no link into the review flow for `ended` items, same as
  `completed`.

Exact component path and copy finalized in the implementation plan.

## Testing

- `services/review/django_impl/test_handler.py`:
  - Flips only `in_progress` rows for the target competition.
  - Leaves `completed` and already-`ended` rows alone.
  - Leaves other competitions' rows alone.
  - Returns the correct affected-row count.
- `apps/projects/tests` (admin action): selecting competitions and running the
  action transitions the expected rows; `message_user` gets the summary.
- `api/routers/test_my_review.py`:
  - List endpoint returns `my_review_status = "ended"` for swept reviews.
  - Detail endpoint returns `my_review_status = "ended"`.
  - `update_review_status` rejects `ended` payload with 400.

Tests use the existing `CompetitionFactory` and `CompetitionReviewerFactory`.
Follow the project convention of descriptive test names and helper
factories/asserts for readability.

## OpenAPI / type regeneration

Because `ReviewStatusEnum` changes, after the Django changes:

1. `cd src/django-backend && make extract-openapi`
2. `cd src/web-ui && npm run generate-types`

## Rollout

Single migration + code change. No data backfill. Existing rows retain their
current status.
