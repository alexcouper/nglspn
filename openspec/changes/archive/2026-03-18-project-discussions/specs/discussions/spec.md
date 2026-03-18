## ADDED Requirements

### Requirement: Discussion model with threaded replies

The system SHALL store discussions in a single model with a self-referential parent foreign key. A discussion with no parent is a root discussion (tied to a project). A discussion with a parent is a reply. Both require a project foreign key and an author foreign key.

Each discussion SHALL have: id (UUID), project (FK), author (FK to User), parent (nullable FK to self), body (text), created_at, and updated_at.

#### Scenario: Create a root discussion on a project
- **WHEN** an authenticated user submits a new discussion with a body and project ID
- **THEN** the system creates a discussion with the given project, the user as author, parent as null, and the provided body

#### Scenario: Reply to an existing discussion
- **WHEN** an authenticated user submits a reply with a body and a parent discussion ID
- **THEN** the system creates a discussion with the same project as the parent, the user as author, and the parent set to the referenced discussion

#### Scenario: Reply inherits project from parent
- **WHEN** a reply is created referencing a parent discussion
- **THEN** the reply's project SHALL be set to the parent's project regardless of any project value provided in the request

### Requirement: Discussions Django app

The system SHALL have a dedicated Django app at `apps/discussions/` with its own models, admin registration, and migrations. The app SHALL be registered in Django settings.

#### Scenario: App is registered
- **WHEN** Django starts
- **THEN** the `apps.discussions` app is loaded and its models are available

### Requirement: Discussions service layer

The system SHALL expose discussion operations through a service layer following the established handler/query pattern. The service SHALL be registered in `services/__init__.py` on both `HANDLERS` and `REPO`.

The handler interface SHALL support:
- `create_discussion(project_id, author_id, body, parent_id=None)` — creates a discussion or reply
- `delete_discussion(discussion_id, requesting_user_id)` — deletes a discussion if the requesting user is the author

The query interface SHALL support:
- `list_for_project(project_id)` — returns all root discussions for a project with their replies
- `get_by_id(discussion_id)` — returns a single discussion with its replies

#### Scenario: Service is accessible via HANDLERS and REPO
- **WHEN** code imports `from services import HANDLERS, REPO`
- **THEN** `HANDLERS.discussions` and `REPO.discussions` are available

### Requirement: Discussions API endpoints

The system SHALL expose discussions through Django Ninja API endpoints requiring JWT authentication. The router SHALL be registered on the API at an appropriate path.

Endpoints:
- `GET /projects/{project_id}/discussions` — list root discussions with replies for a project
- `POST /projects/{project_id}/discussions` — create a new root discussion
- `POST /projects/{project_id}/discussions/{discussion_id}/replies` — reply to a discussion
- `DELETE /projects/{project_id}/discussions/{discussion_id}` — delete a discussion (author only)

#### Scenario: List discussions for a project
- **WHEN** an authenticated user sends GET to `/projects/{project_id}/discussions`
- **THEN** the system returns a list of root discussions with their replies, ordered by creation date

#### Scenario: Create a new discussion
- **WHEN** an authenticated user sends POST to `/projects/{project_id}/discussions` with a body
- **THEN** the system creates a root discussion and returns it with 201 status

#### Scenario: Reply to a discussion
- **WHEN** an authenticated user sends POST to `/projects/{project_id}/discussions/{discussion_id}/replies` with a body
- **THEN** the system creates a reply under the given discussion and returns it with 201 status

#### Scenario: Delete own discussion
- **WHEN** the author of a discussion sends DELETE to `/projects/{project_id}/discussions/{discussion_id}`
- **THEN** the system deletes the discussion and returns 204 status

#### Scenario: Cannot delete another user's discussion
- **WHEN** a user who is not the author sends DELETE to `/projects/{project_id}/discussions/{discussion_id}`
- **THEN** the system returns 403 status

#### Scenario: Unauthenticated access is rejected
- **WHEN** an unauthenticated user sends any request to a discussions endpoint
- **THEN** the system returns 401 status

### Requirement: Async notification trigger on comment creation

When a discussion or reply is created, the discussions service SHALL enqueue an async task to create notifications. The task SHALL NOT block the API response.

#### Scenario: Discussion creation triggers notification task
- **WHEN** a new discussion is created via the service
- **THEN** the service enqueues a `create_discussion_notifications` task with the discussion ID

#### Scenario: Reply creation triggers notification task
- **WHEN** a new reply is created via the service
- **THEN** the service enqueues a `create_discussion_notifications` task with the reply ID

### Requirement: Discussion response includes author info

Discussion API responses SHALL include the author's id, first name, and last name so the frontend can display attribution.

#### Scenario: Discussion response shape
- **WHEN** a discussion is returned from any API endpoint
- **THEN** it SHALL include: id, body, created_at, author (with id, first_name, last_name), and replies (list of discussions, for root discussions)
