## ADDED Requirements

### Requirement: Tags query interface

The system SHALL provide a `TagQueryInterface` abstract base class in `services/tags/query_interface.py` with the following methods:

- `list_non_rejected()` — return a QuerySet of tags excluding those with REJECTED status
- `list_categories()` — return a QuerySet of active tag categories
- `list_grouped(with_projects)` — return tags grouped by active category, optionally filtered to only tags with at least one APPROVED project
- `list_pending()` — return tags with PENDING status with their category prefetched
- `get_by_id(tag_id)` — return a single tag with category prefetched; raise `TagNotFoundError` if not found

#### Scenario: List non-rejected tags
- **WHEN** `list_non_rejected()` is called
- **THEN** the system SHALL return a QuerySet of tags where status is not REJECTED

#### Scenario: List active categories
- **WHEN** `list_categories()` is called
- **THEN** the system SHALL return a QuerySet of tag categories where `is_active=True`

#### Scenario: List grouped tags without project filter
- **WHEN** `list_grouped(with_projects=False)` is called
- **THEN** the system SHALL return categories with their non-rejected tags prefetched

#### Scenario: List grouped tags with project filter
- **WHEN** `list_grouped(with_projects=True)` is called
- **THEN** the system SHALL return categories with tags that have at least one APPROVED project, excluding REJECTED tags, deduplicated

#### Scenario: List pending tags
- **WHEN** `list_pending()` is called
- **THEN** the system SHALL return tags with PENDING status with their category selected/prefetched

#### Scenario: Get tag by ID
- **WHEN** `get_by_id(tag_id)` is called with an existing tag ID
- **THEN** the system SHALL return the tag with category prefetched

#### Scenario: Tag not found
- **WHEN** `get_by_id(tag_id)` is called with a non-existent tag ID
- **THEN** the system SHALL raise `TagNotFoundError`

### Requirement: Tags handler interface

The system SHALL provide a `TagHandlerInterface` abstract base class in `services/tags/handler_interface.py` with the following methods:

- `suggest(name, slug, description, color, category_id, created_by)` — validate category exists and is active, check for duplicate name/slug, create tag with PENDING status; raise `DuplicateTagNameError` or `DuplicateTagSlugError` on conflicts; raise `TagCategoryNotFoundError` if category is invalid
- `approve(tag_id, reviewed_by)` — set tag status to APPROVED, set reviewed_by and reviewed_at; raise `TagNotFoundError` if not found; raise `TagAlreadyApprovedError` if already approved; raise `TagRejectedError` if tag is rejected
- `reject(tag_id, reviewed_by)` — remove tag from all projects, set status to REJECTED, set reviewed_by and reviewed_at; raise `TagNotFoundError` if not found; raise `TagAlreadyRejectedError` if already rejected

#### Scenario: Suggest a new tag
- **WHEN** `suggest` is called with valid data
- **THEN** the system SHALL create a tag with PENDING status and return the created tag

#### Scenario: Suggest tag with duplicate name
- **WHEN** `suggest` is called with a name that already exists (case-insensitive)
- **THEN** the system SHALL raise `DuplicateTagNameError`

#### Scenario: Suggest tag with duplicate slug
- **WHEN** `suggest` is called and a tag with the same slug already exists
- **THEN** the system SHALL raise `DuplicateTagSlugError`

#### Scenario: Suggest tag with inactive category
- **WHEN** `suggest` is called with a category ID that does not exist or is inactive
- **THEN** the system SHALL raise `TagCategoryNotFoundError`

#### Scenario: Approve a pending tag
- **WHEN** `approve` is called on a PENDING tag
- **THEN** the system SHALL set status to APPROVED, set reviewed_by and reviewed_at, and return the tag

#### Scenario: Approve an already approved tag
- **WHEN** `approve` is called on an APPROVED tag
- **THEN** the system SHALL raise `TagAlreadyApprovedError`

#### Scenario: Approve a rejected tag
- **WHEN** `approve` is called on a REJECTED tag
- **THEN** the system SHALL raise `TagRejectedError`

#### Scenario: Reject a tag
- **WHEN** `reject` is called on a tag
- **THEN** the system SHALL remove the tag from all projects, set status to REJECTED, set reviewed_by and reviewed_at

#### Scenario: Reject an already rejected tag
- **WHEN** `reject` is called on a REJECTED tag
- **THEN** the system SHALL raise `TagAlreadyRejectedError`

### Requirement: Django implementation of tags services

The system SHALL provide `DjangoTagQuery` and `DjangoTagHandler` in `services/tags/django_impl/` implementing `TagQueryInterface` and `TagHandlerInterface` respectively using Django ORM. They SHALL be registered in `QueryServices` as `REPO.tags` and `HandlerServices` as `HANDLERS.tags`.

#### Scenario: DjangoTagQuery uses Django ORM
- **WHEN** any `TagQueryInterface` method is called via `REPO.tags`
- **THEN** the system SHALL use Django ORM queries to fulfill the request

#### Scenario: DjangoTagHandler uses Django ORM
- **WHEN** any `TagHandlerInterface` method is called via `HANDLERS.tags`
- **THEN** the system SHALL use Django ORM to create, update, or delete tags

### Requirement: Tags router uses service layer

The API router `api/routers/tags.py` SHALL NOT import from `apps.tags.models` or `apps.projects.models` directly. All database queries and mutations SHALL be delegated to `REPO.tags` and `HANDLERS.tags`.

#### Scenario: List tags endpoint uses service layer
- **WHEN** the list tags endpoint is called
- **THEN** it SHALL call `REPO.tags.list_non_rejected()` instead of `Tag.objects.exclude()`

#### Scenario: List categories endpoint uses service layer
- **WHEN** the list categories endpoint is called
- **THEN** it SHALL call `REPO.tags.list_categories()` instead of `TagCategory.objects.filter()`

#### Scenario: List grouped tags endpoint uses service layer
- **WHEN** the list grouped tags endpoint is called
- **THEN** it SHALL call `REPO.tags.list_grouped(with_projects)` instead of direct ORM queries

#### Scenario: Suggest tag endpoint uses service layer
- **WHEN** the suggest tag endpoint is called
- **THEN** it SHALL call `HANDLERS.tags.suggest()` instead of `Tag.objects.create()` and direct validation queries

#### Scenario: List pending tags endpoint uses service layer
- **WHEN** the list pending tags endpoint is called
- **THEN** it SHALL call `REPO.tags.list_pending()` instead of `Tag.objects.filter()`

#### Scenario: Approve tag endpoint uses service layer
- **WHEN** the approve tag endpoint is called
- **THEN** it SHALL call `HANDLERS.tags.approve()` instead of directly modifying and saving the tag model

#### Scenario: Reject tag endpoint uses service layer
- **WHEN** the reject tag endpoint is called
- **THEN** it SHALL call `HANDLERS.tags.reject()` instead of directly modifying, clearing relations, and saving the tag model