# Tasks: competition reviewer groups

All paths are under `src/django-backend/`.

## 1. Model and schema

- [ ] 1.1 Add `ReviewerGroup` to `apps/projects/models.py`, with these fields:
  `name` (unique), `includes_all_users` (bool, default False), and `members`
  (M2M to `AUTH_USER_MODEL`, `blank=True`, `related_name="reviewer_groups"`).
  Add a `has_member(user)` method: always true when flagged, otherwise
  `members.filter(pk=user.pk).exists()`. Add `everyone_reviewer_group_id()`,
  which does `get_or_create` on name "Everyone" and returns the pk.
- [ ] 1.2 Add `Competition.reviewer_group` as a nullable FK with
  `on_delete=PROTECT`, and generate the schema migration.
- [ ] 1.3 Add `ReviewerGroupFactory` to `tests/factories.py`, plus helpers that
  name the access rule: `voting_competition(group=None, **kw)` and
  `review_of(user, competition, status=..., ranked=[...])`.
- [ ] 1.4 Tests in `apps/projects/test_reviewer_groups.py`: Everyone exists
  after migrations and is flagged; `has_member` is true for anyone on a flagged
  group and exactly the members on a panel; deleting a referenced group raises
  `ProtectedError`. `make test` passes.

## 2. Data migration

- [ ] 2.1 Write the data migration from design.md, steps 1 to 4: seed
  Everyone, backfill `reviewer_group`, delete rows that are not `completed` and
  have no rankings, and convert `ended` to `in_progress`. The reverse is a
  no-op.
- [ ] 2.2 Follow it with a migration that makes `reviewer_group` non-null with
  `default=everyone_reviewer_group_id`, and one that removes `ENDED` from
  `ReviewStatus` choices. `makemigrations --check --dry-run` reports nothing.
- [ ] 2.3 Write a migration test in the style of
  `apps/projects/test_winner_announced_at_backfill.py`. Build a competition
  holding an untouched `in_progress` row, an untouched `ended` row, an `ended`
  row with rankings, a `completed` row with rankings and a `completed` row
  with none. Assert:
  - the first two are gone;
  - the third is `in_progress` with its rankings;
  - the last two are unchanged;
  - the competition is on Everyone;
  - `get_competition_tally` gives the same counted ballots and tiers before
    and after.

  `make test` passes.
- [ ] 2.4 Write the production pre-flight query (rows the deletion will
  remove, per competition) into the PR description, and state the count seen.

## 3. Access rule in the review service

- [ ] 3.1 In `services/review/`, add `can_review(user, competition)` and
  `review_competitions_for(user)` to the query interface and the Django
  implementation. The latter returns the union of reviewable `voting`
  competitions and competitions where the user has a row, each with its row
  status or None. Add `effective_status(row_status, competition_status)`
  next to `eligibility.py`.
- [ ] 3.2 Tests in `services/review/django_impl/test_query.py`. For
  `can_review`, cover each part of the rule: every non-`voting` status, an
  inactive user, a system user, a non-member of a panel, and a member of a
  panel. For `review_competitions_for`, check the union: a closed competition
  with a row is listed, a closed competition without one isn't, and an open
  one without a row is. Add a table test for `effective_status`. Rewrite the
  `ENDED` case in the existing tally tests to use `in_progress` on a closed
  competition. `make test` passes.

## 4. Writes create the row

- [ ] 4.1 Change `replace_ballot`. Without access, raise
  `ReviewerNotAssignedError` when the user has no row and `ReviewClosedError`
  when they do. With access, `get_or_create` the row, then keep the existing
  rule that a `completed` ballot can't be re-ranked, plus the duplicate and
  eligibility checks.
- [ ] 4.2 Add `set_review_status(user_id, competition_id, status)` to the
  handler, with the same gate and `get_or_create`. Remove `end_review_period`
  from the interface and the implementation.
- [ ] 4.3 Tests in `services/review/django_impl/test_handler.py`:
  - the first ballot save creates one `in_progress` row;
  - the first status change to `completed` creates an abstention that the
    tally counts;
  - a save after the competition closes raises `ReviewClosedError` and
    changes nothing;
  - a non-member raises `ReviewerNotAssignedError`;
  - two calls leave one row.

  Delete the `end_review_period` tests. `make test` passes.

## 5. Router

- [ ] 5.1 In `api/routers/my_review.py`:
  - the list uses `review_competitions_for` and `effective_status`;
  - detail and project allow access when `can_review` holds or a row exists,
    and otherwise return 404. Detail reports `effective_status`, treating a
    missing row as `in_progress`;
  - the status endpoint calls `set_review_status`, maps the two errors to 404
    and 400, and keeps rejecting an `ended` payload.

  Remove every direct `CompetitionReviewer` query from the router.
- [ ] 5.2 Rewrite `api/routers/test_my_review.py` against the new factory
  helpers. Add scenarios from the spec:
  - a user who registered late sees the open competition;
  - opening a ballot and a project creates no row;
  - a panel non-member gets 404;
  - a `pending` competition is neither listed nor openable;
  - a past reviewer reads a closed ballot;
  - a non-reviewer gets 404 on a closed one;
  - an `in_progress` row on a closed competition lists as `ended`;
  - assigning a winner makes further ranking and status writes return 400.

  Keep the existing projection, image and N+1 tests, with their setup
  switched to the helpers. `make test` passes.

## 6. Admin

- [ ] 6.1 Register `ReviewerGroupAdmin` in `apps/projects/admin.py`:
  `list_display` with name, flag and member count; `filter_horizontal`
  members; `has_delete_permission` is False for the flagged group.
- [ ] 6.2 In `CompetitionAdmin`, add `reviewer_group` to the form. Remove the
  `end_review_period` action, the `_add_all_reviewers` branch of
  `response_change` (and the override, if nothing is left in it), and the
  button in `templates/admin/competition_change_form.html`. Keep the
  voting-results link. Change the `reviewer_count` column label to "Reviews
  started".
- [ ] 6.3 Delete `apps/projects/test_admin_end_review_period.py`. Add admin
  tests: `has_delete_permission` is False for Everyone and True for an
  unreferenced panel, and the change form renders without the removed button.
  `make test` passes.

## 7. Checks

- [ ] 7.1 From `src/django-backend/`, run `make lint`, `make extra-tests` and
  `make test`. All pass, and `backend-openapi.json` is unchanged.
- [ ] 7.2 From `src/web-ui/`, run `make test`. It passes, with no frontend
  change.
- [ ] 7.3 Manual check against a local seeded instance:
  - Move a competition to Voting and confirm the test user sees it under
    `/my-reviews` without any admin assignment.
  - Confirm that opening the ballot doesn't raise the admin's "Reviews
    started" count, and that ranking a project does.
  - Assign a winner and confirm the ballot reads as locked on the competition
    page.
  - Switch a second voting competition to a panel that doesn't include the
    test user, and confirm it disappears from `/my-reviews`.
