## Context

This implements Phase 2 of the design at `docs/superpowers/specs/2026-05-13-articles-following-news-design.md`. Phase 1 (`add-project-following`) stood up the data model and seeded preferences for existing users from the legacy `email_opt_in_*` flags. Phase 2 makes those preferences visible and editable.

Three constraints from the design shape this change:

1. The legacy email broadcast pipeline still reads `email_opt_in_*` until Phase 3 flips the send path. Any user-driven write to a Naglasúpan email switch MUST mirror back to the legacy flag, otherwise the UI lies (toggle off the switch, still get emails).
2. The popover and the global page are both required surfaces, not alternatives.
3. The visual design is implementation-driven — the design doc does not prescribe styling.

## Goals / Non-Goals

**Goals:**

- Expose the per-channel × per-medium switches in two places: a popover on the Follow button, and a global "Followed projects" page.
- Provide endpoints to read and write preferences.
- Keep the legacy email pipeline correct (mirror writes for Naglasúpan's named channels).

**Non-Goals:**

- Flipping the email send path (Phase 3).
- Removing legacy `email_opt_in_*` fields (Phase 3).
- Per-channel cadence (`notification_frequency` stays user-global).
- Notification firing (Phase 3 — no Articles yet).
- Project-owner channel management (Phase 3).
- Following users.

## Decisions

### 1. Three endpoints, scoped narrowly

- `GET /api/follows` — for the global page. Returns all of the user's follows + nested channel/preference data in one round trip.
- `GET /api/projects/{slug}/follow/preferences` — for the popover. Returns just one project's worth of data. Returns 404 if the user is not following — the popover should not open unless the user is in a follow state, so this is a misuse signal.
- `PATCH /api/projects/{slug}/follow/channels/{channel_id}` — for both surfaces. Patches a single preference row.

A potential alternative was a single `PATCH /api/follows/{follow_id}` that takes a nested array of channel updates. We avoided it because: (a) the per-toggle optimistic update on the frontend wants per-toggle responses; (b) one toggle failing in the middle of a multi-toggle batch is harder to recover from; (c) channel-id uniquely identifies the target without needing the Follow id.

### 2. Mirror writes only for Naglasúpan's two named channels

A patch to `email_enabled` on the Naglasúpan "Competition Winners" channel SHALL also set `user.email_opt_in_competition_results` to the same value. Same for "Product Updates" → `email_opt_in_platform_updates`.

Mirror writes are scoped to the house project (looked up by `is_house_project = True`) and to the two specific channel names. The "Updates" channel has no legacy correlate. Other projects' channels have no legacy correlate either.

The mirror logic lives in a single helper (`mirror_legacy_email_flag(user, channel, email_enabled)`) called from the PATCH handler. The helper is the only place that writes the legacy flags.

When Phase 3 ships (legacy flags removed, send path flipped), the mirror helper becomes a no-op and can be deleted as part of that change. Until then, the mirror keeps the two systems in agreement.

```
   User toggles "Competition Winners email" OFF in popover
                            │
                            ▼
        PATCH /api/projects/naglasupan/follow/channels/{id}
                            │
                ┌───────────┴───────────┐
                ▼                       ▼
   FollowChannelPreference         User.email_opt_in_
   email_enabled = False           competition_results = False
                                            │
                                            ▼
                            Legacy email pipeline sees the change
                            and stops sending competition emails.
```

### 3. Popover replaces Phase 1's instant-unfollow

Phase 1: click "Following" → instantly unfollows.
Phase 2: click "Following" → opens the popover.

This is a behaviour change for users who got used to Phase 1's instant-unfollow. The "Unfollow" link inside the popover (bottom) is the new path. Confirmation is not added — one extra click is the friction; an explicit "Unfollow" link is the intent signal.

### 4. The "Followed projects" page is collapsible

The design says "channel preferences inline (collapsed by default; click to expand)". Implementation: a `<details>` element or a controlled accordion component. Each row shows the project's icon + title + a count chip ("3 channels"). Expanding reveals the per-channel toggles.

This shape will work even for users following many projects without overwhelming the page on first paint.

### 5. Optimistic UI on toggles

A toggle click flips the visual state immediately; the PATCH fires in the background; on error, the toggle reverts and a toast surfaces the failure. Same pattern in the popover and the global page.

This matches how the rest of the platform handles toggles (review existing patterns; reuse if there's a hook).

### 6. Unfollow from the global page

The per-project row in `/profile/followed-projects` has an "Unfollow" affordance. Clicking it calls `DELETE /api/projects/{slug}/follow` and removes the row from the list optimistically.

The Naglasúpan project is an edge case: a user can unfollow Naglasúpan from this page, which then stops their emails entirely (because the mirror write doesn't fire on DELETE — the Follow row is just gone). The legacy flags are NOT reset to False on unfollow. This is fine because:

- The Follow row's absence means re-follow will start fresh (defaults-on), which writes new prefs that re-mirror.
- The legacy email pipeline reads `email_opt_in_*` AND checks that the user is active — but it doesn't check Follow existence. So a user who unfollows Naglasúpan in Phase 2 but whose legacy flags are still True would *still get the legacy emails until Phase 3*.

This is a documented gap, only relevant during the Phase 2 → Phase 3 window:

- If the user unfollows Naglasúpan via the global page, we mirror the legacy flags to False on unfollow as well, to honour intent.

So the mirror is bidirectional in scope: not only PATCH-driven writes, but also DELETE-driven Follow removal SHALL set the two `email_opt_in_*` flags to False on the user (when it's the Naglasúpan unfollow).

Conversely, follow-creation (POST) writes the per-channel prefs all-on but does NOT touch `email_opt_in_*` — because the legacy flags retain their existing user-chosen value. Only PATCH and the unfollow-of-Naglasúpan case mirror.

### 7. No "Unfollow Naglasúpan?" confirmation

The design doesn't add a confirmation modal. The Follow popover and the global page both let users unfollow Naglasúpan with one click. This is intentional: making it harder to unfollow is dark-pattern territory.

If we later find a regression — say, a flood of unintended unfollows — we add a confirmation then.

## Risks / Trade-offs

### Risk: drift between per-channel prefs and legacy flags

If the mirror logic has a bug, the popover toggle could say "off" while the legacy pipeline still sees "on". We mitigate with tests that cover every mirror path:

- PATCH email_enabled=False on Competition Winners → legacy flag is False.
- PATCH email_enabled=True on Product Updates → legacy flag is True.
- PATCH email_enabled on a non-Naglasúpan channel → no legacy flag changed.
- PATCH email_enabled on the Naglasúpan "Updates" channel → no legacy flag changed.
- DELETE the Naglasúpan follow → both legacy flags set to False.

### Risk: the global-page query is expensive

`GET /api/follows` joins Follow → FollowChannelPreference → Channel → Project. For users following many projects (none today, but plausible later), the row count grows. We use `select_related`/`prefetch_related` aggressively and accept that a user with 100+ follows will pay a moderate query cost. No pagination in v1 — return everything.

### Risk: the "Unfollow Naglasúpan" path silently strips legacy emails

Decision 6 explicitly handles this. Tests cover it.

### Trade-off: popover styling

The design says "subtle but visible" for the button and defers the popover visuals. We pick a styling consistent with existing top-bar elements at implementation time. If a design pass is owed, capture it as a follow-up — not a blocker.

## Migration Plan

No data migration. No schema change. Pure code change.

Deploy order: this change ships **after** `add-project-following` (Phase 1) is merged. Phase 1's Follow + FollowChannelPreference rows are required for the Phase 2 endpoints to return anything.

Deploy is single-step. Rollback is straightforward (revert).

## Open implementation choices

- Exact route path for the global page: `/profile/followed-projects` is the default. If the existing user-settings routes use a different convention, match that.
- Whether the popover anchors to the right or the bottom of the Follow button: design pass at implementation time.
- Whether to show the channel description (none today) or just the name in the popover: name-only for v1.
