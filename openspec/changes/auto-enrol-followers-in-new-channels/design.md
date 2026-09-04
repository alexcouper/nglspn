## Context

`FollowedChannel(follow, channel)` row existence *is* the subscription — there
are no per-medium booleans left on it (archived decision 1). Rows are written
in exactly three places today, and all three enrol a snapshot of the channels
that exist at the moment a `Follow` is created:

| Writer | Trigger |
|---|---|
| `DjangoFollowHandler.follow` (`services/follows/django_impl/handler.py:17`) | `POST /api/projects/{slug}/follow`, only when the `Follow` is new |
| `create_house_project_follow` (`apps/follows/services.py:21`) | `post_save` on `User`, `created=True` |
| `anoint_house_project` (`apps/follows/services.py:48`) | admin action, and the named broadcast channels only |

Nothing writes a row when a `Channel` appears. Reversing archived decision 7
means adding a fourth writer keyed on channel creation rather than follow
creation.

The constraint that shapes the rest: channels are created from the Django admin
(`apps/follows/admin.py:7`), and the admin writes `Channel` through the model
manager. It has no route through the service layer.

## Goals / Non-Goals

**Goals:**

- A channel created on a project reaches everyone already following that
  project, by every creation route that goes through the model.
- Unfollowing the project remains the single, sufficient way out.
- No schema change, no API change, no frontend change.

**Non-Goals:**

- Backfilling follower/channel pairs that are already missing.
- Any per-channel control over whether enrolment happens.
- Changing when notifications or emails are *sent*; only who is subscribed.

## Decisions

### 1. A `post_save` receiver on `Channel`, not a service-layer call

`HANDLERS.articles.add_channel` (`services/articles/django_impl/handler.py:260`)
has exactly one caller, `api/routers/channels.py:71`. Putting enrolment there
would miss the admin, which is the route being asked for, and the shell, and
`create_default_channel` (`apps/projects/signals.py:25`). A receiver on the
model catches all of them.

The cost is the usual one: `Channel.objects.bulk_create()` sends no `post_save`
and so enrols nobody. The `project-following` spec already carries this caveat
for the default-channel receiver, and nothing in the codebase bulk-creates
channels.

Receivers for the follows app go in a new `apps/follows/signals.py` imported
from `FollowsConfig.ready()`, which does not exist yet. That is the convention
`apps/projects/apps.py:8` and `apps/users/apps.py:8` already follow. The
alternative — hanging it off `apps/projects/signals.py`, where the existing
`Channel`-touching receiver lives — was rejected: that one is there because it
fires on `Project`; this one fires on a follows model and belongs with it.

### 2. `bulk_create(..., ignore_conflicts=True)` over a `get_or_create` loop

One statement per batch instead of two queries per follower. `ignore_conflicts`
covers the `(follow, channel)` unique constraint against a `follow_channel`
call racing in between, which is the only way a row can already exist for a
channel that was just created. `batch_size=1000` keeps the parameter count off
the Postgres limit on the house project.

The receiver runs inside whatever transaction the caller holds — the admin's
change view is atomic — so a rolled-back channel insert takes its enrolments
with it.

### 3. Synchronous, with an escape hatch if it stops being cheap

One insert per follower of the project. For every project except the house one
that is a handful of rows. For the house project it is one row per active user,
in the admin request that created the channel.

Enqueuing it instead — the article fan-out's pattern, `_enqueue_fan_out` at
`services/articles/django_impl/handler.py:62` — buys nothing at current scale
and costs the guarantee that the enrolment either commits with the channel or
not at all. Revisit when the admin save gets slow enough to notice, not before.

### 4. `follow()` keeps its enrolment loop

The receiver only covers channels created *after* a follow exists. Channels
that predate the follow are still `follow()`'s job. Both writers are needed;
neither subsumes the other.

What does change is the comment above that loop
(`services/follows/django_impl/handler.py:18-22`), which explains that
later-added channels are deliberately left to the user. It goes. The behaviour
it documents — a re-POST not enrolling anyone — is untouched, but it is now
unobservable: by the time anyone re-POSTs, the receiver has already enrolled
them.

### 5. `created=True` only

A rename is a `save()` on an existing channel and must not enrol anyone; a
follower who unticked that channel would silently reappear on it the next time
an admin fixed a typo.

### 6. What this does to the "unfollow your last channel" rule

`unfollow_channel` deletes the `Follow` when it removes the last
`FollowedChannel` (`handler.py:66-79`), so a user who unticks everything is
fully unfollowed and stays out of reach of future channels. That is the exit,
and it now carries more weight than it did.

A `Follow` left with zero channels by some other route — channel deletion
cascading, a racing double-unfollow, the `follows/0004` sweep; see archived
decision 6 — still reads as "Following" and will now be enrolled in the next
channel created. It is the same tolerated state as before, behaving
consistently with every other follow.

## Risks / Trade-offs

**A follower who deliberately unticked channels gets pulled onto a new one** →
Intended, and the point of the change. The exit is unfollowing the project,
which the popover reaches in one click and which the last-channel rule performs
implicitly.

**An admin adding a house-project channel now subscribes the entire user base
in one save** → No mail is sent by that act. The broadcast path
(`services/users/django_impl/query.py:51`) only mails a channel's followers
when a `BroadcastEmail` whose type maps to that channel name is sent, and
adding a new type to `BROADCAST_CHANNEL_BY_EMAIL_TYPE` is a code change.
Article fan-out reaches the bell and the digest, gated per user by
`article_email_frequency`.

**Admin save latency on the house project** → Batched inserts now; decision 3
records the async fallback if it stops being enough.

**Data migrations create channels through historical models and enrol nobody**
→ Pre-existing, shared with `create_default_channel`. A migration that adds a
channel and wants followers on it has to write the rows itself, as
`follows/0002` already does.
