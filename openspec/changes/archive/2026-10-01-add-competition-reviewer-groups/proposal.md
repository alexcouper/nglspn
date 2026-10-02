# Proposal: competition reviewer groups

Issue: [#93](https://github.com/alexcouper/nglspn/issues/93), point 4.

## Why

Today you can only review a competition if you have a `CompetitionReviewer`
row for it, and the only thing that creates those rows in bulk is an admin
pressing **Add all users as reviewers** (`CompetitionAdmin.response_change`,
`apps/projects/admin.py`). One round the button was missed: nobody had a row,
`/my-reviews` was empty for everyone, and no votes were cast. Anyone who
registers after the button is pressed is left out too.

The competition's status plays no part in reviewing. Rankings stay editable
after a competition is `closed` unless an admin runs the **End review period**
bulk action, and nobody has been running it.

Who may review, and when, should follow from the competition itself: its
status, and a named group of users. That group is Everyone for now, and a fixed
judging panel later. Rows should exist only for reviews that have actually been
started.

## What Changes

- **New `ReviewerGroup` model** in `apps/projects`: a named set of users.
  - A migration seeds **Everyone**, flagged `includes_all_users`. Its members
    are every user, resolved when checked rather than stored.
  - Other groups (panels) keep an explicit member list, edited in the Django
    admin.
- **`Competition.reviewer_group`**: an FK to `ReviewerGroup`. New competitions
  default to Everyone, and existing competitions are backfilled to Everyone.
- **Review access is derived, not stored.** A user may review a competition
  when all of these hold:
  - the competition's status is `voting`;
  - the user is active and not a system user;
  - the user is a member of the competition's reviewer group.

  The `/api/my-review/*` endpoints switch to this check.
- **Status is the only open/close control.** Reviewing opens when an admin
  moves the competition to `voting`. It shuts when the status moves on, either
  by hand or by setting a winner, which forces `closed` in `Competition.save`.
  To freeze ballots before choosing a winner, move the competition to `closed`
  first.
- **A reviewer row is created on the first write.** Saving a ballot or setting
  a status creates it. Reading a competition or its projects never does. A user
  with no row sees an empty ballot with status `in_progress`.
- **History stays readable through rows.** Once a competition has left
  `voting`, a user can still read it if they have a row, as `CompetitionReveal`
  does on closed competitions, but can't change anything. A user without a row
  gets 404 as today.
- **`ended` is derived, no longer stored.** The API returns `ended` when the
  competition is not in `voting` and the user's row is not `completed`.
  `in_progress` and `completed` stay the only stored values. The API enum is
  unchanged, so no schema changes and the web-ui needs no change.
- **BREAKING (data): the old assignment rows are removed.** A data migration
  deletes every reviewer row that is not `completed` and has no rankings, since
  those rows are only assignments. It converts the remaining `ended` rows to
  `in_progress`. `completed` rows, including abstentions, are untouched, so
  every past tally comes out the same. The deletion cannot be reversed.
- **Removed:**
  - the **Add all users as reviewers** button and its template;
  - the **End review period** admin action;
  - `end_review_period` in the review handler;
  - the `ENDED` choice on `ReviewStatus`.
- The admin **Reviewers** column now counts started reviews, not eligible
  users.

Out of scope:
- The rest of #93 (feed noise, auto open/close, feed split). Point 2's
  automatic status changes will open and close reviewing without further work,
  because access reads the status.
- Closing reviews on `voting_end_date`. That date stays display-only.
- Renaming `CompetitionReviewer` to fit its new meaning.
- A "not started" review status.

## Capabilities

### New Capabilities

- `competition-reviewer-groups`: who may review a competition and when, how
  the reviewer group is chosen, and when a review record exists.

### Modified Capabilities

None. No existing spec covers reviewing.

## Impact

- `apps/projects/models.py`: `ReviewerGroup`; `Competition.reviewer_group`;
  `ReviewStatus.ENDED` removed.
- Migrations: schema, plus data (seed Everyone, backfill competitions, delete
  assignment-only rows, convert `ended`). Before deploying, check the row count
  the deletion will remove on production.
- `services/review/`: a single access check, used by the query, the handler
  and the router. `replace_ballot` and status updates create the row on first
  write. `end_review_period` is removed, along with its tests
  (`apps/projects/test_admin_end_review_period.py`).
- `api/routers/my_review.py`: list, detail, rankings, status and project
  endpoints use the derived check. Response shapes are unchanged. The
  regenerated `backend-openapi.json` differs only in endpoint descriptions.
- `apps/projects/admin.py` and
  `templates/admin/competition_change_form.html`: reviewer group on the form,
  `ReviewerGroupAdmin`, the button and the bulk action removed.
- Tests that set up access by creating `CompetitionReviewer` rows
  (`api/routers/test_my_review.py`, `services/review/django_impl/test_*.py`)
  must set up group membership and a `voting` competition instead.
