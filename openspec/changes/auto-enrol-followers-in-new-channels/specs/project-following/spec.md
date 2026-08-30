## ADDED Requirements

### Requirement: Creating a Channel enrols the project's existing followers

When a `Channel` is created, the platform SHALL create a `FollowedChannel` row
for that channel against every `Follow` row that already exists on the
channel's project. Following a project therefore subscribes the follower to
every channel the project gains from then on; opting out of an individual
channel remains available, and unfollowing the project is what stops future
channels reaching the user at all.

This SHALL be implemented via a `post_save` signal on `Channel` scoped to
`created = True`. Saving an existing channel — a rename in particular — SHALL
NOT enrol anyone.

Enrolment SHALL be idempotent: where a `FollowedChannel` row for
`(follow, channel)` already exists, no duplicate SHALL be created and the save
SHALL NOT raise.

Enrolment SHALL run in the same transaction as the channel insert, so a
rolled-back channel creation leaves no enrolments behind.

Bulk-creating Channels (`Channel.objects.bulk_create()`) bypasses the signal by
design, as does any data migration operating on historical model classes.
Callers using those paths SHALL write the `FollowedChannel` rows themselves.

#### Scenario: New channel enrols existing followers of the project

- **GIVEN** users U1 and U2 follow project P
- **WHEN** a new `Channel` C is created on P
- **THEN** a `FollowedChannel` row exists for `(U1's Follow on P, C)`
- **AND** a `FollowedChannel` row exists for `(U2's Follow on P, C)`

#### Scenario: Users who do not follow the project are not enrolled

- **GIVEN** user U1 follows project P and user U2 follows only project Q
- **WHEN** a new `Channel` C is created on P
- **THEN** a `FollowedChannel` row exists for `(U1's Follow on P, C)`
- **AND** U2 has no `FollowedChannel` row referencing C

#### Scenario: Renaming a channel enrols nobody

- **GIVEN** user U follows project P with channels C and D, and has unfollowed C
- **WHEN** C is renamed and saved
- **THEN** U still has no `FollowedChannel` row for C

#### Scenario: A project's first channel enrols nobody and does not fail

- **WHEN** a new `Project` is created, triggering creation of its default
  "Updates" channel
- **THEN** the project save succeeds
- **AND** no `FollowedChannel` rows are created

#### Scenario: Enrolment does not duplicate an existing row

- **GIVEN** user U follows project P and already has a `FollowedChannel` row
  for channel C on P
- **WHEN** the enrolment for C runs again
- **THEN** exactly one `FollowedChannel` row exists for `(U's Follow on P, C)`
- **AND** no error is raised

#### Scenario: A Follow with no channels is enrolled like any other

- **GIVEN** user U has a `Follow` on project P with no `FollowedChannel` rows
- **WHEN** a new `Channel` C is created on P
- **THEN** a `FollowedChannel` row exists for `(U's Follow on P, C)`

## MODIFIED Requirements

### Requirement: User can follow and unfollow a Project

The platform SHALL expose two endpoints:

- `POST /api/projects/{slug}/follow` — authentication required. Creates a `Follow` row for the requesting user against the project identified by `slug`, and creates a `FollowedChannel` row for every `Channel` currently associated with that project. The endpoint SHALL be idempotent: if a `Follow` already exists for `(user, project)`, no duplicate row is created. If the `Follow` exists but the user is missing `FollowedChannel` rows for some channels, the existing rows SHALL be left in place — POST SHALL NOT re-enrol a user in channels they have unfollowed. Channels added to the project after the user followed are covered by "Creating a Channel enrols the project's existing followers" and need no repair from this endpoint.

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

#### Scenario: Re-POST does not re-enrol a channel the user unfollowed

- **GIVEN** an authenticated user follows project P, which has channels C1 and C2, and has unfollowed C2
- **WHEN** the user POSTs to `/api/projects/{P.slug}/follow` again
- **THEN** the response is 200
- **AND** the user's `FollowedChannel` rows still cover only C1 (no row for C2 is created)

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
