# Architecture: Service Layer

## The Rule

The API layer (routers, schemas, async tasks) **MUST NOT** directly access the database via Django ORM. All database access **MUST** go through service interfaces (`HANDLERS` and `REPO`).

This means:
- No `Model.objects.get()`, `.filter()`, `.create()`, `.save()`, `.delete()` in routers, schemas, or tasks
- No `get_object_or_404()` with model classes in routers
- No `from apps.*.models import ...` in routers or schemas (for the purpose of DB queries)
- No schema `resolve_*` methods that call `.filter()`, `.exclude()`, or other ORM query methods

## Why

We're building a monolith now, but we want the option to extract domains into separate services later. By keeping all database access behind interfaces, each domain's data access is encapsulated and can be moved with its tables intact.

## The Pattern

Each domain has a service module under `services/` with this structure:

```
services/<domain>/
├── __init__.py
├── exceptions.py              # Domain-specific exceptions
├── handler_interface.py       # ABC for write operations
├── query_interface.py         # ABC for read operations
└── django_impl/
    ├── __init__.py
    ├── handler.py             # Django ORM implementation of handler
    └── query.py               # Django ORM implementation of query
```

### Interfaces

- **`handler_interface.py`**: Abstract base class defining write operations (create, update, delete)
- **`query_interface.py`**: Abstract base class defining read operations (get, list, count)
- Use dataclass DTOs for complex return types (e.g., `ProjectListItem`, `CompetitionDetailItem`)
- Return model instances for simple single-object lookups

### Implementations

- **`django_impl/handler.py`**: Concrete implementation using Django ORM
- **`django_impl/query.py`**: Concrete implementation using Django ORM
- This is the **only** place Django ORM code should live for this domain

### Registration

All services are registered centrally in `services/__init__.py`:

```python
HANDLERS = HandlerServices()  # Write operations
REPO = QueryServices()          # Read operations
```

Routers import and use:
```python
from services import HANDLERS, REPO

# Reads
project = REPO.project.get_by_id(project_id)
items = REPO.competitions.list_highlights()

# Writes
project = HANDLERS.project.create(data)
HANDLERS.tags.approve(tag_id, reviewer_id)
```

## Service Domains

| Domain | Handler | Query | Description |
|--------|---------|-------|-------------|
| competitions | - | `REPO.competitions` | Competition listing, detail, highlights |
| discussions | `HANDLERS.discussions` | `REPO.discussions` | Discussion CRUD |
| email | `HANDLERS.email` | `REPO.email` | Email sending, broadcast rendering |
| image | `HANDLERS.image` | - | Image variant generation |
| notifications | `HANDLERS.notifications` | - | Notification batching |
| project | `HANDLERS.project` | `REPO.project` | Project CRUD, discovery listings |
| project_images | `HANDLERS.project_images` | `REPO.project_images` | Image upload, roles, deletion |
| registration | `HANDLERS.registration` | - | User registration, onboarding |
| review | `HANDLERS.review` | `REPO.review` | Competition review, rankings |
| tags | `HANDLERS.tags` | `REPO.tags` | Tag CRUD, admin review |
| users | `HANDLERS.users` | `REPO.users` | User profile, verification, password reset |

## Correct vs Incorrect

### Incorrect - Direct ORM in router

```python
# DON'T
from apps.projects.models import Competition, ProjectStatus

def list_competitions(request):
    competitions = Competition.objects.prefetch_related("projects").all()
    pending = Project.objects.filter(status=ProjectStatus.PENDING).count()
```

### Correct - Service layer in router

```python
# DO
from services import REPO

def list_competitions(request):
    items = REPO.competitions.list_all()
    pending = REPO.competitions.count_pending_projects()
```

### Incorrect - Direct ORM in schema

```python
# DON'T
class ProjectResponse(Schema):
    @staticmethod
    def resolve_tags(obj):
        return list(obj.tags.exclude(status="rejected"))
```

### Correct - Use prefetch cache with Python filtering

```python
# DO
class ProjectResponse(Schema):
    @staticmethod
    def resolve_tags(obj):
        return [t for t in obj.tags.all() if t.status != "rejected"]
```

### Incorrect - Direct ORM in async task

```python
# DON'T
from apps.users.models import User
from apps.projects.models import Project

def send_email(project_id):
    project = Project.objects.select_related("owner").get(id=project_id)
```

### Correct - Service layer in async task

```python
# DO
from services import REPO

def send_email(project_id):
    project = REPO.project.get_by_id(project_id)
```

## Exceptions

When a service operation can fail in expected ways, define domain-specific exceptions in `services/<domain>/exceptions.py`. Routers catch these and return appropriate HTTP responses.

```python
# services/review/exceptions.py
class ReviewNotFoundError(Exception):
    pass

class ReviewAlreadyCompletedError(Exception):
    pass

# api/routers/my_review.py
try:
    HANDLERS.review.update_rankings(...)
except ReviewNotFoundError:
    return 404, Error(detail="Not found")
except ReviewAlreadyCompletedError:
    return 400, Error(detail="Already completed")
```

## Adding a New Service

1. Create `services/<domain>/` with `__init__.py` and `exceptions.py`
2. Define `handler_interface.py` (ABC) and/or `query_interface.py` (ABC)
3. Implement `django_impl/handler.py` and/or `django_impl/query.py`
4. Register in `services/__init__.py` as both `HANDLERS.<domain>` and `REPO.<domain>`
5. Refactor routers to use the new service instead of direct ORM
6. Write tests for the Django implementations
