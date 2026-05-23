## ADDED Requirements

### Requirement: Endpoint to list the authenticated user's follows

The platform SHALL expose `GET /api/follows`, authentication required. The endpoint SHALL return the requesting user's full set of follows. Each follow SHALL include enough information to render a list item without further requests: the project's slug, title, and hero/icon image URL (nullable), the follow's `created_at`, and the list of channels with their per-channel preference values (`email_enabled`, `in_app_enabled`).

The endpoint SHALL return an empty list for an authenticated user with no follows. The endpoint SHALL return 401 for unauthenticated requests.

#### Scenario: User with multiple follows gets all of them

- **GIVEN** an authenticated user U following projects P1, P2, and P3
- **WHEN** U fetches `GET /api/follows`
- **THEN** the response is 200
- **AND** the response contains three entries, one per followed project
- **AND** each entry includes its project's slug, title, hero image URL, and a list of channels with `email_enabled` / `in_app_enabled` values

#### Scenario: User with no follows

- **GIVEN** an authenticated user U with no Follow rows
- **WHEN** U fetches `GET /api/follows`
- **THEN** the response is 200
- **AND** the response is an empty list

#### Scenario: Anonymous request

- **WHEN** an unauthenticated client fetches `GET /api/follows`
- **THEN** the response is 401

### Requirement: Endpoint to read a single project's follow preferences

The platform SHALL expose `GET /api/projects/{slug}/follow/preferences`, authentication required. The endpoint SHALL return the requesting user's per-channel preferences for the specified project's follow.

The response SHALL include the project's slug and title, and the list of channels with `email_enabled` and `in_app_enabled` values for each.

The endpoint SHALL return 404 if the requesting user is not following the project (i.e., no Follow row exists). The endpoint SHALL return 401 for unauthenticated requests.

#### Scenario: Followed project returns preferences

- **GIVEN** an authenticated user U following project P with three channels
- **WHEN** U fetches `GET /api/projects/{P.slug}/follow/preferences`
- **THEN** the response is 200
- **AND** the response contains three channel entries with current `email_enabled` and `in_app_enabled` values

#### Scenario: Not following returns 404

- **GIVEN** an authenticated user U not following project P
- **WHEN** U fetches `GET /api/projects/{P.slug}/follow/preferences`
- **THEN** the response is 404

#### Scenario: Anonymous request

- **WHEN** an unauthenticated client fetches `GET /api/projects/{P.slug}/follow/preferences`
- **THEN** the response is 401

### Requirement: Endpoint to update a single channel preference

The platform SHALL expose `PATCH /api/projects/{slug}/follow/channels/{channel_id}`, authentication required. The endpoint SHALL update the requesting user's `FollowChannelPreference` row for the specified project + channel.

The request body SHALL accept `email_enabled` and/or `in_app_enabled` (both optional, but at least one MUST be provided). If neither field is provided, the endpoint SHALL return 400.

The endpoint SHALL return 404 if any of the following hold: the project doesn't exist; the channel doesn't belong to the project; the user is not following the project; the `FollowChannelPreference` row doesn't exist. The endpoint SHALL return 401 for unauthenticated requests.

The endpoint SHALL return 200 with the updated preference values on success.

When the request modifies `email_enabled`, the endpoint SHALL invoke the mirror-write helper (see "Mirror legacy email flag" requirement below).

#### Scenario: Toggling email off succeeds

- **GIVEN** an authenticated user U following project P with channel C, where `email_enabled = True`
- **WHEN** U PATCHes `{"email_enabled": false}` to `/api/projects/{P.slug}/follow/channels/{C.id}`
- **THEN** the response is 200
- **AND** the `FollowChannelPreference` row has `email_enabled = False` after the request

#### Scenario: Empty body returns 400

- **WHEN** U PATCHes an empty body `{}` to a valid channel preference endpoint
- **THEN** the response is 400
- **AND** no rows are modified

#### Scenario: Channel does not belong to the project returns 404

- **GIVEN** a channel C' that belongs to project P' (not P)
- **WHEN** U PATCHes `/api/projects/{P.slug}/follow/channels/{C'.id}`
- **THEN** the response is 404

#### Scenario: Not following returns 404

- **GIVEN** U is not following project P
- **WHEN** U PATCHes `/api/projects/{P.slug}/follow/channels/{any_channel.id}`
- **THEN** the response is 404

### Requirement: Mirror legacy email flag for the house project's named channels

When a `PATCH` modifies `email_enabled` on a `FollowChannelPreference` whose channel is on the house project (`channel.project.is_house_project = True`) AND whose channel name is "Competition Winners" or "Product Updates", the platform SHALL set the corresponding legacy field on the user to the same value:

- "Competition Winners" → `user.email_opt_in_competition_results`
- "Product Updates" → `user.email_opt_in_platform_updates`

The mirror SHALL NOT fire for: the house project's "Updates" channel; any channel of any non-house project; PATCHes that only modify `in_app_enabled`.

The mirror SHALL save with `update_fields=[…]` to avoid touching other User columns.

#### Scenario: Mirror fires for Competition Winners email

- **GIVEN** an authenticated user U with `email_opt_in_competition_results = True`, following the house project H
- **WHEN** U PATCHes `{"email_enabled": false}` to the Competition Winners channel preference
- **THEN** `U.email_opt_in_competition_results` is `False` after the request

#### Scenario: Mirror fires for Product Updates email

- **GIVEN** an authenticated user U with `email_opt_in_platform_updates = True`, following the house project H
- **WHEN** U PATCHes `{"email_enabled": false}` to the Product Updates channel preference
- **THEN** `U.email_opt_in_platform_updates` is `False` after the request

#### Scenario: Mirror does not fire for house project's Updates channel

- **GIVEN** an authenticated user U with `email_opt_in_competition_results = True` and `email_opt_in_platform_updates = True`, following the house project H
- **WHEN** U PATCHes `{"email_enabled": false}` to the "Updates" channel preference on H
- **THEN** both `email_opt_in_*` flags on U remain `True`

#### Scenario: Mirror does not fire for non-house projects

- **GIVEN** an authenticated user U with `email_opt_in_competition_results = True`, following a non-house project P
- **WHEN** U PATCHes `{"email_enabled": false}` to any channel preference on P
- **THEN** `U.email_opt_in_competition_results` remains `True`

#### Scenario: PATCH that only changes in_app does not mirror

- **GIVEN** an authenticated user U with `email_opt_in_competition_results = True`, following the house project H
- **WHEN** U PATCHes `{"in_app_enabled": false}` to the Competition Winners channel preference
- **THEN** `U.email_opt_in_competition_results` remains `True`
- **AND** the `FollowChannelPreference.in_app_enabled` is `False`

## MODIFIED Requirements

### Requirement: User can follow and unfollow a Project

The platform SHALL expose two endpoints (originally introduced in `add-project-following`):

- `POST /api/projects/{slug}/follow` — authentication required. Creates a `Follow` row for the requesting user against the project identified by `slug`, with `FollowChannelPreference` rows for every Channel of that project. All `email_enabled` and `in_app_enabled` switches default to `True` on creation. The endpoint SHALL be idempotent: if a Follow already exists for `(user, project)`, no duplicate row is created and the endpoint returns the existing state. POST SHALL NOT modify the legacy `email_opt_in_*` fields (the user's existing flag values are preserved).

- `DELETE /api/projects/{slug}/follow` — authentication required. Hard-deletes the Follow row for the requesting user against the project. `FollowChannelPreference` rows cascade-delete. The endpoint SHALL be idempotent: deleting a non-existent Follow returns 204.

  **NEW in Phase 2:** when the deleted Follow is on the house project (the one with `is_house_project = True`), the DELETE handler SHALL also set `user.email_opt_in_competition_results = False` and `user.email_opt_in_platform_updates = False`. This ensures the legacy email broadcast pipeline (which still reads those flags through Phase 2) honours the user's intent to stop receiving Naglasúpan updates. The legacy flags are NOT modified on DELETE of any non-house-project follow.

Anonymous (unauthenticated) requests to either endpoint SHALL return 401.

#### Scenario: First follow creates the row

- **GIVEN** an authenticated user with no Follow row for project P
- **WHEN** they POST to `/api/projects/{P.slug}/follow`
- **THEN** the response is 200
- **AND** a Follow row exists for `(user, P)`
- **AND** for every Channel of P, a `FollowChannelPreference` row exists with `email_enabled = True` and `in_app_enabled = True`

#### Scenario: Second follow is a no-op

- **GIVEN** an authenticated user who already follows project P
- **WHEN** they POST to `/api/projects/{P.slug}/follow` again
- **THEN** the response is 200
- **AND** there is still exactly one Follow row for `(user, P)`
- **AND** existing `FollowChannelPreference` rows are unchanged

#### Scenario: POST does not modify legacy email flags

- **GIVEN** an authenticated user U with `email_opt_in_competition_results = False`, not following the house project H
- **WHEN** U POSTs to `/api/projects/{H.slug}/follow`
- **THEN** a Follow row is created
- **AND** the `FollowChannelPreference` for the Competition Winners channel has `email_enabled = True` (default, regardless of legacy flag — POST does not read legacy flags)
- **AND** `U.email_opt_in_competition_results` is unchanged (still `False`)

#### Scenario: Unfollow hard-deletes

- **GIVEN** an authenticated user who follows project P, with a custom preference (e.g., `email_enabled = False` on one channel)
- **WHEN** they DELETE `/api/projects/{P.slug}/follow`
- **THEN** the response is 204
- **AND** no Follow row exists for `(user, P)`
- **AND** no `FollowChannelPreference` rows referencing that Follow remain

#### Scenario: Unfollowing the house project mirrors to legacy flags

- **GIVEN** an authenticated user U with `email_opt_in_competition_results = True` and `email_opt_in_platform_updates = True`, following the house project H
- **WHEN** U DELETEs `/api/projects/{H.slug}/follow`
- **THEN** the response is 204
- **AND** `U.email_opt_in_competition_results = False`
- **AND** `U.email_opt_in_platform_updates = False`

#### Scenario: Unfollowing a non-house project does not mirror

- **GIVEN** an authenticated user U with `email_opt_in_competition_results = True`, following a non-house project P
- **WHEN** U DELETEs `/api/projects/{P.slug}/follow`
- **THEN** the response is 204
- **AND** `U.email_opt_in_competition_results` is unchanged (still `True`)

#### Scenario: Re-follow after unfollow is fresh

- **GIVEN** an authenticated user who previously unfollowed project P
- **WHEN** they POST to `/api/projects/{P.slug}/follow`
- **THEN** a new Follow row exists
- **AND** every per-channel preference is defaulted to `email_enabled = True`, `in_app_enabled = True`

#### Scenario: Unfollow when not following is a no-op

- **GIVEN** an authenticated user with no Follow row for project P
- **WHEN** they DELETE `/api/projects/{P.slug}/follow`
- **THEN** the response is 204

#### Scenario: Anonymous follow is rejected

- **WHEN** an unauthenticated request POSTs or DELETEs `/api/projects/{P.slug}/follow`
- **THEN** the response is 401
