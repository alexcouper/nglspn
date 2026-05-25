## MODIFIED Requirements

### Requirement: User can follow and unfollow a Project

The platform SHALL expose two endpoints (originally introduced in `add-project-following`):

- `POST /api/projects/{slug}/follow` — authentication required. Creates a `Follow` row for the requesting user against the project identified by `slug`, with `FollowChannelPreference` rows for every Channel of that project. All `email_enabled` and `in_app_enabled` switches default to `True` on creation. The endpoint SHALL be idempotent: if a Follow already exists for `(user, project)`, no duplicate row is created and the endpoint returns the existing state.

- `DELETE /api/projects/{slug}/follow` — authentication required. Hard-deletes the Follow row for the requesting user against the project. `FollowChannelPreference` rows cascade-delete. The endpoint SHALL be idempotent: deleting a non-existent Follow returns 204.

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

#### Scenario: Unfollow hard-deletes

- **GIVEN** an authenticated user who follows project P, with a custom preference (e.g., `email_enabled = False` on one channel)
- **WHEN** they DELETE `/api/projects/{P.slug}/follow`
- **THEN** the response is 204
- **AND** no Follow row exists for `(user, P)`
- **AND** no `FollowChannelPreference` rows referencing that Follow remain

#### Scenario: Unfollow on the house project just deletes

- **GIVEN** an authenticated user U following the house project H
- **WHEN** U DELETEs `/api/projects/{H.slug}/follow`
- **THEN** the response is 204
- **AND** no Follow row exists for `(U, H)`
- **AND** no side-effects fire on the User row itself (the legacy `email_opt_in_*` fields no longer exist)

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

### Requirement: Endpoint to update a single channel preference

The platform SHALL expose `PATCH /api/projects/{slug}/follow/channels/{channel_id}`, authentication required. The endpoint SHALL update the requesting user's `FollowChannelPreference` row for the specified project + channel.

The request body SHALL accept `email_enabled` and/or `in_app_enabled` (both optional, but at least one MUST be provided). If neither field is provided, the endpoint SHALL return 400.

The endpoint SHALL return 404 if any of the following hold: the project doesn't exist; the channel doesn't belong to the project; the user is not following the project; the `FollowChannelPreference` row doesn't exist. The endpoint SHALL return 401 for unauthenticated requests.

The endpoint SHALL return 200 with the updated preference values on success.

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

## REMOVED Requirements

### Requirement: Mirror legacy email flag for the house project's named channels

**Reason**: The legacy `User.email_opt_in_competition_results` and `User.email_opt_in_platform_updates` fields are removed in this change. There is nothing left to mirror to. The Naglasúpan broadcast pipeline now reads Follow + ChannelPreference directly (see `async-broadcast-send` spec), making the mirror layer redundant.

**Migration**: No runtime migration required for the mirror behaviour itself — the mirror code is deleted alongside the columns it wrote to. The seed data that the mirror previously preserved is already canonical in `FollowChannelPreference` (Phase 1's data migration backfilled it).

### Requirement: Legacy email opt-in flags are untouched in Phase 1

**Reason**: This requirement asserted that Phase 1 did not modify the legacy fields. In this change (Phase 3) the legacy fields are dropped entirely, so the invariant is vacuously satisfied and the requirement no longer describes any system behaviour.

**Migration**: A migration in this change removes `email_opt_in_competition_results` and `email_opt_in_platform_updates` from the User model. See `async-broadcast-send` spec for how broadcast recipient resolution changes in lock-step with the column drop.

### Requirement: Data migration seeds existing-user preferences from legacy flags

**Reason**: The one-shot data migration ran in production as part of Phase 1's deploy. Its job — populating `FollowChannelPreference` rows from the legacy `email_opt_in_*` columns — is complete; the resulting preferences are now the canonical source of truth. Because this change drops the columns the migration referenced, leaving the requirement in the live spec would describe a migration that can no longer be re-derived from the current schema.

**Migration**: The historical migration file is preserved in `apps/users/migrations/` (or wherever it was committed) — Django will not re-run it. The output data — `FollowChannelPreference` rows — survives and is now the only source of per-user email preference for the Naglasúpan channels.
