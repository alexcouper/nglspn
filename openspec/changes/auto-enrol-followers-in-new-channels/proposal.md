# Auto-enrol followers in new channels

## Why

Add a channel to a project today and the people already following that project
never see it. `DjangoFollowHandler.follow`
(`services/follows/django_impl/handler.py:17`) enrols channels only in the
branch where it *creates* the `Follow`, so a channel created afterwards reaches
nobody who was already there. The article fan-out selects recipients straight
off `FollowedChannel` (`services/notifications/django_impl/handler.py:216`), so
an article posted to that channel notifies nobody — no bell, no digest — while
the Following page shows the channel present and unticked.

New signups are enrolled in whatever channels exist at signup
(`create_house_project_follow`, `apps/follows/services.py:21`), so the audience
for a channel splits by signup date: everyone who joined after it was created,
nobody who joined before. On the house project, which every user is
auto-followed onto, that split is the whole existing user base.

That was a deliberate call — archived decision 7 in
[`2026-08-07-simplify-follow-and-cadence/design.md`](../archive/2026-08-07-simplify-follow-and-cadence/design.md),
on the grounds that a project owner should not be able to unilaterally push
into a follower's bell. We are reversing it. Following a project is the consent;
a follower who wants out unfollows the project, and then no future channel can
reach them either.

## What Changes

- **Creating a `Channel` enrols every existing follower of its project.** A
  `post_save` receiver on `Channel`, firing only for `created=True`, inserts a
  `FollowedChannel` row per existing `Follow` on that project. Channel
  subscription becomes opt-out *within* a followed project, while following the
  project itself stays opt-in.
- **The receiver, not the service handler, is the hook.** Channels are created
  from the Django admin (`ChannelAdmin`, `apps/follows/admin.py:7`), which
  writes the model directly and never reaches
  `HANDLERS.articles.add_channel` — the only caller of which is
  `api/routers/channels.py:71`. A signal covers both, plus the shell and the
  default-channel seeding in `apps/projects/signals.py:25`.
- **`apps/follows/apps.py` gains a `ready()`.** It has none today, so there is
  nowhere for a follows-app receiver to be registered from.
- **`follow()` keeps its enrolment loop.** It still covers the channels that
  existed *before* the follow, which the receiver never sees. Its comment about
  later-added channels being the user's own choice becomes wrong and goes.
- **No backfill of channels that already exist.** Existing follower/channel
  pairs stay as they are; this changes what happens from here on.

Not breaking: no model field, migration, API route, request or response shape
changes. `backend-openapi.json` is untouched and no frontend file changes.

### Explicitly out of scope

- **A per-channel "create quietly" switch.** Creating a channel sends no email
  by itself — the broadcast path (`list_opted_in_for_broadcast_type`,
  `services/users/django_impl/query.py:51`) mails a channel's followers only
  when a `BroadcastEmail` of a type mapped to that channel name in
  `BROADCAST_CHANNEL_BY_EMAIL_TYPE` is actually sent. Staging a channel before
  announcing it is therefore still possible; it just no longer happens by
  accident.
- **Repairing a `Follow` that has no `FollowedChannel` rows.** That state is
  tolerated deliberately (see archived decision 6 and the docstring at
  `services/follows/django_impl/query.py:69`). Such a follow will now be
  enrolled in future channels like any other, which is a side effect of this
  change, not its purpose.

## Capabilities

### Modified Capabilities

- `project-following`: a new requirement that channel creation enrols the
  project's existing followers, and a correction to **User can follow and
  unfollow a Project**, whose "Re-POST after the project added a new channel
  does not enrol the user" scenario can no longer arise — the follower is
  already enrolled by the time any re-POST happens.

## Impact

**Backend** (`src/django-backend/`):

- `apps/follows/signals.py` — new. The `post_save` receiver on `Channel`.
- `apps/follows/apps.py` — `FollowsConfig.ready()` imports it, matching
  `apps/projects/apps.py:8` and `apps/users/apps.py:8`.
- `services/follows/django_impl/handler.py` — the stale comment at lines 18–22
  goes; the code under it does not change.
- `apps/follows/tests/test_channel_signal.py` — extended with the enrolment
  cases.

**Not affected**: models and migrations (no schema change), the notification
fan-out and broadcast queries (they read `FollowedChannel` and do not care how
rows got there), every router, and the whole of `src/web-ui/`.

Data migrations that create channels use historical model classes, so the
receiver does not fire for them — the same limitation the existing
`create_default_channel` receiver has.
