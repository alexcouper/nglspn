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

The Naglasúpan project (the project with `is_house_project = True`) SHALL have, in addition to the default "Updates" channel, two further channels named "Competition Winners" and "Product Updates".

These channels SHALL be created as part of the one-shot data migration that ships with this change. The names SHALL match the two existing `BroadcastEmailType` values 1:1 in concept: "Competition Winners" corresponds to `competition_results`, "Product Updates" corresponds to `platform_updates`.

#### Scenario: Naglasúpan has three channels after migration

- **GIVEN** the Naglasúpan Project row exists prior to migration
- **WHEN** the data migration runs
- **THEN** Naglasúpan has exactly three channels: "Updates", "Competition Winners", "Product Updates"

#### Scenario: Other projects have only Updates

- **GIVEN** a non-Naglasúpan Project P existing prior to migration
- **WHEN** the data migration runs
- **THEN** P has exactly one channel: "Updates"

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

When a new `User` is created (`is_active = True`, `is_system_user = False`), the platform SHALL automatically create a `Follow` row for that user against the house project (the project with `is_house_project = True`), with `FollowChannelPreference` rows for every Channel of the house project. All `email_enabled` and `in_app_enabled` switches SHALL default to `True`.

This SHALL be implemented via a `post_save` signal on User scoped to `created = True`. The signal handler SHALL silently no-op (with a logged warning) if no house project exists in the database — this is the greenfield dev/test case.

System users (`is_system_user = True`) SHALL NOT be auto-followed.

#### Scenario: New regular user is auto-followed

- **GIVEN** the house project exists with three channels
- **WHEN** a new user with `is_system_user = False` is created
- **THEN** a Follow row exists for `(user, house_project)`
- **AND** three `FollowChannelPreference` rows exist, all with `email_enabled = True` and `in_app_enabled = True`

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

### Requirement: Data migration seeds existing-user preferences from legacy flags

A one-shot data migration SHALL backfill `Follow` rows and `FollowChannelPreference` rows for every existing active non-system User against the house project. The migration SHALL seed per-channel email switches from the legacy `User.email_opt_in_*` fields rather than defaulting to `True`:

- "Competition Winners" channel → `email_enabled = user.email_opt_in_competition_results`
- "Product Updates" channel → `email_enabled = user.email_opt_in_platform_updates`
- "Updates" channel → `email_enabled = True` (no legacy correlate)

In-app switches SHALL default to `True` for all three channels (the existing in-app system has no per-category opt-in to migrate from).

The migration SHALL use `bulk_create` in batches of 1000 to keep transaction size bounded. The migration SHALL be idempotent: running it twice produces the same end-state without errors.

The migration SHALL NOT modify or delete the legacy `email_opt_in_competition_results` or `email_opt_in_platform_updates` fields on User. These fields remain operational and continue to drive the existing email broadcast pipeline (which is unchanged by this change).

#### Scenario: Opted-out user has email switch off

- **GIVEN** an existing user U with `email_opt_in_competition_results = False` and `email_opt_in_platform_updates = True`
- **WHEN** the data migration runs
- **THEN** U has a Follow row against the house project
- **AND** the "Competition Winners" preference has `email_enabled = False`
- **AND** the "Product Updates" preference has `email_enabled = True`
- **AND** the "Updates" preference has `email_enabled = True`
- **AND** all three preferences have `in_app_enabled = True`

#### Scenario: Inactive users skipped

- **GIVEN** an existing user U with `is_active = False`
- **WHEN** the data migration runs
- **THEN** no Follow row is created for U

#### Scenario: System users skipped

- **GIVEN** an existing user U with `is_system_user = True`
- **WHEN** the data migration runs
- **THEN** no Follow row is created for U

#### Scenario: Re-running the migration is idempotent

- **GIVEN** the migration has already run
- **WHEN** the migration is forced to run again (developer scenario)
- **THEN** no duplicate Follow or `FollowChannelPreference` rows are created
- **AND** existing preference values are not clobbered

### Requirement: Legacy email opt-in flags are untouched in Phase 1

The User-model fields `email_opt_in_competition_results` and `email_opt_in_platform_updates` SHALL remain in place after this change, with their existing default of `True`. No endpoint or signal in this change writes to them. The existing email broadcast pipeline (`services/email/django_impl/query.py::list_opted_in_for_broadcast_type`) SHALL continue to read them unchanged.

#### Scenario: Broadcast recipient resolution is unchanged

- **GIVEN** a `BroadcastEmail` with `email_type = "platform_updates"` and a population of users with mixed opt-in states
- **WHEN** `resolve_broadcast_recipients` is called
- **THEN** the resulting QuerySet SHALL match the result returned before this change ships

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

