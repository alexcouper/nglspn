# Tasks: auto-enrol followers in new channels

All paths are relative to `src/django-backend/`.

## 1. The receiver

- [x] 1.1 Add `apps/follows/signals.py` with a `post_save` receiver on `Channel`
  that returns immediately unless `created` is true.
- [x] 1.2 Insert one `FollowedChannel` per existing `Follow` on
  `instance.project_id` with a single `bulk_create(..., batch_size=1000,
  ignore_conflicts=True)`, iterating the follows queryset rather than
  materialising it.
- [x] 1.3 Comment why `ignore_conflicts` is there — a `follow_channel` call
  racing the channel insert is the only way a row for a brand-new channel can
  already exist — and why the receiver hangs off the model rather than
  `HANDLERS.articles.add_channel`: the Django admin writes `Channel` directly
  and never reaches the service layer.
- [x] 1.4 Give `FollowsConfig` in `apps/follows/apps.py` a `ready()` that
  imports the module, matching `apps/projects/apps.py:8` and
  `apps/users/apps.py:8` including the `# noqa: F401, PLC0415`.

## 2. Remove the contradicted comment

- [x] 2.1 Replace the comment at `services/follows/django_impl/handler.py:18-22`
  — it states that channels added after the follow are deliberately left to the
  user, which is what this change reverses. Keep a line explaining why the
  enrolment loop is still needed: it covers the channels that predate the
  follow, which the receiver never sees.

## 3. Tests

- [x] 3.1 In `apps/follows/tests/test_channel_signal.py`, add a class covering
  the new requirement: a new channel enrols existing followers; a follower of a
  different project is untouched; a rename enrols nobody; a project's first
  channel (created by the `Project` receiver) enrols nobody and does not raise;
  a second enrolment run creates no duplicate and does not raise; a `Follow`
  with no `FollowedChannel` rows is enrolled like any other.
- [x] 3.2 Use the existing factories in `tests/factories.py` and assert on
  `FollowedChannel` rows directly, in the style of the neighbouring tests.
- [x] 3.3 Retarget the tests that assert a re-follow leaves a later-added
  channel unenrolled at a channel the user *unfollowed* instead — the
  behaviour is unchanged, but a channel added after the follow is now enrolled
  before any re-follow happens. That test lives in
  `services/follows/django_impl/test_handler.py`, not the router tests; add the
  router-level equivalent to `api/routers/test_follows.py` while there.
- [x] 3.4 Fix the setups that now hit the `(follow, channel)` unique
  constraint because they create a channel after the `Follow` and then insert
  the `FollowedChannel` row by hand: `_make_follow` in
  `services/follows/django_impl/test_query.py` and two tests in
  `api/routers/test_follows.py`.

## 4. Verify

- [x] 4.1 `make lint`
- [x] 4.2 `make extra-tests` — no API change is expected, so this confirms
  `backend-openapi.json` is still in sync.
- [x] 4.3 `make test` — 1427 passed
- [x] 4.4 `uv run python manage.py makemigrations --check --dry-run` — no model
  change, so this must report nothing to make.
- [ ] 4.5 Drive it in the running app: create a channel on a project in the
  Django admin and confirm a follower who predates it sees the channel ticked on
  `/profile/following`, then publish an article to it and confirm it reaches
  their bell.
