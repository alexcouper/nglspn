# project-following Specification

## Purpose
TBD - created by archiving change add-project-following. Update Purpose after archive.
## Requirements
### Requirement: Project carries an `is_house_project` boolean

The `Project` model SHALL include a non-nullable boolean column `is_house_project` with `default=False`. At most one `Project` row SHALL have `is_house_project = True` at any time.

Uniqueness SHALL be enforced both at the database level (Postgres partial unique constraint on `is_house_project = TRUE`) and via a save-time guard on `Project.save()` (which protects test/dev environments running SQLite where partial unique constraints are not enforced identically).

The `is_house_project` column SHALL be settable only by administrators (Django admin) or by the one-shot data migration that runs as part of this change. No public API exposes a way to toggle it.

#### Scenario: Setting the flag on a second row raises

- **GIVEN** a Project P1 with `is_house_project = True`
- **WHEN** a second Project P2 is saved with `is_house_project = True`
- **THEN** the save raises a validation error
- **AND** P2's row in the database has `is_house_project = False` (or no row exists)

#### Scenario: Re-saving the house project is idempotent

- **GIVEN** a Project P with `is_house_project = True`
- **WHEN** P is saved again with `is_house_project = True` (no change)
- **THEN** the save succeeds with no error

#### Scenario: Moving the flag between rows succeeds

- **GIVEN** a Project P1 with `is_house_project = True`
- **WHEN** P1 is updated to `is_house_project = False`, and then a different Project P2 is saved with `is_house_project = True`
- **THEN** both saves succeed
- **AND** P2 has `is_house_project = True`, P1 has `is_house_project = False`

### Requirement: Every Project has at least one Channel

Every `Project` SHALL have at least one `Channel` named "Updates" associated with it. This Channel SHALL be created automatically by a `post_save` signal on `Project` when `created=True`.

The signal SHALL create the default "Updates" channel idempotently — if the Project is saved a second time, no duplicate "Updates" channel SHALL be created (enforced by the `(project, name)` unique-together constraint).

Bulk-creating Projects (`Project.objects.bulk_create()`) bypasses the signal by design. Callers using bulk paths SHALL invoke the channel-seeding helper explicitly.

#### Scenario: New project gets an Updates channel

- **WHEN** a new `Project` is created (single-instance `save()`)
- **THEN** exactly one `Channel` with `name = "Updates"` exists for that project after the save commits

#### Scenario: Re-saving a project does not duplicate the Updates channel

- **GIVEN** a Project with one "Updates" channel
- **WHEN** the project is saved again (`created = False`)
- **THEN** no additional "Updates" channel is created

### Requirement: Naglasúpan has the two seeded channels

The Naglasúpan project (the project with `is_house_project = True`) SHALL have, in addition to the default "Updates" channel, one further channel named "Competition Winners".

The name SHALL match the sole remaining `BroadcastEmailType` value 1:1 in concept: "Competition Winners" corresponds to `competition_results`.

The house project SHALL NOT have a "Product Updates" channel. Where one exists, the data migration `follows/0006_merge_product_updates_into_updates` SHALL merge it into "Updates" by reassigning the house project's articles from "Updates" onto it, deleting the "Updates" channel, and renaming it to "Updates". The surviving channel therefore carries the "Product Updates" subscriber list.

#### Scenario: Naglasúpan has two channels after the merge migration

- **GIVEN** the Naglasúpan Project row exists with channels "Updates", "Competition Winners" and "Product Updates"
- **WHEN** the merge migration runs
- **THEN** Naglasúpan has exactly two channels: "Updates" and "Competition Winners"

#### Scenario: Surviving Updates channel carries the Product Updates subscribers

- **GIVEN** user U1 has a `FollowedChannel` row on "Product Updates" and on "Updates"
- **AND** user U2 has a `FollowedChannel` row on "Updates" only
- **WHEN** the merge migration runs
- **THEN** U1 has a `FollowedChannel` row on the surviving "Updates" channel
- **AND** U2 has no `FollowedChannel` row on any house channel

#### Scenario: Articles from both channels survive the merge

- **GIVEN** article A on the house project's "Updates" channel and article B on its "Product Updates" channel
- **WHEN** the merge migration runs
- **THEN** both A and B reference the surviving "Updates" channel
- **AND** no `Notification` row referencing A or B is deleted

#### Scenario: Merge migration is idempotent

- **GIVEN** the merge migration has already run
- **WHEN** it runs again
- **THEN** it SHALL make no changes and SHALL NOT raise

#### Scenario: Merge migration no-ops without a house project

- **GIVEN** no Project has `is_house_project = True`
- **WHEN** the merge migration runs
- **THEN** it SHALL log a warning, make no changes, and SHALL NOT raise

#### Scenario: Other projects have only Updates

- **GIVEN** a non-Naglasúpan Project P existing prior to migration
- **WHEN** the data migration runs
- **THEN** P has exactly one channel: "Updates"

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

### Requirement: Project response includes derived `is_followed` boolean

The Pydantic schema for the project-detail response SHALL include a derived field `is_followed: bool`. The field SHALL be computed from the requesting user's `Follow` rows: `True` if the requesting authenticated user has a Follow for this project, `False` otherwise (including for anonymous requests).

#### Scenario: Followed project for a followed-by user

- **GIVEN** an authenticated user U who follows Project P
- **WHEN** U fetches `/api/projects/{P.slug}`
- **THEN** the response includes `is_followed: true`

#### Scenario: Unfollowed project for a non-followed-by user

- **GIVEN** an authenticated user U who does not follow Project P
- **WHEN** U fetches `/api/projects/{P.slug}`
- **THEN** the response includes `is_followed: false`

#### Scenario: Anonymous request

- **GIVEN** an unauthenticated request
- **WHEN** it fetches `/api/projects/{P.slug}`
- **THEN** the response includes `is_followed: false`

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

When the delete leaves the `Follow` with no `FollowedChannel` rows, the endpoint SHALL delete the `Follow` as well: the user has just asked to stop, so dropping the last channel is a full unfollow rather than a silently inert follow that still reports `is_following = true`.

This is a rule about this endpoint, not an invariant on the table. A `Follow` with no `FollowedChannel` rows is a tolerated state and arrives by other routes — see "Data migration sweeps existing FollowChannelPreference rows" below.

The endpoint SHALL return `200` with a `FollowStateResponse` rather than `204`, so the caller learns the resulting project-level state instead of re-deriving the last-channel rule client-side.

The endpoint SHALL be idempotent while other channels remain: deleting a non-existent `FollowedChannel` on a `Follow` that still has others SHALL return `200` with `is_followed = true`. Once the `Follow` itself is gone, a repeat SHALL return 404.

The endpoint SHALL return 404 if the project doesn't exist, the channel doesn't belong to the project, or the user is not following the project. The endpoint SHALL return 401 for unauthenticated requests.

#### Scenario: Unfollow an individually-followed channel

- **GIVEN** an authenticated user U following project P with `FollowedChannel` rows for channels C and D
- **WHEN** U DELETEs `/api/projects/{P.slug}/follow/channels/{C.id}`
- **THEN** the response is `200` with `is_followed = true`
- **AND** no `FollowedChannel` row exists for `(U's Follow on P, C)`
- **AND** the `Follow` row for `(U, P)` is unchanged

#### Scenario: Unfollowing the last channel unfollows the project

- **GIVEN** an authenticated user U following project P with `FollowedChannel` rows for exactly one channel C
- **WHEN** U DELETEs `/api/projects/{P.slug}/follow/channels/{C.id}`
- **THEN** the response is `200` with `is_followed = false`
- **AND** no `FollowedChannel` row remains
- **AND** the `Follow` row for `(U, P)` is deleted

#### Scenario: Unfollow a channel that is already not followed

- **GIVEN** an authenticated user U following project P with a `FollowedChannel` row for channel D but none for channel C
- **WHEN** U DELETEs `/api/projects/{P.slug}/follow/channels/{C.id}`
- **THEN** the response is `200` with `is_followed = true`

#### Scenario: Repeating the last-channel unfollow is a 404

- **GIVEN** an authenticated user U who has just unfollowed their last channel on project P, so no `Follow` row remains
- **WHEN** U DELETEs `/api/projects/{P.slug}/follow/channels/{C.id}` again
- **THEN** the response is 404

### Requirement: Data migration sweeps existing FollowChannelPreference rows

A one-shot data migration SHALL collapse every existing `FollowChannelPreference` row to a `FollowedChannel` row based on the prior `email_enabled` boolean:

- A row with `email_enabled = True` SHALL survive as a `FollowedChannel` row (the booleans are subsequently dropped as columns by a follow-up schema migration).
- A row with `email_enabled = False` SHALL be deleted before the booleans are dropped, whatever `in_app_enabled` holds.

`in_app_enabled` SHALL NOT be consulted. Rows seeded by `follows/0002` carry `in_app_enabled = True` unconditionally — a value that migration wrote, not one the user chose — so any rule that ORs the two booleans matches every legacy row and discards the email opt-out it was meant to preserve.

The migration SHALL NOT delete any `Follow` row, even when the sweep removes the last `FollowedChannel` underneath it.

This is a deliberate divergence from the unfollow-channel endpoint, which *does* unfollow the project when a user drops their last channel (see "Endpoint to unfollow a single channel"). Unfollowing in bulk from a migration is a larger action than the sweep is willing to take, and the affected users receive nothing from the project either way.

The consequence is a `Follow` with no channels. That is a state the platform tolerates rather than one it prevents, and the sweep is not the only source of it. It also arises when a project owner deletes a channel (`FollowedChannel.channel` is `CASCADE`, and `DELETE /api/projects/{slug}/channels/{id}` refuses only a channel with articles or the last channel on a project), when a staff user deletes a `Channel` or a `FollowedChannel` in the Django admin, and when two `DELETE /api/projects/{slug}/follow/channels/{id}` requests race.

Everything that notifies keys on `FollowedChannel` — the article fan-out selects it directly, and the digest runs off `Notification` rows — so such a `Follow` correctly delivers nothing. The reads key on `Follow` instead: `is_followed`, `get_state` and `_follow_queryset` (`services/follows/django_impl/query.py`) all report `is_following = true`, so the project still shows as "Following" with no channels ticked, on the project page and on `/profile/following`. `POST /follow` does not repair it — the handler enrols channels only when it creates the `Follow` — but re-enrolling a channel from the popover does, because `follow_channel` only needs the `Follow` to exist.

Expect this cohort to be small: `follows/0002` seeds the house project's `Updates` channel with `email_enabled = True` unconditionally, so no house-project `Follow` can be emptied by the sweep, and `POST /follow` creates channels with `email_enabled` defaulting to `True`. Only a user who deliberately turned email off on *every* channel of a project can land here.

The migration SHALL NOT add any `Follow` rows. Users who explicitly unfollowed a project pre-migration (no `Follow` row exists) stay unfollowed — this includes users who explicitly unfollowed the house project. The sweep operates purely on `FollowChannelPreference` rows that already exist; the new-user auto-follow signal handles future signups.

#### Scenario: All-True row survives

- **GIVEN** a `FollowChannelPreference(follow=F, channel=C, email_enabled=True, in_app_enabled=True)`
- **WHEN** the migration runs
- **THEN** a `FollowedChannel(follow=F, channel=C)` row exists

#### Scenario: Email-off row deleted even though in-app was on

- **GIVEN** a `FollowChannelPreference(follow=F, channel=C, email_enabled=False, in_app_enabled=True)`
- **WHEN** the migration runs
- **THEN** no `FollowedChannel(follow=F, channel=C)` row exists
- **AND** the underlying `Follow=F` row SHALL be retained

#### Scenario: Both-off row deleted

- **GIVEN** a `FollowChannelPreference(follow=F, channel=C, email_enabled=False, in_app_enabled=False)`
- **WHEN** the migration runs
- **THEN** no `FollowedChannel(follow=F, channel=C)` row exists
- **AND** the underlying `Follow=F` row SHALL be retained

#### Scenario: In-app-off row survives on the strength of email

- **GIVEN** a `FollowChannelPreference(follow=F, channel=C, email_enabled=True, in_app_enabled=False)`
- **WHEN** the migration runs
- **THEN** a `FollowedChannel(follow=F, channel=C)` row exists

#### Scenario: User without house-project Follow stays unfollowed

- **GIVEN** an existing active non-system user U with no `Follow` row on the house project
- **WHEN** the migration runs
- **THEN** no `Follow` row is created for U on the house project
- **AND** no `FollowedChannel` rows are created for U on the house project's channels

