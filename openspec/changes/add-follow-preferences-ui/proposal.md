## Why

Phase 1 (`add-project-following`) stood up the `Follow` + `Channel` + `FollowChannelPreference` data model and populated it for every user, but left the per-channel × per-medium switches invisible: the Follow button is a binary toggle, with no way to see or edit the email/in-app preferences inside.

Phase 2 (this change) adds the UI to view and manage those preferences. Two surfaces, both required by the design:

- **On each project page**, the "Following" button opens a popover that lists the project's channels with `email` and `in-app` toggles per channel. An "Unfollow" link sits at the bottom. (This replaces Phase 1's instant-unfollow-on-click.)
- **In user settings**, a new "Followed projects" page lists every project the user follows, with the same per-channel × per-medium toggles inline (collapsed by default; click to expand).

The change is pure UI/API. No data migration (Phase 1 already seeded the rows). No notification firing (Phase 3 does that). The legacy email broadcast pipeline still reads the `email_opt_in_*` flags — but to avoid a perceived bug where a user toggles the new "Competition Winners email" switch and still receives emails, the Naglasúpan-channel switches MUST mirror writes back to the corresponding legacy flag while Phase 3 has not yet shipped.

## What Changes

### Backend

- **Add** `GET /api/follows` — authentication required. Returns the requesting user's full follow set: each Follow with its Project (slug, title, hero image, etc.) and a list of channels with the current `email_enabled` / `in_app_enabled` values for each. Used by the global "Followed projects" page.
- **Add** `GET /api/projects/{slug}/follow/preferences` — authentication required. Returns the channels and current preference values for the requesting user's follow of this project. Used by the popover. Returns 404 if the user is not following.
- **Add** `PATCH /api/projects/{slug}/follow/channels/{channel_id}` — authentication required. Updates `email_enabled` and/or `in_app_enabled` on a single `FollowChannelPreference` row. Body: `{"email_enabled": bool?, "in_app_enabled": bool?}` (both optional). Returns the updated row.
- **Add** mirror-write logic for the house project's two named channels: when `PATCH` modifies `email_enabled` on the Naglasúpan "Competition Winners" channel preference, the user's `email_opt_in_competition_results` SHALL be set to the same value. Same for "Product Updates" → `email_opt_in_platform_updates`. The mirror SHALL only fire for the house project and only for those two channel names; "Updates" has no legacy correlate.
- **Modify** existing email-preference writes (none currently exist in user-facing API, but any future / admin write paths to `email_opt_in_*` SHOULD mirror in the *other* direction to keep state consistent — captured as a constraint, not a code change in this phase).

### Frontend

- **Add** a `FollowPopover` component (`src/web-ui/src/components/FollowPopover.tsx`). Anchored to the Follow button on the project page. When opened, fetches `/api/projects/{slug}/follow/preferences` and renders:
  - The list of channels with two toggles each (email, in-app).
  - An "Unfollow" link at the bottom.
- **Modify** `FollowButton.tsx`: when the user is currently following, click opens the popover instead of instant-unfollowing. The "Follow" action (initial click when not following) still instantly creates the follow.
- **Add** a "Followed projects" page at `/profile/followed-projects` (or wherever fits the existing user-settings nav).
  - Lists every Project the user follows.
  - Each project shows its hero/icon + title, collapsed by default. Click expands to reveal channel × medium toggles inline.
  - Toggles call `PATCH /api/projects/{slug}/follow/channels/{channel_id}` with optimistic update.
  - An "Unfollow" link at the per-project row level removes the follow (and removes the project from the list immediately).
- **Modify** existing user-settings navigation: add a "Followed projects" link to the settings sidebar.

### Out of scope

- Per-channel cadence (digest vs immediate per channel) — `notification_frequency` remains user-global.
- Following users (only projects in v1).
- Removal of the legacy `email_opt_in_*` fields (Phase 3 removes them).
- Flipping the outbound email send path to read from per-channel preferences (Phase 3).
- Any notification firing (Phase 3).
- Channel management UI for project owners (Phase 3).
- Followers count, follower list, social affordances.

## Capabilities

### Modified Capabilities

- `project-following`: adds requirements for the preference-read and preference-write endpoints, the popover and global-page UX, and the mirror-write semantics to legacy flags while Phase 3 has not yet shipped.

## Impact

- **Django backend**: three new endpoints + the mirror-write helper. No new models. No migrations.
- **OpenAPI / generated types**: regenerated.
- **Web UI**: new `FollowPopover`, new `/profile/followed-projects` page (and supporting list/expand components), modification of `FollowButton` to launch the popover on subsequent clicks.
- **Tests**: endpoint behaviour (mirror writes for the house project's two channels; no mirror for "Updates" or for other projects' channels); popover interaction (expand, toggle, unfollow); followed-projects page (list, expand, toggle, unfollow); Playwright golden path for both surfaces.
- **Unchanged**: the email broadcast pipeline (`async-broadcast-send`) still reads `email_opt_in_*`. No change to notifications. No change to the data model from Phase 1.
- **Out of scope**: anything in Phases 3-6 of the design doc.

## Dependencies

This change strictly depends on `add-project-following` (Phase 1) being merged first. Phase 2's endpoints assume the `Follow` / `Channel` / `FollowChannelPreference` rows exist for every user; Phase 1's data migration creates them.
