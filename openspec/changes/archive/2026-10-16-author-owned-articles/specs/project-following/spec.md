# Spec Delta

## MODIFIED Requirements

### Requirement: Endpoint to list the authenticated user's follows

The platform SHALL expose `GET /api/follows`, authentication required. The endpoint SHALL return the requesting user's full set of follows, of projects and of people. Each follow SHALL include a `target` of `project` or `user`, the follow's `created_at`, and the list of channels on the target annotated with whether the user is following each one (`{id, name, followed: bool}`). A project follow SHALL include the project's slug, title and hero/icon image URL (nullable); a user follow SHALL include the user's id, display name and avatar URL (nullable), and the project fields SHALL be null.

The endpoint SHALL return an empty list for an authenticated user with no follows. The endpoint SHALL return 401 for unauthenticated requests.

#### Scenario: User with multiple follows gets all of them with channel follow state

- **GIVEN** an authenticated user U following projects P1, P2, and P3
- **WHEN** U fetches `GET /api/follows`
- **THEN** the response is 200
- **AND** the response contains three entries, one per followed project, each with `target = "project"`
- **AND** each entry includes its project's slug, title, hero image URL, and a list of every channel on the project with a `followed: bool` flag derived from `FollowedChannel` existence

#### Scenario: A followed person is listed alongside projects

- **GIVEN** an authenticated user U following project P and user V
- **WHEN** U fetches `GET /api/follows`
- **THEN** the response contains two entries: one `target = "project"` for P and one `target = "user"` carrying V's id, name and avatar URL with null project fields

#### Scenario: User with no follows

- **GIVEN** an authenticated user U with no Follow rows
- **WHEN** U fetches `GET /api/follows`
- **THEN** the response is 200
- **AND** the response is an empty list

#### Scenario: Anonymous request

- **WHEN** an unauthenticated client fetches `GET /api/follows`
- **THEN** the response is 401
