## Why

Four domains (competitions, tags, project images, review/rankings) have no service layer, forcing the API to access the database directly via Django ORM. Several other modules (email tasks, auth router, competition schema) also bypass the service layer with direct ORM calls. This undermines the monolith-to-microservices migration strategy — all DB access should be encapsulated behind service interfaces so that domains can be extracted with their data access intact.

## What Changes

- Create 4 new service modules following the established pattern (ABC interface → `django_impl/` → `HANDLERS`/`REPO` registries):
  - `services/competitions/` — query + handler interfaces for competition listing, detail, and highlights
  - `services/tags/` — query + handler interfaces for tag CRUD and admin review
  - `services/project_images/` — query + handler interfaces for image upload, complete, delete, and role management
  - `services/review/` — query + handler interfaces for reviewer assignments, rankings, and status updates
- Refactor `api/routers/competitions.py` to use `REPO.competitions.*` and `HANDLERS.competitions.*`
- Refactor `api/routers/my_review.py` to use `REPO.review.*` and `HANDLERS.review.*`
- Refactor `api/routers/tags.py` to use `REPO.tags.*` and `HANDLERS.tags.*`
- Refactor `api/routers/my_projects.py` image operations to use `REPO.project_images.*` and `HANDLERS.project_images.*`
- Refactor `api/tasks/email.py` to use `REPO` lookups instead of direct `Model.objects.get()`
- Refactor `api/routers/auth.py:update_current_user()` to delegate to `HANDLERS.users`
- Refactor `api/schemas/competition.py` to remove direct ORM queries and `django_impl` imports
- Refactor `api/schemas/project.py` and `api/schemas/my_review.py` resolve methods to use service-layer data
- Add architectural documentation (ARCHITECTURE.md) capturing the service-layer rule and patterns

## Capabilities

### New Capabilities
- `competitions-service`: Service layer for competition queries (listing, detail, highlights with project counts)
- `tags-service`: Service layer for tag CRUD, public listing, and admin review operations
- `project-images-service`: Service layer for project image lifecycle (create, complete upload, delete, role management)
- `review-service`: Service layer for competition reviewer assignments, project rankings, and review status
- `service-layer-architecture-doc`: Documentation of the service-layer rule, patterns, and conventions

### Modified Capabilities

## Impact

- **API routers**: `competitions.py`, `my_review.py`, `tags.py`, `my_projects.py`, `auth.py`, `projects.py` — all lose direct model imports and ORM calls
- **API schemas**: `competition.py`, `project.py`, `my_review.py`, `user.py` — lose direct model/ORM usage
- **Async tasks**: `email.py` — loses direct `Model.objects.get()` calls
- **New files**: 4 new service module directories under `services/`, each with `handler_interface.py`, `query_interface.py`, `django_impl/handler.py`, `django_impl/query.py`
- **Registry**: `services/__init__.py` gains 4 new service registrations
- **No API contract changes**: endpoints, request/response shapes remain identical — this is an internal refactor