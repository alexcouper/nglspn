## MODIFIED Requirements

### Requirement: User can follow and unfollow a Project

The platform SHALL expose two endpoints:

- `POST /api/projects/{slug}/follow` — authentication required. Creates a `Follow` row for the requesting user against the project identified by `slug`, and creates a `FollowedChannel` row for every `Channel` currently associated with that project. The endpoint SHALL be idempotent: if a `Follow` already exists for `(user, project)`, no duplicate row is created. If the `Follow` exists but the user is missing `FollowedChannel` rows for some channels (because channels were added since the user first followed), the existing rows SHALL be left in place — POST SHALL NOT auto-enrol the user in channels they were not subscribed to.

- `DELETE /api/projects/{slug}/follow` — authentication required. Hard-deletes the Follow row for the requesting user against the project. `FollowedChannel` rows cascade-delete. The endpoint SHALL be idempotent: deleting a non-existent Follow returns 204.

Anonymous (unauthenticated) requests to either endpoint SHALL return 401.

#### Scenario: First follow creates the Follow and one FollowedChannel per existing channel

- **GIVEN** an authenticated user with no Follow row for project P, where P has three channels
- **WHEN** they POST to `/api/projects/{P.slug}/follow`
- **THEN** the response is 200
- **AND** a `Follow` row exists for `(user, P)`
- **AND** three `FollowedChannel` rows exist, one per channel of P

#### Scenario: Second follow is a no-op

- **GIVEN** an authenticated user who already follows project P
- **WHEN** they POST to `/api/projects/{P.slug}/follow` again
- **THEN** the response is 200
- **AND** there is still exactly one `Follow` row for `(user, P)`
- **AND** the existing `FollowedChannel` rows are unchanged

#### Scenario: Re-POST after the project added a new channel does not enrol the user

- **GIVEN** an authenticated user follows project P (which then had two channels), and P later added a third channel C3
- **WHEN** the user POSTs to `/api/projects/{P.slug}/follow` again
- **THEN** the response is 200
- **AND** the user's `FollowedChannel` rows still cover only the original two channels (no row for C3 is created)

#### Scenario: Unfollow hard-deletes Follow and all FollowedChannels

- **GIVEN** an authenticated user who follows project P, with `FollowedChannel` rows for some of P's channels
- **WHEN** they DELETE `/api/projects/{P.slug}/follow`
- **THEN** the response is 204
- **AND** no `Follow` row exists for `(user, P)`
- **AND** no `FollowedChannel` rows referencing that `Follow` remain

#### Scenario: Unfollow on the house project just deletes

- **GIVEN** an authenticated user U following the house project H
- **WHEN** U DELETEs `/api/projects/{H.slug}/follow`
- **THEN** the response is 204
- **AND** no `Follow` row exists for `(U, H)`
- **AND** no side-effects fire on the User row itself

#### Scenario: Re-follow after unfollow re-enrols every current channel

- **GIVEN** an authenticated user who previously unfollowed project P, where P now has three channels
- **WHEN** they POST to `/api/projects/{P.slug}/follow`
- **THEN** a new `Follow` row exists
- **AND** three new `FollowedChannel` rows exist, one per current channel

#### Scenario: Unfollow when not following is a no-op

- **GIVEN** an authenticated user with no Follow row for project P
- **WHEN** they DELETE `/api/projects/{P.slug}/follow`
- **THEN** the response is 204

#### Scenario: Anonymous follow is rejected

- **WHEN** an unauthenticated request POSTs or DELETEs `/api/projects/{P.slug}/follow`
- **THEN** the response is 401

### Requirement: Auto-follow the house project on user creation

When a new `User` is created (`is_active = True`, `is_system_user = False`), the platform SHALL automatically create a `Follow` row for that user against the house project (the project with `is_house_project = True`), AND create a `FollowedChannel` row for every Channel of the house project.

This SHALL be implemented via a `post_save` signal on User scoped to `created = True`. The signal handler SHALL silently no-op (with a logged warning) if no house project exists in the database — this is the greenfield dev / test case.

System users (`is_system_user = True`) SHALL NOT be auto-followed.

#### Scenario: New regular user is auto-followed

- **GIVEN** the house project exists with three channels
- **WHEN** a new user with `is_system_user = False` is created
- **THEN** a `Follow` row exists for `(user, house_project)`
- **AND** three `FollowedChannel` rows exist, one per house channel

#### Scenario: System user is not auto-followed

- **GIVEN** the house project exists
- **WHEN** a new user with `is_system_user = True` is created
- **THEN** no Follow row is created

#### Scenario: No house project, no failure

- **GIVEN** a database with no Project where `is_house_project = True`
- **WHEN** a new user is created
- **THEN** the user create succeeds
- **AND** no Follow row is created
- **AND** a warning is logged

### Requirement: Endpoint to list the authenticated user's follows

The platform SHALL expose `GET /api/follows`, authentication required. The endpoint SHALL return the requesting user's full set of follows. Each follow SHALL include: the project's slug, title, hero/icon image URL (nullable), the follow's `created_at`, and the list of channels on that project annotated with whether the user is following each one (`{id, name, followed: bool}`).

The endpoint SHALL return an empty list for an authenticated user with no follows. The endpoint SHALL return 401 for unauthenticated requests.

#### Scenario: User with multiple follows gets all of them with channel follow state

- **GIVEN** an authenticated user U following projects P1, P2, and P3
- **WHEN** U fetches `GET /api/follows`
- **THEN** the response is 200
- **AND** the response contains three entries, one per followed project
- **AND** each entry includes its project's slug, title, hero image URL, and a list of every channel on the project with a `followed: bool` flag derived from `FollowedChannel` existence

#### Scenario: User with no follows

- **GIVEN** an authenticated user U with no Follow rows
- **WHEN** U fetches `GET /api/follows`
- **THEN** the response is 200
- **AND** the response is an empty list

#### Scenario: Anonymous request

- **WHEN** an unauthenticated client fetches `GET /api/follows`
- **THEN** the response is 401

### Requirement: Endpoint to read a single project's follow preferences

The platform SHALL expose `GET /api/projects/{slug}/follow/preferences`, authentication required. The endpoint SHALL return the requesting user's follow state for the specified project.

The response SHALL include the project's slug and title and the list of channels on the project annotated with the user's follow state per channel (`{id, name, followed: bool}`).

The endpoint SHALL return 404 if the requesting user is not following the project (i.e., no `Follow` row exists). The endpoint SHALL return 401 for unauthenticated requests.

#### Scenario: Followed project returns channel follow states

- **GIVEN** an authenticated user U following project P with three channels, with `FollowedChannel` rows for two of them
- **WHEN** U fetches `GET /api/projects/{P.slug}/follow/preferences`
- **THEN** the response is 200
- **AND** the response contains three channel entries
- **AND** two channels have `followed: true`
- **AND** one channel has `followed: false`

#### Scenario: Not following returns 404

- **GIVEN** an authenticated user U not following project P
- **WHEN** U fetches `GET /api/projects/{P.slug}/follow/preferences`
- **THEN** the response is 404

#### Scenario: Anonymous request

- **WHEN** an unauthenticated client fetches `GET /api/projects/{P.slug}/follow/preferences`
- **THEN** the response is 401

## ADDED Requirements

### Requirement: FollowedChannel model replaces FollowChannelPreference

The system SHALL provide a `FollowedChannel` model whose row identity (`follow`, `channel`) records that the user follows the named channel. The model SHALL replace `FollowChannelPreference` from earlier phases. It SHALL pin its database table name to `follow_channel_preferences` via `Meta.db_table` so the migration is a pure column-drop on the existing table.

The model SHALL have no `email_enabled` or `in_app_enabled` columns. *Existence* of the row is the followed signal; per-medium gating is owned by the `notifications` capability through the User-level cadence settings.

The `(follow, channel)` pair SHALL be unique. Deleting a `Follow` SHALL cascade-delete every `FollowedChannel` row referencing it.

#### Scenario: FollowedChannel row identity drives "is followed"

- **WHEN** code asks whether user U follows channel C on project P
- **THEN** the answer SHALL be: `FollowedChannel.objects.filter(follow__user=U, follow__project=P, channel=C).exists()`

#### Scenario: Cascade delete from Follow

- **GIVEN** user U follows project P with three `FollowedChannel` rows
- **WHEN** the underlying `Follow` row is deleted
- **THEN** all three `FollowedChannel` rows SHALL also be deleted

### Requirement: Endpoint to follow a single channel

The platform SHALL expose `POST /api/projects/{slug}/follow/channels/{channel_id}`, authentication required. The endpoint SHALL create a `FollowedChannel` row for the requesting user's `Follow` on the specified project and the specified channel.

The endpoint SHALL return 404 if any of the following hold: the project doesn't exist; the channel doesn't belong to the project; the user is not following the project. The endpoint SHALL return 401 for unauthenticated requests. The endpoint SHALL be idempotent: if the `FollowedChannel` row already exists, the endpoint SHALL return 200 without creating a duplicate.

The endpoint SHALL return 200 with the channel's current `followed: true` state on success.

#### Scenario: Follow a channel the user wasn't following

- **GIVEN** an authenticated user U following project P with channel C, with no `FollowedChannel(follow, C)` row
- **WHEN** U POSTs to `/api/projects/{P.slug}/follow/channels/{C.id}`
- **THEN** the response is 200
- **AND** a `FollowedChannel` row exists for `(U's Follow on P, C)`

#### Scenario: Re-following a channel is idempotent

- **GIVEN** the user already has a `FollowedChannel` row for `(Follow, C)`
- **WHEN** U POSTs to the same endpoint
- **THEN** the response is 200
- **AND** there is still exactly one `FollowedChannel` row

#### Scenario: Channel does not belong to the project returns 404

- **GIVEN** a channel C' that belongs to project P' (not P)
- **WHEN** U POSTs to `/api/projects/{P.slug}/follow/channels/{C'.id}`
- **THEN** the response is 404

#### Scenario: Not following the project returns 404

- **GIVEN** U is not following project P
- **WHEN** U POSTs to `/api/projects/{P.slug}/follow/channels/{any_channel.id}`
- **THEN** the response is 404

### Requirement: Endpoint to unfollow a single channel

The platform SHALL expose `DELETE /api/projects/{slug}/follow/channels/{channel_id}`, authentication required. The endpoint SHALL hard-delete the `FollowedChannel` row for the requesting user's `Follow` on the project and the specified channel.

The endpoint SHALL be idempotent: deleting a non-existent `FollowedChannel` SHALL return 204. The endpoint SHALL NOT delete the user's `Follow` row, even when the deleted `FollowedChannel` was the user's last followed channel on the project — an empty-channels-followed `Follow` is a valid state (the user can re-enrol channels via the popover).

The endpoint SHALL return 404 if the project doesn't exist, the channel doesn't belong to the project, or the user is not following the project. The endpoint SHALL return 401 for unauthenticated requests.

#### Scenario: Unfollow an individually-followed channel

- **GIVEN** an authenticated user U following project P with a `FollowedChannel` row for channel C
- **WHEN** U DELETEs `/api/projects/{P.slug}/follow/channels/{C.id}`
- **THEN** the response is 204
- **AND** no `FollowedChannel` row exists for `(U's Follow on P, C)`
- **AND** the `Follow` row for `(U, P)` is unchanged

#### Scenario: Unfollow the last channel keeps the Follow

- **GIVEN** an authenticated user U following project P with `FollowedChannel` rows for exactly one channel C
- **WHEN** U DELETEs `/api/projects/{P.slug}/follow/channels/{C.id}`
- **THEN** the response is 204
- **AND** no `FollowedChannel` row remains
- **AND** the `Follow` row for `(U, P)` is unchanged (still present, no children)

#### Scenario: Unfollow when not followed is a no-op

- **GIVEN** an authenticated user U following project P, with no `FollowedChannel` row for channel C
- **WHEN** U DELETEs `/api/projects/{P.slug}/follow/channels/{C.id}`
- **THEN** the response is 204

### Requirement: Data migration sweeps existing FollowChannelPreference rows

A one-shot data migration SHALL collapse every existing `FollowChannelPreference` row to a `FollowedChannel` row based on the prior booleans:

- A row with `email_enabled = True` OR `in_app_enabled = True` SHALL survive as a `FollowedChannel` row (the booleans are subsequently dropped as columns by a follow-up schema migration).
- A row with both `email_enabled = False` AND `in_app_enabled = False` SHALL be deleted before the booleans are dropped.

The migration SHALL NOT delete any `Follow` row, even when the sweep removes the last `FollowedChannel` underneath it — that's a valid (if uncommon) "I follow this project, currently subscribed to none of its channels" state. The user can re-enrol via the popover.

The migration SHALL NOT add any `Follow` rows. Users who explicitly unfollowed a project pre-migration (no `Follow` row exists) stay unfollowed — this includes users who explicitly unfollowed the house project. The sweep operates purely on `FollowChannelPreference` rows that already exist; the new-user auto-follow signal handles future signups.

#### Scenario: All-True row survives

- **GIVEN** a `FollowChannelPreference(follow=F, channel=C, email_enabled=True, in_app_enabled=True)`
- **WHEN** the migration runs
- **THEN** a `FollowedChannel(follow=F, channel=C)` row exists
- **AND** no row with both booleans `False` referencing `(F, C)` exists

#### Scenario: Either-on row survives

- **GIVEN** a `FollowChannelPreference(follow=F, channel=C, email_enabled=False, in_app_enabled=True)`
- **WHEN** the migration runs
- **THEN** a `FollowedChannel(follow=F, channel=C)` row exists

#### Scenario: Both-off row deleted

- **GIVEN** a `FollowChannelPreference(follow=F, channel=C, email_enabled=False, in_app_enabled=False)`
- **WHEN** the migration runs
- **THEN** no `FollowedChannel(follow=F, channel=C)` row exists
- **AND** the underlying `Follow=F` row SHALL be retained

#### Scenario: User without house-project Follow stays unfollowed

- **GIVEN** an existing active non-system user U with no `Follow` row on the house project
- **WHEN** the migration runs
- **THEN** no `Follow` row is created for U on the house project
- **AND** no `FollowedChannel` rows are created for U on the house project's channels

## REMOVED Requirements

### Requirement: Endpoint to update a single channel preference

**Reason**: `FollowChannelPreference` no longer carries `email_enabled` / `in_app_enabled` booleans, so there is nothing for a PATCH to toggle. The follow/unfollow semantics are now expressed as existence of a `FollowedChannel` row, addressed by the new `POST` and `DELETE` endpoints under `/api/projects/{slug}/follow/channels/{channel_id}` (see ADDED requirements above).

**Migration**: Web-ui callers of `PATCH /api/projects/{slug}/follow/channels/{channel_id}` SHALL migrate to:
- `POST` with the same path to add a `FollowedChannel` row.
- `DELETE` with the same path to remove it.

The `email_enabled` / `in_app_enabled` fields disappear from request/response shapes. Email cadence is now controlled per-user-per-kind via `User.discussion_email_frequency` and `User.article_email_frequency` (see `notifications` spec).
