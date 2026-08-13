# Merge Product Updates into Updates — Design

Date: 2026-08-13
Status: design (pre-implementation)

## Summary

The house project carries three channels: `Updates`, `Competition Winners` and
`Product Updates`. Two of those are deliberate; `Updates` is not. It exists on
the house project only because the `post_save` signal in
`apps/projects/signals.py:14` gives every Project a default channel, and the
house project is a Project. `Product Updates` and `Competition Winners` were
seeded to match the two legacy `email_opt_in_*` booleans 1:1, so the per-category
opt-outs survived the move into the channel model
([`2026-05-13-articles-following-news-design.md`](2026-05-13-articles-following-news-design.md)).

The result is two channels doing one job, with different subscriber lists.
Everyone active at migration time is on `Updates` (`follows/0002` seeded it
`email_enabled=True` unconditionally); only those who had not opted out of
platform-update email are on `Product Updates`. Anyone who opted out years ago
still receives whatever lands in `Updates`.

This change collapses the two into one channel named `Updates`, carrying the
`Product Updates` subscriber list. It first removes the `platform_updates`
broadcast type, so that by the time the channels merge there is exactly one way
to reach the surviving channel: publishing an article.

## Goals

- One house channel for general announcements, with a subscriber list that
  honours the original opt-outs.
- One delivery path to that channel — article publication.
- Leave `Competition Winners` alone.

## Non-goals

- Merging `Competition Winners` too. Whether it is a genuinely separate opt-out
  or the second fossil of the same legacy pair is a real question, but not this
  change's question.
- Any immediate-send path for house articles (see decision 1).
- Backfilling historic `BroadcastEmail` rows into Articles.
- Fixing the empty-`Follow` read behaviour described in
  `follows/0004_sweep_both_off_rows.py`. It grows slightly here and is
  knowingly left alone.

## Decisions

### 1. Accept the loss of immediate delivery

Broadcast emails send immediately to everyone opted in. Articles have no
immediate path — `create_notifications_for_article`
(`services/notifications/django_impl/handler.py:200`) snapshots each
recipient's `article_email_frequency` and lets the digest deliver.

So removing `platform_updates` changes house announcements from "goes now" to
"goes at the recipient's cadence": `hourly` by default, later for `daily` and
`weekly` users, never for `never`. That is accepted. The alternative — the
`Channel.send_policy` carve-out parked in
`openspec/changes/archive/2026-08-07-add-article-authoring/design.md:172` —
rebuilds the split this change exists to remove.

Users on `article_email_frequency = "never"` see no change:
`list_opted_in_for_broadcast_type` already excluded them from broadcasts.

### 2. Delete the enum member outright

`BroadcastEmailType.PLATFORM_UPDATES` goes. Existing `BroadcastEmail` rows keep
`email_type="platform_updates"` in the column — it is a plain `CharField` — and
remain readable in the admin, rendering as the raw string rather than
"Platform Updates". `list_filter` (`apps/emails/admin.py:68`) stops offering it,
since it renders from current choices.

The table is an audit trail, not a browsing surface. Cheaper than keeping a dead
enum member alive behind a hidden form field, and cheaper than a content
backfill.

### 3. Merge by rename, not by deleting followers

The obvious reading of "make `Updates` have the `Product Updates` follower set"
is to delete `FollowedChannel` rows from `Updates`. The inverse reaches the same
end state without touching the list being kept:

1. Reassign any house articles from `Updates` to `Product Updates`.
2. Delete the `Updates` channel — cascading its `FollowedChannel` rows.
3. Rename `Product Updates` to `Updates`.

The surviving row already holds the correct subscribers. Order is forced twice
over: `Article.channel` is `on_delete=PROTECT`, so reassignment must precede the
delete; `unique_together = (("project", "name"))` on `Channel` means the rename
must follow it.

`Notification` rows are FK'd to the article, not the channel, so reassignment
leaves bell history intact.

### 4. Remove the broadcast type first

Doing the enum removal ahead of the merge means
`BROADCAST_CHANNEL_BY_EMAIL_TYPE` (`services/users/django_impl/query.py:15`) is
down to one entry by the time the channels collapse. `anoint_house_project`
(`apps/follows/services.py:64`) derives its channel list as
`[DEFAULT_CHANNEL_NAME, *BROADCAST_CHANNEL_BY_EMAIL_TYPE.values()]`, so it lands
on `["Updates", "Competition Winners"]` with no code change. Had the merge come
first, that list would contain `"Updates"` twice.

### 5. A plain data migration

Automatic on deploy, matching how the current state was reached
(`follows/0002`). Not a management command: a manual step drifts across
dev/staging/prod. Reverse is a documented no-op, following `0004`'s precedent —
cascaded follower rows cannot be reconstructed and a reverse that pretends
otherwise misleads whoever reads the rollback plan.

## Changes

### Backend

- `apps/emails/models.py:9` — delete `PLATFORM_UPDATES`. Nothing references it
  symbolically; remaining hits are string literals in tests.
- `apps/emails/migrations/` — `AlterField` for the narrowed `choices`. No SQL,
  but CI runs `makemigrations --check`.
- `services/users/django_impl/query.py:15` —
  `BROADCAST_CHANNEL_BY_EMAIL_TYPE` becomes
  `{"competition_results": "Competition Winners"}`.
  `list_opted_in_for_broadcast_type` already returns `none()` for an unmapped
  type, so a stray `platform_updates` row sends to nobody rather than raising.
- `apps/follows/migrations/0006_merge_product_updates_into_updates.py` — the
  merge, per decision 3, inside one `transaction.atomic()`. Depends on
  `follows/0005_drop_legacy_booleans` and
  `articles/0005_alter_article_listing_image` (for
  `apps.get_model("articles", "Article")`).

The migration resolves the house project via `is_house_project=True`, not the
slug `0002` used — the flag did not exist when `0002` was written, and
`anoint_house_project` can have moved it. No house project, or no
`Product Updates` channel: log and return, the same defensive shape as `0002`.
No `Updates` channel: skip to the rename.

### Frontend

None. `platform_updates` does not appear in `backend-openapi.json` —
`BroadcastEmail` is admin-only — so there is no type regeneration. Nothing in
`src/web-ui/` looks a channel up by name.

### Tests

No test for the migration itself.

`tests/factories.py:166` (`make_broadcast_follower`) indexes
`BROADCAST_CHANNEL_BY_EMAIL_TYPE`, so `"platform_updates"` becomes a `KeyError`.
Its callers in `tests/test_broadcast_emails.py`,
`tests/test_inactive_user_emails.py` and
`services/users/django_impl/test_query.py` move to `competition_results` where
the assertion is about the mechanism, and are deleted where they only restate
it. Also touched: `apps/follows/tests/test_anoint_house_project.py`,
`apps/follows/tests/test_auto_follow_signal.py`,
`services/follows/django_impl/test_integration.py`,
`services/notifications/django_impl/test_article_fanout.py`.

### Specs

Delta specs land in one OpenSpec change,
`openspec/changes/merge-product-updates-into-updates/`:

- `openspec/specs/project-following/spec.md:55` — the "two further channels"
  requirement and the "exactly three channels" scenario.
- `openspec/specs/async-broadcast-send/spec.md:77` and its scenario at line 102.
- `openspec/specs/notifications/spec.md:511`.

## Consequences

**BREAKING for subscribers of `Updates` who had opted out of platform updates.**
They lose the channel and receive nothing further from it. That is the intent —
their original opt-out is being honoured — but it is an unsubscribe event, not a
no-op. Worth counting articles per house channel on prod before running the
migration: if `Updates` has never carried content, nobody notices.

More `Follow` rows on the house project end up with zero `FollowedChannel`
rows — users who had opted out of both categories. The state is already
tolerated and documented in `follows/0004_sweep_both_off_rows.py`: they read as
"Following" with nothing ticked, and ticking a channel in the popover repairs
it.

`Updates` becomes both the default channel every project gets and the house
project's announcement channel. Anything later wanting to treat the house
project's announcement channel specially can no longer identify it by name.
