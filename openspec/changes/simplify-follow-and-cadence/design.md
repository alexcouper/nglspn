## Context

`add-project-following` (Phase 1) and `add-follow-preferences-ui` (Phase 2) shipped a `Follow` row plus a `FollowChannelPreference` row per channel, each carrying two booleans (`email_enabled`, `in_app_enabled`). `add-article-authoring` (Phase 3) wired that model into the article publish path: fan-out reads the per-channel booleans and creates the in-app `Notification` row + queues / sends the email accordingly.

In practice the per-channel × per-medium granularity is unused. Two related deferrals from Phase 3 land here:

- **§5.4 / §5.5 mixed-digest work** — article rows were stitched into a separate per-article send because the existing digest template only knew about discussion rows. The "true per-recipient mixed digest" was parked.
- **`Channel.send_policy`** — sketched in `add-article-authoring/design.md:172` as the future home of the "Naglasúpan broadcasts go instant, articles respect cadence" carve-out. Never implemented.

This change collapses the model: existence of a `FollowedChannel` row means "user follows this channel", in-app fan-out always fires (no preference check), and email cadence is a per-user, per-kind setting. The "broadcasts go instant" carve-out is dropped — house-channel articles ride the user's article cadence like everything else, and we log enough at fan-out time to see if that hurts.

Stakeholders: every existing follower (no email-regression contract continues to apply), Naglasúpan admins (broadcasts no longer instant), project authors (no change to publish flow).

## Goals / Non-Goals

**Goals:**

- Single model for "is this user following this channel": existence of a row.
- Per-user email cadence per kind (discussion, article), independent.
- One discussion digest + one article digest per user per tick. Discussion `immediate` continues to send a single-thread email immediately on fan-out.
- House project's channels auto-followed for new users; existing users are swept based on prior preference state.
- Observable house-channel fan-out — we can answer "of N expected recipients, how many will see this within the hour?" from logs.

**Non-Goals:**

- Mixed (discussion + article) digest emails. Two separate emails.
- Per-channel cadence (each channel cannot have its own frequency).
- Per-project cadence (the project doesn't carry a cadence field).
- Re-introducing any "send this article immediately to followers" path. The only immediate path that remains is the per-thread discussion `immediate` email — for in-the-conversation feel.
- Backfilling pending email rows. Rows in flight at deploy time finish under the existing path.
- Removing or renaming the `notifications` capability's grouping / bell behaviour. The bell, popover, feed, toaster all continue to render notifications immediately regardless of email cadence.

## Decisions

### 1. Keep the table, drop the booleans, rename the model

`FollowChannelPreference` becomes `FollowedChannel` at the Django model layer. The Django migration uses `RenameModel` followed by `RemoveField` for the two booleans. The underlying `db_table` stays as `"follow_channel_preferences"` (pinned via `Meta.db_table`) so the data migration is a pure column drop — no row copies, no FK rewrites.

Why preserve the table name: the table holds the row identity (`(follow, channel)` unique-together is the meaning of "followed"), and all existing rows already represent the right relationships post-migration. Renaming the table buys nothing and risks references in raw SQL elsewhere. The model name change is a code-clarity win that the migration can express through Django state ops.

**Alternative considered:** drop `FollowChannelPreference` entirely and add `Follow.channels = ManyToManyField(Channel)`. Cleaner conceptually, but requires migrating every row to the implicit M2M table Django creates, and breaks any code that imports `FollowChannelPreference` directly. The rename + column-drop approach is strictly less invasive.

### 2. Two cadence fields, not one shared field

`User.discussion_email_frequency` and `User.article_email_frequency` are independent enums with overlapping but non-identical choice sets:

| Field | Choices | Default | Rationale |
|---|---|---|---|
| `discussion_email_frequency` | `immediate \| hourly \| daily \| never` | `hourly` | Conversations need an `immediate` option — an hour-long lag on a reply derails the thread. |
| `article_email_frequency` | `hourly \| daily \| weekly \| never` | `hourly` | Articles aren't time-critical at minute granularity; `weekly` is a reasonable "low-effort follower" cadence; `immediate` would defeat the digest. |

These are two separate `TextChoices` enum classes (`DiscussionEmailFrequency`, `ArticleEmailFrequency`) so each field's admin dropdown shows the right options and the model layer enforces the valid set. Sharing a single enum and policing valid values per field is more code and trades clarity for the wrong kind of brevity.

**Naming:** the `_email_` infix is load-bearing. It signals "this only governs email" so future readers don't assume it also gates in-app fan-out. The existing `notification_frequency` name was ambiguous on that point.

### 3. In-app fan-out always fires

The article publish path and the discussion fan-out path both create the `Notification` row unconditionally for every recipient (modulo author-exclusion, which stays). No preference check. The cadence fields only gate the email send.

This means: if a user follows a channel, articles + replies always appear in their bell. They can't have "follow but no in-app." That removes the "silenced follow" four-way state. The follow either exists (in-app on) or it doesn't (in-app off).

### 4. Two digest workers, not one

A per-user dispatch task is responsible for both digests; the rendering logic and templates are separate (`discussion_digest.{html,txt}` and `article_digest.{html,txt}`). The dispatch task runs on the hourly schedule (the smallest tick anyone selects). For each (user, kind) it checks whether the user's cadence bucket fires this tick:

- `immediate` (discussion only) — handled separately, at fan-out time, per Decision 5.
- `hourly` — fires every hourly tick.
- `daily` — fires on the daily tick (e.g. 09:00 UTC; the exact wall clock is fine to pick once and stick to).
- `weekly` (article only) — fires on the weekly tick (e.g. Monday 09:00 UTC).
- `never` — never fires; rows accumulate forever but are never sent. (We could prune them with a cleanup task — see Open Questions.)

Each digest fetches all `Notification` rows for the user in the relevant kind that are unsent + unread (state-tracked on the row), renders them into a single email, and marks them sent. **A user can receive two emails on the same tick** (their hourly discussion + hourly article digests). That's accepted; coalescing is a Future-Us problem.

**Alternative considered:** unify into a single digest email. Rejected — the user explicitly wants the two kinds delivered separately, and one-template-handles-both adds template complexity for unclear value.

### 5. Discussion `immediate` keeps its current direct-send path

`services/notifications/django_impl/handler.py` already calls `_send_immediate` for the discussion path when `notification.email_cadence == IMMEDIATE`. That branch survives unchanged — just gated on the renamed field. No discussion digest worker handles `immediate` rows; they're sent at fan-out time and never enter the digest queue.

Article fan-out drops `_send_immediate` entirely — there is no `IMMEDIATE` value in `ArticleEmailFrequency`.

### 6. Existing-user sweep is "email was off → drop the row"

The Phase-1 → Phase-2 mirror left every existing user with `FollowChannelPreference` rows on the house project. The migration keys on `email_enabled` alone:

- `True` → row stays (becomes a `FollowedChannel` row with no booleans after the column drop).
- `False` → row deleted before the column drop runs.

`in_app_enabled` is deliberately not consulted. Once the booleans are gone the row *is* the subscription — following a channel means its articles reach you at your `article_email_frequency` — so `email_enabled` is the only pre-change signal the new model can still carry.

An earlier draft of this decision used `email_enabled OR in_app_enabled`. That rule is wrong for the cohort it was written for: `0002_seed_channels_and_house_follows` writes `in_app_enabled=True` on every row it seeds, unconditionally. Those rows came from two checkboxes (`email_opt_in_competition_results`, `email_opt_in_platform_updates`) that predate the in-app bell, so their `in_app_enabled` is a migration default, not a user choice. OR-ing against a constant `True` matches every legacy row regardless of the opt-out — the sweep would delete none of them, and everyone who had unticked those boxes would be resubscribed to exactly those broadcasts.

What the narrower rule costs: a user who wanted in-app but not email on a channel is unfollowed rather than kept. That state is not expressible after the column drop either way, and a quiet inbox is the safer side to land on.

Users with no `Follow(user, house_project)` row stay unfollowed. That's an explicit choice — if they didn't follow the house project pre-change, they don't get auto-subscribed by the migration. This is the "respect the user's choice" interpretation we agreed to.

A `Follow` row whose `FollowedChannel` set becomes empty after the sweep is **left in place**. It's a "you follow this project but currently follow none of its channels" state — the popover still works, and the user can re-enable channels. Deleting the empty `Follow` would silently change the "I am a follower" semantic; better to leave it.

### 7. Auto-follow on Follow creation

When a user creates a `Follow(user, project)` row, the same handler creates a `FollowedChannel(follow, channel)` row for every channel currently on the project. The follow popover deletes individual rows when the user unticks a channel; if they delete all rows, the `Follow` itself stays (same reasoning as Decision 6).

**Edge case:** a channel is added to the project after the user follows. The user does *not* automatically get a `FollowedChannel` row for the new channel. They keep the channels they had at follow-time. (Otherwise the project owner can unilaterally add a channel and silently push notifications into a follower's bell.)

This is a deliberate semantics call: project owners can add channels, but each existing follower decides whether to enrol — exposed in the popover, where the new channel renders as "not followed" and the follower can tick it.

### 8. Broadcast-send path: digest, not instant

`async-broadcast-send` resolves recipients with the same query as article fan-out: every user with a `FollowedChannel(user, c)` row where `c` is the broadcast's target channel AND `article_email_frequency != never`. The email row is enqueued in the user's article-digest bucket, not sent immediately.

Naglasúpan ranking-day implication: a user on `weekly` won't see the ranking article in their inbox until Monday morning. Acceptable per discussion. The risk is logged (Decision 9) so we can quantify it before deciding whether to revisit.

**Alternative considered:** keep one immediate path for the house broadcasts via a `Channel.send_policy = immediate` flag. Rejected — adds a special case to keep an old behaviour, and we're explicitly choosing to test whether the digest model is good enough.

### 9. House-channel fan-out observability

A single `logger.info` line at the point of `Notification` row creation for an article on a house-project channel:

```
event=house_channel_article_enqueued
article_id=<uuid>
user_id=<uuid>
channel_id=<uuid>
recipient_frequency=<hourly|daily|weekly|never>
article_published_at=<iso>
```

`never` is logged too — those are silent misses, the most important number for a retro. Hourly / daily / weekly are recorded so we can compute the within-T window for any T.

The log goes through Django's default logging — no new dependency. Post-incident the answer to "how many ranking-day recipients hadn't seen it within the hour?" is a single `grep | awk` over the log archive. If this signal becomes important enough to live in a dashboard, we can promote it to a structured metric later.

## Risks / Trade-offs

- **Ranking-day silence** → Users on `weekly` or `never` won't get house-channel articles in time. Mitigated by the fan-out log, which makes the impact measurable. If the impact is bad in practice, revisit by either changing the `article_email_frequency` default for house-project followers (project-specific opt-in to hourly) or re-introducing a per-channel cadence override.
- **Empty-Follow rows after the sweep** → Users with all-`False` channels in Phase 2 get a `Follow` row with no `FollowedChannel` children. They appear as followers in counts but receive nothing. This is a knowable inconsistency, not a bug — the popover lets them re-enrol. Document it in the migration runbook.
- **Two emails on the same tick** → A user on hourly-for-both with new content in both kinds gets two emails the same hour. Acceptable; revisit only if support complaints justify the coalescing engineering.
- **Channel-add-after-follow semantics** → A new channel doesn't auto-enrol existing followers. If a project later renames a default channel (say splits "Updates" into "Updates" + "Releases") existing followers miss the new one until they revisit the popover. Mitigation: don't reorganise channels on populated projects without a plan to surface the change in-app.
- **Discussion `immediate` is now the only synchronous email path in the system** → Every other email goes through the digest path. If we ever want to drop `immediate` (to deduplicate the send code), it'd be a separate small change. For now `_send_immediate` stays — it works and the user wants the option.
- **Migration ordering** → Field rename on `User` must happen before the `services/notifications/django_impl/handler.py` flip. If they ship out of order the handler reads a removed column. Pin both in the same release, sequenced inside one migration plan (see Migration Plan).
- **Web-ui type churn** → Removing `email_enabled` / `in_app_enabled` from `FollowChannelPreference` schemas and removing `notification_frequency` from `UserUpdate` will surface every consumer that touched those fields. That's a finite, code-search-able set; do it in the same web-ui PR that ships the cadence dropdowns.

## Migration Plan

Single deploy. Migrations are sequenced so the live system is consistent at every intermediate state.

1. **Backend code lands first (same release):**
   1. Add the two new `User` cadence fields and the choice classes; **don't** remove `notification_frequency` yet.
   2. Add `FollowedChannel` as an alias / read path that reads from `FollowChannelPreference` ignoring the booleans. Phase-3 fan-out path also continues to read the booleans during the transition window.
   3. (Optional safety belt — only if we want one) Mirror writes from `notification_frequency` ↔ `discussion_email_frequency` for one release. Probably not needed since they're synonyms with the same shape.
2. **Migration 1 — add columns + sweep:**
   - Add `discussion_email_frequency` (default = current `notification_frequency` value for that row), add `article_email_frequency` (default `hourly`).
   - Sweep `FollowChannelPreference`: delete rows with both booleans `False`.
   - For every user *without* a `FollowedChannel` on each house-project channel, add it.
3. **Code flip:** the fan-out path reads the new fields; the broadcast path reads the FollowedChannel existence; the digest workers ship. The follow popover ships with the simplified UI.
4. **Migration 2 — drop columns:**
   - Drop `email_enabled` and `in_app_enabled` from `follow_channel_preferences`.
   - Drop `notification_frequency` from users.

Steps 2 and 4 are separate Django migrations in the same release. Step 3 is the code release.

**Rollback:** between step 2 and step 4, the schema is a superset and the old code still works. After step 4, rollback requires a forward-fix (re-add columns, re-derive booleans from `FollowedChannel` existence — would be all-`True`). The window where steps 2 and 4 are split gives us a checkpoint.

## Open Questions

1. **`never` row growth** — In-app `Notification` rows for users on `never` accumulate forever. Do we add a cleanup task that hard-deletes them after N days? Not in scope for this change, but worth opening as a follow-up if the table grows. Numbers will tell.
2. **Default for new-user `discussion_email_frequency` on signup** — settling on `hourly` (matches today's default for `notification_frequency`). The signup flow doesn't ask; we set the default and surface the setting in the settings page. Confirmed.
3. **Per-project cadence override** — Out of scope. If house-channel silence becomes a problem (Risk 1), the cleanest fix is per-project cadence, not re-introducing per-channel `send_policy`. Don't design for it yet.
4. **Wall-clock for daily / weekly ticks** — Pick at implementation time. Probably 09:00 UTC for daily and Monday 09:00 UTC for weekly, but the celery schedule lives in settings; one-line change later if we want to move it.

5. **Broadcast send integration shape (§8.2 deferred)** — Spec §8.2 says the broadcast task SHOULD stop sending synchronously and instead enqueue per-recipient rows that the article-digest workers deliver on each user's cadence. The implementation in this change updates the recipient resolver (§8.1) but leaves `send_broadcast` doing direct per-recipient mail. The reason it's deferred: `Notification` has only `article` and `discussion` FKs, so routing broadcasts through the digest path requires picking one of:
   - **(a) Model broadcasts as articles.** When admin sends a `BroadcastEmail`, create a hidden/system `Article` on the relevant house channel, then call `create_notifications_for_article` and let the existing digest path fan out. Pros: zero new plumbing; broadcasts become first-class content. Cons: needs an article body/title shape that matches the broadcast (or a transform), and a way to keep these articles out of project listings / global feeds if that's undesirable.
   - **(b) Add a `broadcast` FK to `Notification`.** Extend the XOR check to three FKs (`discussion XOR article XOR broadcast`), teach the digest workers to render a broadcast-shaped row. Pros: keeps broadcasts cleanly separate from articles. Cons: every notification-touching surface (bell, grouping, templates, in-app UI) needs to learn the third kind.
   
   Both are larger than this change wanted to absorb. **In the meantime** the synchronous send path still works correctly because:
   - The resolver excludes `article_email_frequency = never` (so the global opt-out is honoured).
   - The resolver requires the matching `FollowedChannel` row (so users who unfollowed the broadcast channel are excluded).
   
   What we LOSE relative to the digest path: a user on `weekly` who got an in-flight broadcast still receives it immediately rather than waiting for their Monday tick. For the current broadcast volume (Naglasúpan ranking days, occasional product updates) this is arguably correct anyway. Revisit when we have enough broadcasts that the digest semantics matters.
