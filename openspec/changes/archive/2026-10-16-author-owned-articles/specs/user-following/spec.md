# Spec Delta

## Purpose

Following a person rather than a project: the follow and channel targets, the
endpoints, and how a person's articles reach their followers.

## ADDED Requirements

### Requirement: A channel belongs to a project or to a person

A channel SHALL have either a project or an owner (a user), never both and never neither. Channel names SHALL be unique per project and unique per owner. A person SHALL have at most one channel; it SHALL be created the first time one of their author-owned articles becomes published, and SHALL NOT be created at signup. A person's channel SHALL NOT be renamed, deleted or added to through the project channel-management endpoints.

#### Scenario: Channel with both owners is rejected
- **WHEN** a channel is saved with both `project` and `owner` set
- **THEN** the save SHALL be rejected

#### Scenario: Channel with neither is rejected
- **WHEN** a channel is saved with `project` null and `owner` null
- **THEN** the save SHALL be rejected

#### Scenario: First publish creates the person's channel
- **GIVEN** user U with no channel
- **WHEN** U publishes their first author-owned article
- **THEN** exactly one channel with `owner = U` SHALL exist and the article SHALL be delivered through it

#### Scenario: Second publish reuses it
- **GIVEN** user U who already has a channel
- **WHEN** U publishes another author-owned article
- **THEN** no second channel SHALL be created

#### Scenario: Signup creates no channel
- **WHEN** a new user is created
- **THEN** no channel with `owner` set SHALL exist for them

### Requirement: A follow targets a project or a person

A follow SHALL have either a project or a followed user, never both and never neither. A user SHALL have at most one follow per project and one per followed user. A user SHALL NOT follow themselves. Following a person SHALL deliver only that person's author-owned articles; it SHALL NOT deliver their projects, comments, competition entries or articles on projects.

#### Scenario: Follow with both targets is rejected
- **WHEN** a follow is saved with both `project` and `followed_user` set
- **THEN** the save SHALL be rejected

#### Scenario: Self-follow is rejected
- **WHEN** user U calls `POST /api/users/{U.id}/follow`
- **THEN** the response SHALL be 400 and no follow SHALL exist

#### Scenario: A followed person's project article is not delivered
- **GIVEN** V follows U and does not follow project P
- **WHEN** U publishes an article on P
- **THEN** V SHALL receive no notification for it

### Requirement: Endpoints to follow and unfollow a person

`POST /api/users/{id}/follow` SHALL create a follow of user `{id}` for the authenticated caller, and a followed-channel row for the person's channel if one exists. It SHALL be idempotent. `DELETE /api/users/{id}/follow` SHALL hard-delete the follow and its followed-channel rows; deleting a follow that does not exist SHALL return 204. Both SHALL return 401 for anonymous callers and 404 for a user who has no public profile (inactive, system user, unknown).

`GET /api/users/{id}` SHALL include `is_followed`, true when the authenticated caller follows `{id}`, false otherwise and for anonymous callers.

#### Scenario: Follow a person who has published
- **GIVEN** authenticated V and user U who has a channel
- **WHEN** V calls `POST /api/users/{U.id}/follow`
- **THEN** the response SHALL be 200
- **AND** a follow of U by V and a followed-channel row for U's channel SHALL exist
- **AND** `GET /api/users/{U.id}` for V SHALL return `is_followed = true`

#### Scenario: Follow a person who has not published
- **GIVEN** user U with no channel
- **WHEN** V calls `POST /api/users/{U.id}/follow`
- **THEN** the response SHALL be 200 and a follow SHALL exist with no followed-channel rows

#### Scenario: The person's first publish enrols existing followers
- **GIVEN** V follows U, and U has no channel yet
- **WHEN** U publishes their first author-owned article
- **THEN** V SHALL have a followed-channel row for U's new channel
- **AND** V SHALL receive the notification for that article

#### Scenario: Unfollow
- **GIVEN** V follows U
- **WHEN** V calls `DELETE /api/users/{U.id}/follow`
- **THEN** the response SHALL be 204 and no follow or followed-channel rows SHALL remain

#### Scenario: Follow a system user
- **WHEN** V calls `POST /api/users/{id}/follow` for a system user
- **THEN** the response SHALL be 404

#### Scenario: Anonymous
- **WHEN** an unauthenticated client calls either endpoint
- **THEN** the response SHALL be 401

### Requirement: Follow button on the public profile

A public profile that is not the viewer's own SHALL show a Follow button reflecting `is_followed`, which calls the follow and unfollow endpoints. An anonymous viewer SHALL be sent to login. The viewer's own profile SHALL NOT show one.

#### Scenario: Visitor follows from the profile
- **GIVEN** authenticated V on U's profile, not following
- **WHEN** V presses Follow
- **THEN** the button SHALL show the followed state and `GET /api/users/{U.id}` SHALL report `is_followed = true`

#### Scenario: Own profile
- **WHEN** U views their own profile
- **THEN** no Follow button SHALL be rendered

### Requirement: A person's articles fan out through their channel

When an author-owned article becomes globally visible, every user with a followed-channel row for the author's channel SHALL receive a notification on the same terms as a project-channel follower: an unread in-app row, email on the recipient's article cadence, the author excluded, and the backdated-publish and approval rules of the `articles` capability unchanged. A person's channel is never a house channel.

#### Scenario: Followers are notified
- **GIVEN** V and W follow U and have followed-channel rows for U's channel
- **WHEN** U, a trusted author, publishes an author-owned article
- **THEN** V and W SHALL each have one unread notification for it
- **AND** U SHALL have none

#### Scenario: Untrusted author's article waits for approval
- **GIVEN** V follows U, and U's `article_trust` is false
- **WHEN** U publishes an author-owned article
- **THEN** V SHALL receive nothing until an administrator approves it
- **AND** on approval V SHALL receive one notification

### Requirement: The follows list carries both kinds of follow

Each entry of `GET /api/follows` SHALL carry a `target` of `project` or `user`. A project entry SHALL carry the project fields as today. A user entry SHALL carry the user's id, display name and avatar URL, and its channel list SHALL contain the person's channel when it exists. The Following page SHALL render user entries with a link to the profile and the same channel toggle as a project entry.

#### Scenario: Mixed follows
- **GIVEN** V follows project P and user U
- **WHEN** V fetches `GET /api/follows`
- **THEN** the response SHALL contain one `target = "project"` entry for P and one `target = "user"` entry for U with U's id, name and avatar URL

#### Scenario: Followed person without a channel
- **GIVEN** V follows U who has not published
- **WHEN** V fetches `GET /api/follows`
- **THEN** U's entry SHALL have an empty channel list
