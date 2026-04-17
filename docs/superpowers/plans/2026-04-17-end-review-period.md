# End Review Period Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an admin-triggered action that transitions all `in_progress` `CompetitionReviewer` rows for a competition into a new `ended` state, rendered as *not done* on the My Reviews page.

**Architecture:** New `services/review/` module follows the existing `handler_interface` + `django_impl` pattern used by `services/project/` and `services/notifications/`. The handler is registered on `HandlerServices` so callers use `HANDLERS.reviews.end_review_period(...)` without instantiating. A Django admin action on `CompetitionAdmin` dispatches to the handler. The API schema surfaces the new status; the Next.js My Reviews list treats `ended` as not-done with a distinct label.

**Tech Stack:** Django 5 + django-ninja + pytest + factory_boy (backend); Next.js + TypeScript + Tailwind (frontend); jj for VCS.

---

## File Structure

**Backend — create:**
- `src/django-backend/services/review/__init__.py`
- `src/django-backend/services/review/handler_interface.py` — `ReviewHandlerInterface` abstract base
- `src/django-backend/services/review/django_impl/__init__.py` — re-exports `DjangoReviewHandler`
- `src/django-backend/services/review/django_impl/handler.py` — ORM implementation
- `src/django-backend/services/review/django_impl/test_handler.py` — unit tests
- `src/django-backend/apps/projects/migrations/0035_add_ended_review_status.py` — choices-only migration

**Backend — modify:**
- `src/django-backend/apps/projects/models.py` — add `ENDED` to `ReviewStatus`
- `src/django-backend/services/__init__.py` — register `reviews` on `HandlerServices`
- `src/django-backend/apps/projects/admin.py` — add admin action on `CompetitionAdmin`
- `src/django-backend/api/schemas/my_review.py` — add `ENDED` to `ReviewStatusEnum`
- `src/django-backend/api/routers/my_review.py` — guard `update_review_status` against `ended`
- `src/django-backend/api/routers/test_my_review.py` — add coverage

**Frontend — modify:**
- `src/web-ui/src/lib/api-types.ts` — regenerated
- `src/web-ui/src/app/my-reviews/CompetitionsList.tsx` — render `ended` alongside in-progress with distinct label
- `src/web-ui/src/app/my-reviews/[competitionId]/CompetitionProjects.tsx` — treat `ended` as read-only if it exposes review status

---

## Task 1: Add `ENDED` value to `ReviewStatus`

**Files:**
- Modify: `src/django-backend/apps/projects/models.py:326-328`

- [ ] **Step 1: Extend the enum**

Replace the existing `ReviewStatus` class with:

```python
class ReviewStatus(models.TextChoices):
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"
    ENDED = "ended", "Ended"
```

- [ ] **Step 2: Create the migration**

Run from `src/django-backend/`:

```bash
uv run python manage.py makemigrations projects --name add_ended_review_status
```

Expected: creates `apps/projects/migrations/0035_add_ended_review_status.py` with an `AlterField` on `CompetitionReviewer.status` that updates the choices (no data migration — `max_length=20` already fits `"ended"`).

- [ ] **Step 3: Run migrations locally to confirm they apply**

```bash
uv run python manage.py migrate projects
```

Expected: `Applying projects.0035_add_ended_review_status... OK`.

- [ ] **Step 4: Commit**

```bash
jj commit -m "Add ENDED value to ReviewStatus"
```

---

## Task 2: Scaffold the `services/review` package

**Files:**
- Create: `src/django-backend/services/review/__init__.py` (empty)
- Create: `src/django-backend/services/review/handler_interface.py`
- Create: `src/django-backend/services/review/django_impl/__init__.py`

- [ ] **Step 1: Start a new changeset**

```bash
jj new -m "Scaffold services/review handler interface"
```

- [ ] **Step 2: Create the package `__init__` files**

Both `src/django-backend/services/review/__init__.py` and `src/django-backend/services/review/django_impl/__init__.py` get created. The top-level one is empty; the `django_impl` one will re-export the concrete handler once Task 3 creates it. Create both now:

`src/django-backend/services/review/__init__.py`:

```python
```

(empty file)

`src/django-backend/services/review/django_impl/__init__.py`:

```python
from .handler import DjangoReviewHandler

__all__ = [
    "DjangoReviewHandler",
]
```

Note: this import will fail until Task 3. That's expected — we commit the interface first.

- [ ] **Step 3: Write the interface**

`src/django-backend/services/review/handler_interface.py`:

```python
from abc import ABC, abstractmethod
from uuid import UUID


class ReviewHandlerInterface(ABC):
    @abstractmethod
    def end_review_period(self, competition_id: UUID) -> int:
        """Transition all IN_PROGRESS reviews for the competition to ENDED.

        Returns the number of reviewer rows transitioned.
        """
```

- [ ] **Step 4: Confirm the interface imports cleanly**

Run from `src/django-backend/`:

```bash
uv run python -c "from services.review.handler_interface import ReviewHandlerInterface; print(ReviewHandlerInterface)"
```

Expected: prints `<class 'services.review.handler_interface.ReviewHandlerInterface'>` without error.

- [ ] **Step 5: Skip committing yet**

Don't commit — the `django_impl/__init__.py` import is still broken. Task 3 completes it.

---

## Task 3: Implement `DjangoReviewHandler` (TDD)

**Files:**
- Test: `src/django-backend/services/review/django_impl/test_handler.py`
- Create: `src/django-backend/services/review/django_impl/handler.py`

- [ ] **Step 1: Write the failing test file**

`src/django-backend/services/review/django_impl/test_handler.py`:

```python
import pytest
from hamcrest import assert_that, equal_to

from apps.projects.models import CompetitionReviewer, ReviewStatus
from services.review.django_impl.handler import DjangoReviewHandler
from tests.factories import CompetitionFactory, CompetitionReviewerFactory


@pytest.fixture
def handler():
    return DjangoReviewHandler()


def _status_of(reviewer: CompetitionReviewer) -> str:
    reviewer.refresh_from_db()
    return reviewer.status


@pytest.mark.django_db
class TestEndReviewPeriod:
    def test_transitions_in_progress_reviews_to_ended(self, handler) -> None:
        competition = CompetitionFactory()
        in_progress = CompetitionReviewerFactory(
            competition=competition, status=ReviewStatus.IN_PROGRESS
        )

        count = handler.end_review_period(competition.id)

        assert_that(count, equal_to(1))
        assert_that(_status_of(in_progress), equal_to(ReviewStatus.ENDED))

    def test_leaves_completed_reviews_untouched(self, handler) -> None:
        competition = CompetitionFactory()
        completed = CompetitionReviewerFactory(
            competition=competition, status=ReviewStatus.COMPLETED
        )

        count = handler.end_review_period(competition.id)

        assert_that(count, equal_to(0))
        assert_that(_status_of(completed), equal_to(ReviewStatus.COMPLETED))

    def test_leaves_already_ended_reviews_untouched(self, handler) -> None:
        competition = CompetitionFactory()
        already_ended = CompetitionReviewerFactory(
            competition=competition, status=ReviewStatus.ENDED
        )

        count = handler.end_review_period(competition.id)

        assert_that(count, equal_to(0))
        assert_that(_status_of(already_ended), equal_to(ReviewStatus.ENDED))

    def test_does_not_affect_other_competitions(self, handler) -> None:
        target = CompetitionFactory()
        other = CompetitionFactory()
        CompetitionReviewerFactory(
            competition=target, status=ReviewStatus.IN_PROGRESS
        )
        other_reviewer = CompetitionReviewerFactory(
            competition=other, status=ReviewStatus.IN_PROGRESS
        )

        handler.end_review_period(target.id)

        assert_that(_status_of(other_reviewer), equal_to(ReviewStatus.IN_PROGRESS))

    def test_counts_all_in_progress_rows_for_competition(self, handler) -> None:
        competition = CompetitionFactory()
        CompetitionReviewerFactory(competition=competition, status=ReviewStatus.IN_PROGRESS)
        CompetitionReviewerFactory(competition=competition, status=ReviewStatus.IN_PROGRESS)
        CompetitionReviewerFactory(competition=competition, status=ReviewStatus.COMPLETED)

        count = handler.end_review_period(competition.id)

        assert_that(count, equal_to(2))
```

- [ ] **Step 2: Run the tests to confirm they fail**

From `src/django-backend/`:

```bash
uv run pytest services/review/django_impl/test_handler.py -v
```

Expected: collection error — `ModuleNotFoundError: No module named 'services.review.django_impl.handler'`.

- [ ] **Step 3: Write the minimal implementation**

`src/django-backend/services/review/django_impl/handler.py`:

```python
from uuid import UUID

from apps.projects.models import CompetitionReviewer, ReviewStatus
from services.review.handler_interface import ReviewHandlerInterface


class DjangoReviewHandler(ReviewHandlerInterface):
    def end_review_period(self, competition_id: UUID) -> int:
        return CompetitionReviewer.objects.filter(
            competition_id=competition_id,
            status=ReviewStatus.IN_PROGRESS,
        ).update(status=ReviewStatus.ENDED)
```

- [ ] **Step 4: Run the tests to confirm they pass**

From `src/django-backend/`:

```bash
uv run pytest services/review/django_impl/test_handler.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Lint**

```bash
make lint
```

Expected: no errors. If `ruff format` reports diffs, run `uv run ruff format services/review` and re-run.

- [ ] **Step 6: Commit**

```bash
jj commit -m "Implement DjangoReviewHandler.end_review_period"
```

---

## Task 4: Register `reviews` on `HandlerServices`

**Files:**
- Modify: `src/django-backend/services/__init__.py`

- [ ] **Step 1: Start a new changeset**

```bash
jj new -m "Register reviews handler on HandlerServices"
```

- [ ] **Step 2: Add the import and field**

In `src/django-backend/services/__init__.py`, after the existing `from services.registration...` imports, add:

```python
from services.review.django_impl import DjangoReviewHandler
from services.review.handler_interface import ReviewHandlerInterface
```

Then inside the `HandlerServices` dataclass, add a `reviews` field (keep fields alphabetical to match existing ordering — place between `registration` and `users`):

```python
    reviews: ReviewHandlerInterface = field(default_factory=DjangoReviewHandler)
```

Final `HandlerServices` block should look like:

```python
@dataclass(frozen=True)
class HandlerServices:
    discussions: DiscussionHandlerInterface = field(
        default_factory=DjangoDiscussionHandler
    )
    email: EmailHandlerInterface = field(default_factory=DjangoEmailHandler)
    image: ImageHandlerInterface = field(default_factory=DjangoImageHandler)
    notifications: NotificationHandlerInterface = field(
        default_factory=DjangoNotificationHandler
    )
    project: ProjectHandlerInterface = field(default_factory=DjangoProjectHandler)
    registration: RegistrationHandlerInterface = field(
        default_factory=DjangoRegistrationHandler
    )
    reviews: ReviewHandlerInterface = field(default_factory=DjangoReviewHandler)
    users: UserHandlerInterface = field(default_factory=DjangoUserHandler)
```

- [ ] **Step 3: Sanity-check the registry**

From `src/django-backend/`:

```bash
uv run python -c "from services import HANDLERS; print(type(HANDLERS.reviews).__name__)"
```

Expected: `DjangoReviewHandler`.

- [ ] **Step 4: Lint**

```bash
make lint
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
jj commit -m "Register reviews handler on HandlerServices"
```

---

## Task 5: Admin action on `CompetitionAdmin`

**Files:**
- Modify: `src/django-backend/apps/projects/admin.py` (`CompetitionAdmin` class, around lines 464-523)
- Test: `src/django-backend/apps/projects/test_admin_end_review_period.py` (new)

- [ ] **Step 1: Start a new changeset**

```bash
jj new -m "Add end review period admin action"
```

- [ ] **Step 2: Write the failing test**

Create `src/django-backend/apps/projects/test_admin_end_review_period.py`:

```python
import pytest
from django.contrib.admin.sites import AdminSite
from django.http import HttpRequest
from hamcrest import assert_that, contains_string, equal_to

from apps.projects.admin import CompetitionAdmin
from apps.projects.models import Competition, CompetitionReviewer, ReviewStatus
from tests.factories import CompetitionFactory, CompetitionReviewerFactory, UserFactory


class _RequestWithMessages(HttpRequest):
    """HttpRequest stub that captures admin messages for assertions."""

    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []


def _make_request() -> _RequestWithMessages:
    request = _RequestWithMessages()
    request.user = UserFactory.build(is_superuser=True, is_staff=True)
    return request


@pytest.fixture
def admin_instance():
    return CompetitionAdmin(Competition, AdminSite())


@pytest.mark.django_db
class TestEndReviewPeriodAction:
    def test_transitions_in_progress_reviews_for_selected_competitions(
        self, admin_instance, monkeypatch
    ) -> None:
        comp_a = CompetitionFactory()
        comp_b = CompetitionFactory()
        in_progress_a = CompetitionReviewerFactory(
            competition=comp_a, status=ReviewStatus.IN_PROGRESS
        )
        in_progress_b = CompetitionReviewerFactory(
            competition=comp_b, status=ReviewStatus.IN_PROGRESS
        )
        completed = CompetitionReviewerFactory(
            competition=comp_a, status=ReviewStatus.COMPLETED
        )

        request = _make_request()
        captured: list[str] = []
        monkeypatch.setattr(
            admin_instance, "message_user", lambda req, msg, *a, **kw: captured.append(msg)
        )

        queryset = Competition.objects.filter(id__in=[comp_a.id, comp_b.id])
        admin_instance.end_review_period(request, queryset)

        in_progress_a.refresh_from_db()
        in_progress_b.refresh_from_db()
        completed.refresh_from_db()

        assert_that(in_progress_a.status, equal_to(ReviewStatus.ENDED))
        assert_that(in_progress_b.status, equal_to(ReviewStatus.ENDED))
        assert_that(completed.status, equal_to(ReviewStatus.COMPLETED))
        assert_that(len(captured), equal_to(1))
        assert_that(captured[0], contains_string("2"))

    def test_leaves_unselected_competition_rows_alone(
        self, admin_instance, monkeypatch
    ) -> None:
        selected = CompetitionFactory()
        unselected = CompetitionFactory()
        CompetitionReviewerFactory(
            competition=selected, status=ReviewStatus.IN_PROGRESS
        )
        untouched = CompetitionReviewerFactory(
            competition=unselected, status=ReviewStatus.IN_PROGRESS
        )

        request = _make_request()
        monkeypatch.setattr(admin_instance, "message_user", lambda *a, **kw: None)

        queryset = Competition.objects.filter(id=selected.id)
        admin_instance.end_review_period(request, queryset)

        untouched.refresh_from_db()
        assert_that(untouched.status, equal_to(ReviewStatus.IN_PROGRESS))
```

- [ ] **Step 3: Run the test to confirm it fails**

From `src/django-backend/`:

```bash
uv run pytest apps/projects/test_admin_end_review_period.py -v
```

Expected: `AttributeError: 'CompetitionAdmin' object has no attribute 'end_review_period'`.

- [ ] **Step 4: Add the admin action**

Open `src/django-backend/apps/projects/admin.py`. Find the `CompetitionAdmin` class (line 464). Add `actions` and the action method. Insert `actions = ("end_review_period",)` near the other class-level attributes (after `ordering = ("-start_date",)`), and add the action method at the end of the class (after existing `@admin.display` methods). Also add imports at the top if they aren't there yet.

Imports at the top of `admin.py` should include (add `HANDLERS` if missing):

```python
from services import HANDLERS
```

Add the class-level `actions` tuple (after `ordering`):

```python
    actions = ("end_review_period",)
```

Add the method to `CompetitionAdmin`:

```python
    @admin.action(description="End review period for selected competitions")
    def end_review_period(self, request, queryset) -> None:
        total_ended = 0
        competition_count = queryset.count()
        for competition in queryset:
            total_ended += HANDLERS.reviews.end_review_period(competition.id)
        self.message_user(
            request,
            f"Ended review period for {competition_count} competition(s); "
            f"{total_ended} review(s) marked as ended.",
        )
```

- [ ] **Step 5: Run the tests to confirm they pass**

```bash
uv run pytest apps/projects/test_admin_end_review_period.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Lint**

```bash
make lint
```

Expected: no errors.

- [ ] **Step 7: Commit**

```bash
jj commit -m "Add end review period admin action on CompetitionAdmin"
```

---

## Task 6: Surface `ENDED` in the API schema and guard `update_review_status`

**Files:**
- Modify: `src/django-backend/api/schemas/my_review.py:13-16`
- Modify: `src/django-backend/api/routers/my_review.py` (around `update_review_status`, lines 173-193)
- Modify: `src/django-backend/api/routers/test_my_review.py`

- [ ] **Step 1: Start a new changeset**

```bash
jj new -m "Expose ended review status via API"
```

- [ ] **Step 2: Add failing test for list endpoint returning `ended`**

In `src/django-backend/api/routers/test_my_review.py`, inside `TestListMyReviewCompetitions` (around line 25), add:

```python
    def test_returns_ended_status_for_swept_reviews(self, client, authed_user) -> None:
        competition = CompetitionFactory()
        CompetitionReviewerFactory(
            user=authed_user,
            competition=competition,
            status=ReviewStatus.ENDED,
        )

        response = client.get("/api/my-review/competitions")

        assert_that(response.status_code, equal_to(200))
        payload = response.json()
        assert_that(payload["competitions"][0]["my_review_status"], equal_to("ended"))
```

Note: if `CompetitionReviewerFactory` or `ReviewStatus` aren't already imported in this file, add them to the existing imports at the top. Use the same import style as neighboring tests.

- [ ] **Step 3: Add failing test for `update_review_status` rejecting `ended`**

In the same file, inside `TestUpdateReviewStatus` (around line 395), add:

```python
    def test_rejects_ended_payload(self, client, authed_user) -> None:
        competition = CompetitionFactory()
        reviewer = CompetitionReviewerFactory(
            user=authed_user,
            competition=competition,
            status=ReviewStatus.IN_PROGRESS,
        )

        response = client.put(
            f"/api/my-review/competitions/{competition.id}/status",
            data={"status": "ended"},
            content_type="application/json",
        )

        assert_that(response.status_code, equal_to(400))
        reviewer.refresh_from_db()
        assert_that(reviewer.status, equal_to(ReviewStatus.IN_PROGRESS))
```

- [ ] **Step 4: Run tests to confirm they fail**

From `src/django-backend/`:

```bash
uv run pytest api/routers/test_my_review.py -v -k "ended"
```

Expected: both new tests fail — the first because `ReviewStatusEnum` rejects `"ended"` at response validation time (or passes through but factory may reject the enum value if unused — confirm message); the second because the endpoint currently accepts `ended` and returns 200.

- [ ] **Step 5: Add `ENDED` to the response enum**

`src/django-backend/api/schemas/my_review.py`, replace lines 13-16:

```python
class ReviewStatusEnum(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ENDED = "ended"
```

- [ ] **Step 6: Guard `update_review_status` against `ended`**

`src/django-backend/api/routers/my_review.py`, in `update_review_status` (lines 179-193), prepend a guard. Updated function body:

```python
def update_review_status(
    request: HttpRequest,
    competition_id: str,
    payload: StatusUpdateRequest,
) -> SuccessResponse | tuple[int, Error]:
    """Update the reviewer's status for a competition."""
    if payload.status == ReviewStatusEnum.ENDED:
        return 400, Error(
            detail="Reviewers cannot set status to 'ended'; that is set by an admin."
        )

    updated = CompetitionReviewer.objects.filter(
        user=request.auth,
        competition_id=competition_id,
    ).update(status=payload.status.value)

    if not updated:
        return 404, Error(detail="Competition not found")

    return SuccessResponse()
```

Make sure `ReviewStatusEnum` is imported at the top of the router module (check around line 24; import from `api.schemas.my_review` if not already present). The router also needs `400` added to its response types:

```python
@router.put(
    "/competitions/{competition_id}/status",
    response={200: SuccessResponse, 400: Error, 404: Error},
    auth=auth,
    tags=["My Review"],
)
```

- [ ] **Step 7: Run tests to confirm they pass**

```bash
uv run pytest api/routers/test_my_review.py -v
```

Expected: all tests in `TestListMyReviewCompetitions` and `TestUpdateReviewStatus` pass, including the two new ones.

- [ ] **Step 8: Regenerate OpenAPI + TypeScript types**

```bash
cd src/django-backend && make extract-openapi
cd ../web-ui && npm run generate-types
```

Expected: the generated `src/web-ui/src/lib/api-types.ts` now includes `"ended"` in the `my_review_status` union for the relevant response schemas.

- [ ] **Step 9: Lint**

```bash
cd src/django-backend && make lint
```

Expected: no errors.

- [ ] **Step 10: Commit**

```bash
jj commit -m "Expose ended review status via API and reject user-initiated transitions"
```

---

## Task 7: Render `ended` on the My Reviews list

**Files:**
- Modify: `src/web-ui/src/app/my-reviews/CompetitionsList.tsx`

- [ ] **Step 1: Start a new changeset**

```bash
jj new -m "Render ended review period as not-done on My Reviews"
```

- [ ] **Step 2: Update the list grouping and rendering**

In `src/web-ui/src/app/my-reviews/CompetitionsList.tsx`:

Replace lines 35-40 (the `inProgress` / `completed` partitioning):

```tsx
  const outstanding = competitions.filter(
    (c) => c.my_review_status === "in_progress" || c.my_review_status === "ended"
  );
  const completed = competitions.filter(
    (c) => c.my_review_status === "completed"
  );
```

Rename the first block's variable from `inProgress` to `outstanding` in the JSX (line 44 and line 46).

Inside the outstanding map (around lines 47-81), branch on `my_review_status`. Replace the existing `<Link>` with:

```tsx
            const isEnded = competition.my_review_status === "ended";
            const cardClasses = isEnded
              ? "group flex items-start gap-4 w-full text-left bg-muted rounded-xl border border-border p-5"
              : "group flex items-start gap-4 w-full text-left bg-white rounded-xl border border-border p-5 hover:border-slate-300 hover:shadow-sm transition-all";
            const Card = isEnded ? "div" : Link;
            const cardProps = isEnded
              ? { className: cardClasses }
              : { href: `/my-reviews/${competition.id}`, className: cardClasses };

            return (
              <Card key={competition.id} {...cardProps}>
                <div
                  className={`relative w-11 h-11 rounded-full overflow-hidden flex-shrink-0 ${!competition.image_url ? placeholderColor : ""}`}
                >
                  {competition.image_url && (
                    <Image
                      src={competition.image_url}
                      alt={competition.name}
                      fill
                      className="object-cover"
                      sizes="44px"
                    />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <h2 className={`font-medium ${isEnded ? "text-muted-foreground" : "text-foreground group-hover:text-accent"} transition-colors`}>
                    {competition.name}
                  </h2>
                  <p className="text-muted-foreground text-xs mt-1">
                    {formatDateRange(competition.start_date, competition.submission_deadline)}
                  </p>
                  <p className="text-muted-foreground text-xs mt-1">
                    {isEnded
                      ? "Review period ended"
                      : `${competition.project_count} project${competition.project_count !== 1 ? "s" : ""} to review`}
                  </p>
                </div>
              </Card>
            );
```

Rationale: `ended` items render in the same *outstanding* group (as the user asked — "not done") but are non-clickable (no `<Link>`), muted, and carry the explicit "Review period ended" copy so the reviewer understands why they can't act on it.

- [ ] **Step 3: Start the dev server and verify visually**

```bash
cd src/web-ui && npm run dev
```

Then in a separate terminal:

```bash
source .env.claude
```

Use the Playwright MCP server to navigate to `$TEST_APP_URL/my-reviews`, log in with `$TEST_USER_EMAIL` / `$TEST_USER_PASSWORD`, and confirm:

- In-progress competitions render with white card + clickable link (unchanged behavior).
- If no `ended` competitions exist in the test DB, seed one via the Django admin (use the new "End review period for selected competitions" action on a competition the test user reviews) and reload the page.
- `ended` competitions render as muted, non-clickable cards in the outstanding group with "Review period ended" copy.
- Completed competitions still render in the bottom group with the check icon.

- [ ] **Step 4: Lint**

```bash
cd src/web-ui && npm run lint
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
jj commit -m "Render ended review period as not-done on My Reviews"
```

---

## Task 8: Confirm detail page behavior for `ended` reviews

**Files:**
- Modify (if needed): `src/web-ui/src/app/my-reviews/[competitionId]/CompetitionProjects.tsx`
- Modify (if needed): `src/web-ui/src/app/my-reviews/[competitionId]/page.tsx`

- [ ] **Step 1: Start a new changeset**

```bash
jj new -m "Handle ended review period on competition detail page"
```

- [ ] **Step 2: Inspect the detail page's use of `my_review_status`**

From the repo root:

```bash
grep -n my_review_status src/web-ui/src/app/my-reviews/[competitionId]/*.tsx
```

If the detail page exposes any "mark as complete" button or other mutation UI gated on `my_review_status === "in_progress"`, add a clause treating `ended` the same as `completed`: disable / hide the action and show read-only copy ("Review period ended — rankings are preserved as-is").

If `my_review_status` is only used to branch between already-implemented `in_progress` vs `completed` UI (e.g., a "Mark complete" button vs a completed badge), add an explicit `else if (my_review_status === "ended")` branch rendering a muted "Review period ended" banner with no action. Rankings and project list remain visible and read-only.

- [ ] **Step 3: Update the detail page if the inspection showed interactive elements**

Adjust the component so that:
- Any mutating call (e.g., to `update_review_status` or to re-rank projects) is not rendered / invoked when `my_review_status === "ended"`.
- The page shows a clear "Review period ended" notice.

If no changes are required (the inspection shows the page already handles non-`in_progress` states identically to `completed`), skip to Step 4.

- [ ] **Step 4: Verify manually via Playwright**

Navigate into an `ended` competition's detail page and confirm:
- Project rankings are visible.
- No "Mark complete" / ranking-update controls are actionable.
- A clear "Review period ended" notice is shown.

- [ ] **Step 5: Lint**

```bash
cd src/web-ui && npm run lint
```

Expected: no errors.

- [ ] **Step 6: Commit (skip if no changes were required)**

```bash
jj commit -m "Treat ended review period as read-only on detail page"
```

---

## Task 9: Full CI check

- [ ] **Step 1: Start a new changeset**

```bash
jj new -m "CI verification for end review period feature"
```

- [ ] **Step 2: Run full CI from repo root**

```bash
make ci
```

Expected: backend lint + tests pass; web-ui lint passes; Terraform unchanged.

- [ ] **Step 3: Fix anything that fails**

Address root causes; do not mask with `--no-verify` or equivalent.

- [ ] **Step 4: Commit (squash-describe if empty)**

If CI passed with no changes needed, discard this empty changeset:

```bash
jj abandon
```

Otherwise commit the fixes:

```bash
jj commit -m "Fixups from CI run"
```

---

## Self-review checklist (already applied)

- **Spec coverage:** model change (Task 1), services/review scaffolding (Task 2), DjangoReviewHandler (Task 3), HandlerServices registration (Task 4), admin action (Task 5), API schema + guard (Task 6), frontend list rendering (Task 7), detail page read-only (Task 8), CI (Task 9).
- **No placeholders:** all code blocks are concrete; no TODO / TBD.
- **Type consistency:** `end_review_period(competition_id: UUID) -> int` is identical across interface, implementation, and admin call sites. `HANDLERS.reviews` is used consistently (never instantiated). `ReviewStatus.ENDED` and `ReviewStatusEnum.ENDED` / `"ended"` match.
