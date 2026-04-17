## Context

The Django backend follows a service-layer pattern where the API layer (routers, schemas, tasks) communicates with the database exclusively through abstract interfaces in `services/`. Each domain has `handler_interface.py` (writes) and `query_interface.py` (reads), with `django_impl/` providing concrete ORM implementations. Services are registered centrally in `services/__init__.py` via `HANDLERS` (writes) and `REPO` (reads).

Currently, 4 domains lack service layers entirely (competitions, tags, project images, review/rankings), and several existing modules have leaks where the API bypasses the service layer and uses Django ORM directly.

## Goals / Non-Goals

**Goals:**
- Encapsulate all DB access for competitions, tags, project images, and review/rankings behind service interfaces
- Eliminate all direct ORM usage in API routers, schemas, and async tasks
- Maintain identical external API contracts (no endpoint, request, or response changes)
- Follow the established interface pattern (ABC → django_impl → HANDLERS/REPO registry)
- Document the service-layer architectural rule and conventions

**Non-Goals:**
- Splitting the monolith into microservices now — this is preparatory work only
- Changing any API endpoint paths, request/response schemas, or behavior
- Refactoring the existing well-structured service layers (discussions, email, notifications, image variants, project, registration, users) — those are already compliant
- Adding new features or changing business logic

## Decisions

### 1. Four new service modules, one per missing domain

Create `services/competitions/`, `services/tags/`, `services/project_images/`, `services/review/` — each with the standard pattern: `handler_interface.py`, `query_interface.py`, `django_impl/handler.py`, `django_impl/query.py`.

**Rationale**: Matches the existing convention exactly. Each domain has distinct models and operations. Keeping them separate preserves the extraction boundary.

**Alternative considered**: A single `services/competitions/` that includes review/rankings — rejected because review logic is complex enough to warrant its own boundary and could be extracted independently.

### 2. Project images as a separate service from projects

Create `services/project_images/` rather than adding image methods to `services/project/`.

**Rationale**: Image lifecycle (upload → process → set role → delete) is a distinct domain with its own models (`ProjectImage`, `ImageVariant`, `UploadStatus`). Separating it means the project service stays focused on project CRUD and the image service can be extracted with its tables intact.

**Alternative considered**: Adding image handler methods to the existing `ProjectHandlerInterface` — rejected because it bloats the project interface and couples two domains that should be independently extractable.

### 3. Return types: dataclass DTOs for complex results, model instances for simple lookups

Follow the existing project service pattern: return Django model instances for simple single-object lookups, and frozen dataclass DTOs (like `ProjectListItem`, `DiscoverProjectItem`) for composed query results that join across relations.

**Rationale**: Consistent with existing code. Model instances are convenient when the caller needs the full object. DTOs are necessary when a query result includes computed fields or data from multiple models.

### 4. Schema resolve methods must not query the DB

Schema `resolve_*` methods that currently traverse ORM relations (e.g., `obj.images.all()`, `obj.tags.exclude()`) will be eliminated by ensuring the router pre-fetches all needed data via the service layer and passes it through.

**Rationale**: Schemas are part of the API layer. Allowing them to lazily query the DB defeats the service boundary. The router should orchestrate data fetching.

### 5. Email tasks use REPO for lookups

Replace `User.objects.get()`, `Project.objects.get()`, `BroadcastEmail.objects.get()` in `api/tasks/email.py` with `REPO.users.get_by_id()`, `REPO.project.get_by_id()`, and a new `REPO.email` query method.

**Rationale**: Async tasks are part of the API layer. They should use the same service interfaces as synchronous request handlers.

### 6. Auth router delegates user updates to HANDLERS.users

The `update_current_user` endpoint in `api/routers/auth.py` directly mutates and saves the User model. This will be replaced with a `HANDLERS.users.update_profile()` method.

**Rationale**: Small, targeted fix. The users service already exists — just needs one more method.

## Risks / Trade-offs

- **[Scope creep]** → Each new service module is a mechanical refactor with no behavior change. Strictly limit to extracting existing ORM calls into interfaces, no redesigning.
- **[DTO proliferation]** → Reuse existing DTOs where possible (e.g., `ProjectListItem`). Only create new DTOs when the query result is genuinely composed across models.
- **[Performance regression]** → Service layer methods should accept query-optimization parameters (e.g., `select_related`, `prefetch_related`) in the implementation, not the interface. The interface describes *what* data is returned; the implementation decides *how* to fetch it efficiently.
- **[Migration friction]** → This is a large refactor touching many files. Do it incrementally: one service module at a time, with routers migrating to the new service before the next module is created.