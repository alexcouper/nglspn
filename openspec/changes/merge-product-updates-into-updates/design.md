## Context

The validated design lives at [`docs/superpowers/specs/2026-08-13-merge-product-updates-into-updates-design.md`](../../../docs/superpowers/specs/2026-08-13-merge-product-updates-into-updates-design.md). This document covers only the technical decisions needed to implement it.

Current state on the house project (`is_house_project = True`):

| Channel | Origin | Subscribers |
|---|---|---|
| `Updates` | `post_save` signal, `apps/projects/signals.py:14` | everyone active at `follows/0002`, plus every user created since |
| `Product Updates` | seeded by `follows/0002` from `email_opt_in_platform_updates` | everyone who had not opted out |
| `Competition Winners` | seeded by `follows/0002` from `email_opt_in_competition_results` | everyone who had not opted out |

`follows/0004_sweep_both_off_rows` collapsed the per-channel `email_enabled` boolean into row existence: a `FollowedChannel` row *is* the subscription.

## Goals / Non-Goals

**Goals:**

- One house channel named `Updates`, carrying the `Product Updates` subscriber list.
- One delivery path to it: publishing an article.
- Fresh installs and dev databases reach the same shape without a second code path.

**Non-Goals:**

- Merging `Competition Winners`.
- Any immediate-send path for house articles.
- Backfilling historic `BroadcastEmail` rows into Articles.
- Repairing the empty-`Follow` read behaviour in `services/follows/django_impl/query.py`.

## Decisions

### 1. Accept cadence-based delivery for house announcements

Broadcasts send immediately: `send_broadcast` (`services/email/django_impl/handler.py:327`) loops recipients calling `email.send()` inside the queued task. Articles have no such path — `create_notifications_for_article` (`services/notifications/django_impl/handler.py:200`) snapshots each recipient's `article_email_frequency` and leaves delivery to the digest.

So the removal changes house announcements from "goes now" to "goes at the recipient's cadence": `hourly` by default, later for `daily`/`weekly`, never for `never`.

**Alternative rejected:** the `Channel.send_policy` carve-out parked in `openspec/changes/archive/2026-08-07-add-article-authoring/design.md:172`. It rebuilds the immediate/cadence split this change exists to remove.

Users on `article_email_frequency = "never"` are unaffected — `list_opted_in_for_broadcast_type` already excluded them from broadcasts.

### 2. Delete the enum member rather than hiding it

`BroadcastEmailType.PLATFORM_UPDATES` goes. Existing rows keep `email_type="platform_updates"` in what is a plain `CharField`, so they still render in the admin — as the raw string, and no longer as a `list_filter` option (`apps/emails/admin.py:68` renders from current choices).

**Alternatives rejected:** hiding the choice via `formfield_for_choice_field` keeps a dead enum member alive and puts the removal in the admin rather than the model; backfilling old rows into Articles is a second content migration for an audit table nobody browses.

### 3. Merge by rename, not by deleting followers

Making `Updates` carry the `Product Updates` subscriber list by deleting `FollowedChannel` rows from `Updates` destroys the list being kept. The inverse reaches the same end state and touches only the list being discarded:

1. Reassign house articles from `Updates` to `Product Updates`.
2. Delete the `Updates` channel, cascading its `FollowedChannel` rows.
3. Rename `Product Updates` to `Updates`.

Order is forced twice: `Article.channel` is `on_delete=PROTECT`, so reassignment must precede the delete; `Channel.Meta.unique_together = (("project", "name"))` means the rename must follow it.

`Notification` rows are FK'd to the article, not the channel, so bell history survives the reassignment.

### 4. Remove the broadcast type before merging

With `platform_updates` gone from `BROADCAST_CHANNEL_BY_EMAIL_TYPE` (`services/users/django_impl/query.py:15`), `anoint_house_project` (`apps/follows/services.py:64`) derives `[DEFAULT_CHANNEL_NAME, *BROADCAST_CHANNEL_BY_EMAIL_TYPE.values()]` as exactly `["Updates", "Competition Winners"]` — correct for fresh installs with no code change. In the other order that list would contain `"Updates"` twice.

### 5. A plain data migration, resolved by flag

`apps/follows/migrations/0006_merge_product_updates_into_updates.py`, depending on `follows/0005_drop_legacy_booleans` and `articles/0005_alter_article_listing_image` (for `apps.get_model("articles", "Article")`), all inside one `transaction.atomic()`.

It resolves the house project via `is_house_project=True`, not the slug `0002` used — the flag did not exist when `0002` was written, and `anoint_house_project` can have moved it. No house project, or no `Product Updates` channel: log and return, the defensive shape `0002` established. No `Updates` channel: skip to the rename.

**Alternative rejected:** a management command with a dry-run. Safer to eyeball, but a manual step drifts across dev/staging/prod, and the follows app has no precedent for it.

Reverse is a documented no-op, following `0004`'s precedent — cascaded follower rows cannot be reconstructed, and a reverse that pretends otherwise misleads whoever reads the rollback plan.

## Risks / Trade-offs

**Users who opted out of platform updates lose the `Updates` channel** → Intended, but it is an unsubscribe event. Count articles per house channel on production before running the migration; if `Updates` has never carried content, nobody is affected in practice.

**The migration is irreversible** → Reverse is declared a no-op rather than faked. Recovery is forward-only: re-enrol affected users via the popover, or `anoint_house_project`.

**More house `Follow` rows with zero `FollowedChannel` rows** → Already tolerated and documented in `follows/0004_sweep_both_off_rows.py`. Affected users read as "Following" with nothing ticked; ticking a channel in the popover repairs it. Explicitly out of scope.

**`Updates` becomes overloaded** → It is now both the default channel every project gets and the house project's announcement channel, so nothing downstream can identify the latter by name. Anything needing that distinction later must add a field.

**The `async-broadcast-send` spec is already stale** → It states that broadcasts are "sent through the per-user article-digest path on each recipient's cadence; there is no longer a synchronous send-to-everyone behaviour". The code does not do this (decision 1). This change does not fix that sentence; it only removes the `platform_updates` mapping. Flagged so the discrepancy is not mistaken for something this change introduced.

## Migration Plan

1. Deploy the enum removal, the `choices` `AlterField`, and the channel-mapping change together with the data migration. One release.
2. `follows/0006` runs on deploy and performs the merge.
3. Verify: the house project has two channels; the surviving `Updates` channel's follower count matches the pre-migration `Product Updates` count.

Rollback: forward-only. Reverting the code leaves the merged channel in place, which is harmless — `anoint_house_project` and the auto-follow signal both operate on whatever channels exist.

## Open Questions

None.
