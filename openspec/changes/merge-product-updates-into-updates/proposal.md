## Why

The house project carries three channels, but only two are deliberate. `Updates` exists on it by accident — the `post_save` signal in `apps/projects/signals.py:14` gives every Project a default channel, and the house project is a Project. `Product Updates` was seeded to preserve the legacy `email_opt_in_platform_updates` opt-out. Two channels now do one job with different subscriber lists: `follows/0002` seeded `Updates` with `email_enabled=True` unconditionally, so users who opted out of platform-update email years ago still receive anything published to `Updates`.

Full rationale: [`docs/superpowers/specs/2026-08-13-merge-product-updates-into-updates-design.md`](../../../docs/superpowers/specs/2026-08-13-merge-product-updates-into-updates-design.md).

## What Changes

- **BREAKING** Remove `BroadcastEmailType.PLATFORM_UPDATES`. Admins can no longer target platform updates by broadcast; the only route to the channel becomes publishing an article on the house project. Existing `BroadcastEmail` rows keep their `email_type` string and stay readable in the admin, rendering as the raw value.
- **BREAKING** Merge the house project's `Product Updates` channel into `Updates`, keeping the `Product Updates` subscriber list. Users who had opted out of platform-update email lose the `Updates` channel and receive nothing further from it — the intent is to honour that original opt-out, but it is an unsubscribe event for them.
- House announcements move from immediate delivery to each recipient's `article_email_frequency` cadence (`hourly` by default). Accepted deliberately; the `Channel.send_policy` alternative rebuilds the split this change removes.
- `BROADCAST_CHANNEL_BY_EMAIL_TYPE` drops to a single entry, which leaves `anoint_house_project` deriving the correct two-channel list for fresh installs with no code change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `project-following`: the house project has one extra seeded channel (`Competition Winners`), not two. The "exactly three channels" requirement becomes two.
- `async-broadcast-send`: `platform_updates` is no longer a valid `email_type`; recipient resolution maps only `competition_results`.
- `notifications`: the house-channel logging scenarios reference `Product Updates`, which no longer exists.

## Impact

**Backend.** `apps/emails/models.py:9` (enum member), a `choices` `AlterField` in `apps/emails/migrations/` (CI runs `makemigrations --check`), `services/users/django_impl/query.py:15` (channel mapping), and a new data migration `apps/follows/migrations/0006_merge_product_updates_into_updates.py`.

**Data.** The merge reassigns articles, deletes the `Updates` channel row and cascades its `FollowedChannel` rows, then renames `Product Updates`. Irreversible — the cascaded rows cannot be reconstructed. More house `Follow` rows end up with zero `FollowedChannel` rows, a state already tolerated and documented in `follows/0004_sweep_both_off_rows.py`.

**Frontend.** None. `platform_updates` does not appear in `backend-openapi.json` (`BroadcastEmail` is admin-only), so no type regeneration. Nothing in `src/web-ui/` resolves a channel by name.

**Tests.** `tests/factories.py:166` (`make_broadcast_follower`) indexes the channel mapping and raises `KeyError` on `"platform_updates"`; its callers in `tests/test_broadcast_emails.py`, `tests/test_inactive_user_emails.py` and `services/users/django_impl/test_query.py` need rewriting. Also touched: `apps/follows/tests/test_anoint_house_project.py`, `apps/follows/tests/test_auto_follow_signal.py`, `services/follows/django_impl/test_integration.py`, `services/notifications/django_impl/test_article_fanout.py`.

**Pre-flight.** Count articles per house channel on production before running the migration. If `Updates` has never carried content, the unsubscribe event affects nobody in practice.
