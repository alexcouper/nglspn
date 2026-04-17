## ADDED Requirements

### Requirement: Email tasks use service layer for lookups

The async tasks in `api/tasks/email.py` SHALL NOT import or use `User.objects.get()`, `Project.objects.get()`, or `BroadcastEmail.objects.get()` directly. All model lookups SHALL be delegated to `REPO` services.

#### Scenario: Send verification email task uses REPO
- **WHEN** the `send_verification_email` task is executed
- **THEN** it SHALL look up the user via `REPO.users.get_active_by_id()` instead of `User.objects.get()`

#### Scenario: Send password reset email task uses REPO
- **WHEN** the `send_password_reset_email` task is executed
- **THEN** it SHALL look up the user via `REPO.users.get_active_by_id()` instead of `User.objects.get()`

#### Scenario: Send project approved email task uses REPO
- **WHEN** the `send_project_approved_email` task is executed
- **THEN** it SHALL look up the project via `REPO.project.get_by_id()` instead of `Project.objects.select_related().get()`

#### Scenario: Send new project notification task uses REPO
- **WHEN** the `send_new_project_notification` task is executed
- **THEN** it SHALL look up the project via `REPO.project.get_by_id()` instead of `Project.objects.select_related().get()`

#### Scenario: Send broadcast email task uses REPO
- **WHEN** the `send_broadcast_email` task is executed
- **THEN** it SHALL look up the broadcast email and user via `REPO.email.get_broadcast_by_id()` and `REPO.users.get_by_id()` instead of `BroadcastEmail.objects.get()` and `User.objects.get()`

### Requirement: Auth router delegates user updates to service layer

The `update_current_user` endpoint in `api/routers/auth.py` SHALL NOT directly mutate and save the User model. It SHALL delegate to `HANDLERS.users.update_profile()` or an equivalent handler method.

#### Scenario: Update current user uses handler
- **WHEN** the update current user endpoint is called
- **THEN** it SHALL call `HANDLERS.users.update_profile()` instead of directly setting attributes and calling `user.save()`

### Requirement: Architecture documentation

The system SHALL include an `ARCHITECTURE.md` file in the Django backend root (`src/django-backend/`) documenting the service-layer architectural rule.

#### Scenario: Architecture document describes the rule
- **WHEN** a developer reads `ARCHITECTURE.md`
- **THEN** it SHALL state that the API layer (routers, schemas, tasks) MUST NOT directly access the database via Django ORM, and MUST communicate through service interfaces (`HANDLERS` and `REPO`)

#### Scenario: Architecture document describes the pattern
- **WHEN** a developer reads `ARCHITECTURE.md`
- **THEN** it SHALL describe the service-layer pattern: ABC interfaces in `handler_interface.py` and `query_interface.py`, Django implementations in `django_impl/`, and centralized registration in `services/__init__.py`

#### Scenario: Architecture document lists service domains
- **WHEN** a developer reads `ARCHITECTURE.md`
- **THEN** it SHALL list all service domains: competitions, discussions, email, image, notifications, project, project_images, registration, review, tags, users

### Requirement: No direct model imports in API layer

The API layer files (routers, schemas, tasks) SHALL NOT import from `apps.*.models` for the purpose of querying or mutating data. The only permitted usage is enum/constant references (e.g., `ProjectStatus.APPROVED`) where the enum value is needed for comparison in service-layer code or schema definitions.

#### Scenario: Routers do not import models for ORM queries
- **WHEN** any router in `api/routers/` is loaded
- **THEN** it SHALL NOT import model classes for the purpose of calling `.objects`, `.filter()`, `.get()`, `.create()`, `.save()`, `.delete()`, or `.update()`

#### Scenario: Schemas do not perform ORM queries
- **WHEN** any schema in `api/schemas/` is used
- **THEN** it SHALL NOT call `.filter()`, `.all()`, `.count()`, `.exists()`, `.prefetch_related()`, `.select_related()`, or any other ORM query method

#### Scenario: Tasks do not use Model.objects
- **WHEN** any task in `api/tasks/` is executed
- **THEN** it SHALL NOT call `Model.objects.get()` or `Model.objects.filter()`