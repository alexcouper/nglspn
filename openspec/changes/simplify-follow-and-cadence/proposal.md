## Why

Phase 3 (`add-article-authoring`) shipped the article publish path with the per-channel × per-medium preference model carried forward from Phase 1. In use, the model is more knobs than the actual problem warrants:

- Two switches per channel per follow (email + in-app) means a follow can be partially silenced four different ways.
- Article notifications currently send one email per article (the deferred §5.4/§5.5 mixed-digest work never landed).
- The house project's "Competition Winners" / "Product Updates" channels still need a dedicated immediate-send path to keep ranking-day broadcasts instant, which means a future `Channel.send_policy` carve-out was already on the books.

This change collapses the model to: **follow a channel or don't**. In-app is implicit when you follow. Email cadence is a single per-user, per-kind setting — independent for discussions and articles. Article emails become a per-user digest. Discussions keep their existing cadence shape (including `immediate`, because conversations don't tolerate hour-long lags) but only the email field name changes to make the intent honest.

The "broadcasts must go instant" carve-out is dropped. Ranking-day announcements ride the user's chosen article cadence like everything else. We accept the risk that some users won't see the result for up to a week and log enough at fan-out time to measure if it's actually a problem.

## What Changes

- Drop `FollowChannelPreference.email_enabled` and `FollowChannelPreference.in_app_enabled`. The row's *existence* now means "user follows this channel". Rename the model to `FollowedChannel` while preserving the underlying `follow_channel_preferences` table via `db_table`.
- Auto-create a `FollowedChannel` row for every channel of the followed project when a user follows that project. The follow popover continues to allow per-channel unfollow (delete the `FollowedChannel` row); fully unfollowing the project deletes every row.
- Add `User.article_email_frequency` enum (`hourly | daily | weekly | never`, default `hourly`).
- Rename `User.notification_frequency` → `User.discussion_email_frequency`. Choices unchanged (`immediate | hourly | daily | never`, default `hourly`). The field still governs only email; in-app discussion notifications continue to fire immediately.
- **Article fan-out becomes digest-only.** Drop the immediate-email branch from the article publish path. Every recipient with `article_email_frequency != never` gets a row queued for the next bucket tick on their cadence. **No** `Channel.send_policy` field is introduced.
- Add two digest workers / templates — one for discussions, one for articles — each rendered per-user on the user's chosen tick. They are independent emails; no attempt to coalesce when ticks coincide.
- **Auto-follow the house project's channels at user-create.** Apply the same rule to existing users via a one-shot migration: any user with a Phase-2 `FollowChannelPreference` row where *either* switch was on gets a `FollowedChannel` row; both-off becomes a delete. Users with no `Follow` row on the house project stay unfollowed (their explicit choice is respected).
- The Phase-3 article fan-out path that calls `_send_immediate` for the article publish drops. The discussion path's immediate branch stays (gated on `discussion_email_frequency == "immediate"`).
- Update `async-broadcast-send` recipient resolution: a broadcast for the "Competition Winners" channel now selects every user with a `FollowedChannel(user, c)` row AND `article_email_frequency != never`. The email is queued for that user's next bucket, not sent immediately — consistent with all other article fan-out.
- Add structured `logger.info` line at article fan-out time when the article is on a house-project channel, recording `article_id`, `user_id`, `channel_id`, `recipient_frequency`, `published_at`. Lets us answer "how many users were on weekly when we shipped a ranking-day article?" after the fact.
- Update follow popover UI: drop per-medium toggles. Each channel row becomes a single checkbox ("Follow this channel") backed by `FollowedChannel` existence. Unfollow-project button stays.
- Update `/profile/following` (or wherever the global list lives) to remove per-channel email / in-app toggles.
- Add settings UI rows: "Discussion email frequency" + "Article email frequency" dropdowns.
- **BREAKING:** API `PATCH /api/projects/{slug}/follow/preferences/{channel_id}` no longer accepts `email_enabled` / `in_app_enabled`. Replaced by `POST /api/projects/{slug}/follow/channels/{channel_id}` (follow channel) and `DELETE` (unfollow channel).
- **BREAKING:** `User.notification_frequency` is removed from `UserUpdate` / `UserResponse` and replaced by the two new fields. The OpenAPI schema regenerates and the web-ui types are regenerated to match.

## Capabilities

### New Capabilities

(none — every change layers onto an existing capability)

### Modified Capabilities

- `project-following`: collapses `FollowChannelPreference` (two booleans) to `FollowedChannel` (existence). Replaces the per-medium preference API with follow / unfollow channel routes. Adds auto-follow-on-Follow.
- `notifications`: drops the per-channel email/in-app gating in fan-out; introduces per-user, per-kind email cadence with independent digest workers; removes article-immediate path entirely; introduces house-channel fan-out logging.
- `in-app-notifications-ui`: removes mentions of per-medium toggles in the UI surface (settings page replaces them with the two cadence rows).
- `async-broadcast-send`: recipient resolution swaps from `FollowChannelPreference.email_enabled` to `FollowedChannel` existence + `User.article_email_frequency != never`; broadcasts now go through the per-user digest tick rather than immediate send.

## Impact

- **Code:**
  - `apps/follows/models.py` — rename `FollowChannelPreference` → `FollowedChannel`, drop booleans, set `db_table = "follow_channel_preferences"` to keep the existing table.
  - `apps/users/models.py` — rename `notification_frequency` → `discussion_email_frequency`, add `article_email_frequency`.
  - `services/follows/` — service-layer + tests follow the rename; follow-channel / unfollow-channel handlers added.
  - `services/notifications/django_impl/handler.py` — drop the article-immediate branch; both fan-out paths consult the new fields. Add the house-channel log line.
  - `services/email/` — two new digest tasks + templates (`discussion_digest`, `article_digest`); per-user dispatch.
  - `services/email/django_impl/query.py` — broadcast recipient query rewritten.
  - `api/routers/follows.py` (and schemas) — preference PATCH endpoint replaced.
  - `api/routers/users.py` — `UserUpdate` / `UserResponse` updated for the renamed + new cadence fields.
  - `api/routers/notifications.py` — no shape change (the bell + groups endpoint shape is unaffected; in-app fan-out path simplifies internally).
  - `web-ui` — settings page (cadence dropdowns), follow popover (single per-channel checkbox), `/profile/following` (preferences-section removal), removal of per-medium toggle types.
- **Migrations:**
  - `apps/follows` — drop `email_enabled` and `in_app_enabled` columns from `follow_channel_preferences` (drops the booleans; keeps the row identity intact).
  - `apps/users` — rename column `notification_frequency` → `discussion_email_frequency`, add `article_email_frequency`.
  - Data migration: for every existing User without a `FollowedChannel(user, house_channel)` row, add one for each house-project channel (so existing users are auto-subscribed to ranking + product update digests). Skip users with no `Follow` on the house project — that's an explicit prior opt-out.
  - Data migration: for every `FollowChannelPreference` row where both booleans were `False`, delete the row before the column-drop migration runs. (Booleans are read by the migration script, then dropped.)
- **APIs:** breaking changes to the follow-preferences and user-update endpoints; OpenAPI regenerated; web-ui types regenerated.
- **Existing callers:**
  - `add-article-authoring` §5.4 / §5.5 (mixed-digest deferrals) are superseded — the new article digest path delivers what they were going to.
  - `add-article-authoring`'s design note about a future `Channel.send_policy` field is dropped — no longer needed.
- **No backfill of pending email rows.** Any `Notification` rows currently sitting in the queue at deploy time were created under the old gating; they continue to flow through the existing immediate-send branch (discussions) or were already sent (articles). New rows after deploy use the new path.
