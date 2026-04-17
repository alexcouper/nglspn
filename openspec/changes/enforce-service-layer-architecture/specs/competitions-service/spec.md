## ADDED Requirements

### Requirement: Competitions query interface

The system SHALL provide a `CompetitionQueryInterface` abstract base class in `services/competitions/query_interface.py` with the following methods:

- `list_all()` — return all competitions with prefetched projects
- `list_with_projects()` — return all competitions with prefetched projects, images, tags, and winner relations
- `get_by_id_or_slug(identifier)` — return a single competition by UUID or slug, with projects, images, tags, and winner relations; raise `CompetitionNotFoundError` if not found
- `list_highlights()` — return active competitions (status ACCEPTING_APPLICATIONS or VOTING) ordered by start date descending, plus the most recent CLOSED competition, each annotated with project count
- `count_pending_projects()` — return the count of projects with PENDING status

#### Scenario: List all competitions
- **WHEN** `list_all()` is called
- **THEN** the system SHALL return all `Competition` instances with projects prefetched

#### Scenario: List competitions with full relations
- **WHEN** `list_with_projects()` is called
- **THEN** the system SHALL return all `Competition` instances with projects, project images, project tags, winner, winner images, and winner tags prefetched

#### Scenario: Get competition by UUID
- **WHEN** `get_by_id_or_slug` is called with a valid UUID string
- **THEN** the system SHALL return the competition matching that UUID with full relations prefetched

#### Scenario: Get competition by slug
- **WHEN** `get_by_id_or_slug` is called with a non-UUID string
- **THEN** the system SHALL return the competition matching that slug with full relations prefetched

#### Scenario: Competition not found
- **WHEN** `get_by_id_or_slug` is called with an identifier that matches no competition
- **THEN** the system SHALL raise `CompetitionNotFoundError`

#### Scenario: List highlights with active and recent closed
- **WHEN** `list_highlights()` is called
- **THEN** the system SHALL return competitions with status ACCEPTING_APPLICATIONS or VOTING ordered by start date descending, plus at most one CLOSED competition ordered by voting end date and submission deadline descending, each annotated with `project_count`

#### Scenario: Count pending projects
- **WHEN** `count_pending_projects()` is called
- **THEN** the system SHALL return the integer count of projects with PENDING status

### Requirement: Django implementation of competitions query

The system SHALL provide `DjangoCompetitionQuery` in `services/competitions/django_impl/query.py` implementing `CompetitionQueryInterface` using Django ORM. It SHALL be registered in `QueryServices` as `REPO.competitions`.

#### Scenario: DjangoCompetitionQuery uses Django ORM
- **WHEN** any `CompetitionQueryInterface` method is called via `REPO.competitions`
- **THEN** the system SHALL use Django ORM queries to fulfill the request, encapsulating all database access within the implementation

### Requirement: Competitions router uses service layer

The API router `api/routers/competitions.py` SHALL NOT import from `apps.projects.models` directly. All database queries SHALL be delegated to `REPO.competitions`.

#### Scenario: List competitions endpoint uses service layer
- **WHEN** the list competitions endpoint is called
- **THEN** it SHALL call `REPO.competitions.list_all()` and `REPO.competitions.count_pending_projects()` instead of `Competition.objects` and `Project.objects`

#### Scenario: List competitions with projects endpoint uses service layer
- **WHEN** the list competitions with projects endpoint is called
- **THEN** it SHALL call `REPO.competitions.list_with_projects()` and `REPO.competitions.count_pending_projects()` instead of `Competition.objects` and `Project.objects`

#### Scenario: Get highlights endpoint uses service layer
- **WHEN** the get highlights endpoint is called
- **THEN** it SHALL call `REPO.competitions.list_highlights()` instead of `Competition.objects.annotate()`

#### Scenario: Get competition detail endpoint uses service layer
- **WHEN** the get competition detail endpoint is called
- **THEN** it SHALL call `REPO.competitions.get_by_id_or_slug()` instead of `Competition.objects` and `get_object_or_404`

### Requirement: Competition schema does not query the database

The schema class `CompetitionResponse` in `api/schemas/competition.py` SHALL NOT perform database queries. Its `from_competition` method SHALL accept pre-fetched data. The import of `to_list_item` from `services.project.django_impl` SHALL be removed.

#### Scenario: CompetitionResponse receives pre-computed data
- **WHEN** `CompetitionResponse.from_competition` is called
- **THEN** all project data, counts, and winner data SHALL already be computed by the service layer before being passed to the schema
- **AND** the schema SHALL NOT call `.filter()`, `.count()`, `.prefetch_related()`, or any other ORM method

#### Scenario: No direct import from django_impl
- **WHEN** the competition schema module is loaded
- **THEN** it SHALL NOT import from `services.project.django_impl`