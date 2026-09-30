# Design: competition reviewer groups

## Context

- `CompetitionReviewer` rows (`apps/projects/models.py`) are the access gate
  today. Every `/api/my-review/*` endpoint looks up the caller's row
  (`api/routers/my_review.py`), and `replace_ballot` raises
  `ReviewerNotAssignedError` without one
  (`services/review/django_impl/handler.py`). Nothing checks
  `Competition.status`.
- The tally counts only `completed` rows (`get_competition_tally` in
  `services/review/django_impl/query.py`). Rows in `in_progress` or `ended`
  never contribute, and neither do rows without rankings unless they are
  `completed` (an abstention).
- `ended` is written only by `end_review_period`, which is reached only from
  the admin bulk action. The web-ui reads it to lock the ballot
  (`MyRanking.tsx`, `isEnded`).
- `Competition.save` forces `closed` whenever a winner is assigned.
- Inactive and system users can't authenticate (`inactive-account-exclusion`,
  `system-users` specs). The eligibility check in this change repeats that rule
  in the domain, so it doesn't depend on the auth layer.
- pytest runs real migrations, so seeded rows exist in tests.

## Goals / Non-Goals

**Goals:** one access rule, computed from the competition and the user and
used by every review endpoint; rows only for reviews that were started;
existing data cleaned to match.

**Non-Goals:** any change to ballots, the tally rule, or API response shapes;
a UI for panels outside the Django admin; closing reviews on a date.

## Decisions

### A dedicated `ReviewerGroup` model, not `auth.Group`

`ReviewerGroup(name unique, includes_all_users bool, members M2M User)` lives
in `apps/projects`, and `Competition.reviewer_group` is an FK to it with
`on_delete=PROTECT`.

Pointing the FK at `auth.Group` instead was rejected for three reasons:
- auth groups carry permissions and are returned by `/api/auth/me`, so a panel
  would show up as a role;
- "Everyone" would need either name-magic or a stored row for every user;
- an auth group's members are edited from each user's page, which is the wrong
  direction for putting a panel together. The dedicated model gets a
  `filter_horizontal` member picker on its own page.

### "Everyone" is a flag, not stored membership

Membership in a flagged group is always true. Membership in a panel is a row
in the `members` table. Storing a row per user, kept in sync
from the `post_save` of `User`, was rejected because rows drift: bulk creates,
data migrations and fixtures all skip the signal. Stored rows would also bring
back exactly the "someone forgot" failure this change removes.

Eligibility (`is_active and not is_system_user`) is a separate condition from
membership. A deactivated panel member stays on the panel but has no access.

### One access check in the review service

The whole rule is one queryset, `reviewable_competitions(user_id)` in
`services/review/django_impl/query.py`. It returns competitions in `voting`,
where the user is eligible, whose group either includes all users or has the
user as a member (an `Exists` on the members table, not a join, so a
competition comes back once). Every access decision is built on it:

- `can_review(user_id, competition_id)` is the write gate.
- `review_competitions_for(user_id)` is the list: the union of reviewable
  competitions and competitions where the user has a row. Each comes back with
  its derived status and whether the user can still write.
- `get_review_competition(user_id, competition_id)` is the same for one
  competition, or None when the user can neither review it nor has a row.
- `can_view_review_project(user_id, project_id)` checks the project endpoint.
- The handler's write gate uses the queryset directly.

A per-object `has_member` method on the model was considered and dropped. It
would have been a second copy of the rule that could drift from the queryset.

The router stops querying `CompetitionReviewer` directly. Read endpoints
(detail, project) allow access when `can_review` holds **or** a row exists,
which is how history stays readable. Write endpoints (rankings, status)
require `can_review`.

An error has to tell the router which response to send. A user with no access
and no row gets `ReviewerNotAssignedError`, which maps to 404 as today. A user
with a row who has lost access gets `ReviewClosedError`, which maps to 400 as
today. Both status codes are already declared on those endpoints, so no schema
in the OpenAPI spec changes. Only the endpoint descriptions change, because
they are generated from the rewritten docstrings.

### The row is created by the first write, inside the handler

`replace_ballot` and a new `set_review_status` handler method both call
`CompetitionReviewer.objects.get_or_create(user, competition)` once the
access check has passed. `replace_ballot` first validates the payload, so a
rejected first ballot creates no row. The existing `(user, competition)` unique constraint makes
concurrent first writes safe: `get_or_create` retries the read on
`IntegrityError`.

The status endpoint moves from a bare `.update()` in the router into the
handler, so the gate and the row creation sit in one place. The rule that a
`completed` ballot can't be re-ranked until reopened stays. The "closed
statuses" check shrinks to `completed` plus the competition gate.

### `ended` derived at the edge

`ReviewStatus` keeps `IN_PROGRESS` and `COMPLETED`. A small function,
`effective_status(row_status, competition_status)`, returns `ended` when the
competition is not in `voting` and the row is not `completed`. It is used in
both response builders, and a missing row counts as `in_progress`. The API's
`ReviewStatusEnum` keeps `ENDED`, so the web-ui needs no change.

Deriving it means past competitions read correctly without a sweep. An
unfinished review on a closed competition reads as `ended` whether or not
anyone ever ran the old action.

### Status alone opens and closes reviewing

`review_ended_at` and date-based closing were both considered and dropped.
The admin already moves competitions through `voting` and assigns a winner,
which forces `closed`. A second control would be another step to forget. The
cost is that ballots stay editable between opening the voting results and
assigning the winner. To freeze them first, move the competition to `closed`
by hand.

### Data migration

In order, in one migration file after the schema migration:

1. Seed Everyone with `get_or_create`.
2. Backfill `reviewer_group` on every competition.
3. Delete rows where `status != completed` and no `ProjectRanking` exists for
   `(reviewer=user, competition)`. Use an `Exists` subquery.
4. Update `status=ended` to `in_progress`.

Steps 3 and 4 don't change any tally, because neither kind of row was counted.
The reverse is a no-op, so the schema migrations can still roll back, but
deleted rows don't come back.

The FK goes in over three migrations: add it as nullable, run the data
migration, then alter it to non-null with `default=everyone_reviewer_group_id`.
That callable uses `get_or_create`, so factories and flushed test databases
work without a fixture. The `ENDED` choice is removed by an `AlterField` after
the data migration.

## Risks / Trade-offs

- **Irreversible deletion.** → Before deploying, count the affected rows on
  production (`status != completed` and no rankings) and record the number in
  the PR. The data carries no meaning beyond "was assigned".
- **Access check per request.** For a panel, the check is one extra
  `exists()` query per review call. For Everyone, it is none. This is
  negligible at current volume.
- **You can no longer exclude one person from a competition.** For Everyone,
  the way is to switch the competition to a panel. A shared panel is edited in
  one place for every competition that uses it.
- **Large test churn.** Most tests in `api/routers/test_my_review.py` and
  `services/review/django_impl/test_*.py` set up access with
  `CompetitionReviewerFactory` on a `pending` competition. → Add factory
  helpers (`voting_competition(group=...)`, `review_of(user, competition, ...)`)
  first, and rewrite tests against them so their intent reads as the access
  rule.
- **Reviewers keep editing until the status changes.** This is intended, and
  noted above.

## Migration Plan

Deploy the schema and data migrations together; no feature flag is needed.
Rollback: revert the code and reverse the migrations. The new field and table
are dropped. Deleted assignment rows stay deleted, and without them the old
code shows those users nothing. After a rollback, an admin would have to press
the old button again for any competition still in `voting`.
