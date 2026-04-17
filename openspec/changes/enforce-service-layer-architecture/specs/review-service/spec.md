## ADDED Requirements

### Requirement: Review query interface

The system SHALL provide a `ReviewQueryInterface` abstract base class in `services/review/query_interface.py` with the following methods:

- `list_reviewer_assignments(user_id)` — return all `CompetitionReviewer` assignments for the given user with competition relation prefetched
- `get_reviewer_assignment(user_id, competition_id)` — return the `CompetitionReviewer` for the given user and competition, or None if not found
- `get_competition_with_projects(competition_id)` — return a Competition with projects and project images prefetched; raise `CompetitionNotFoundError` if not found
- `get_reviewer_rankings(user_id, competition_id)` — return a dict mapping project_id to position for the given reviewer and competition
- `get_competition_project_ids(competition_id, excluded_statuses)` — return a set of project IDs belonging to the competition, excluding projects with the given statuses
- `get_review_project(user_id, project_id)` — return a Project with owner, tags, images, and won_competitions prefetched if the user is a reviewer for a competition containing the project and the project is not excluded; raise `ProjectNotFoundError` if not found or no access

#### Scenario: List reviewer assignments
- **WHEN** `list_reviewer_assignments(user_id)` is called
- **THEN** the system SHALL return all CompetitionReviewer instances for the user with competition relation selected

#### Scenario: Get reviewer assignment exists
- **WHEN** `get_reviewer_assignment(user_id, competition_id)` is called and the assignment exists
- **THEN** the system SHALL return the CompetitionReviewer instance

#### Scenario: Get reviewer assignment not found
- **WHEN** `get_reviewer_assignment(user_id, competition_id)` is called and no assignment exists
- **THEN** the system SHALL return None

#### Scenario: Get competition with projects
- **WHEN** `get_competition_with_projects(competition_id)` is called
- **THEN** the system SHALL return the Competition with projects and images prefetched

#### Scenario: Get reviewer rankings
- **WHEN** `get_reviewer_rankings(user_id, competition_id)` is called
- **THEN** the system SHALL return a dict mapping project IDs to ranking positions

#### Scenario: Get review project with access
- **WHEN** `get_review_project(user_id, project_id)` is called and the user is a reviewer for a competition containing the project
- **THEN** the system SHALL return the Project with owner, tags, images, and won_competitions prefetched

#### Scenario: Get review project without access
- **WHEN** `get_review_project(user_id, project_id)` is called and the user is not a reviewer for any competition containing the project
- **THEN** the system SHALL raise `ProjectNotFoundError`

### Requirement: Review handler interface

The system SHALL provide a `ReviewHandlerInterface` abstract base class in `services/review/handler_interface.py` with the following methods:

- `update_rankings(user_id, competition_id, project_ids)` — delete existing rankings for the reviewer/competition and bulk-create new ones with sequential positions; raise `ReviewNotFoundError` if no assignment exists; raise `ReviewAlreadyCompletedError` if the review is marked completed; raise `InvalidProjectIdsError` if any project_ids do not belong to the competition (after excluding rejected/ice-boxed projects)
- `update_review_status(user_id, competition_id, status)` — update the reviewer's status for the given competition; raise `ReviewNotFoundError` if no assignment exists

#### Scenario: Update rankings for valid review
- **WHEN** `update_rankings` is called with valid project IDs for an in-progress review
- **THEN** the system SHALL delete existing rankings and create new ones with positions 1..N

#### Scenario: Update rankings for completed review
- **WHEN** `update_rankings` is called for a review with COMPLETED status
- **THEN** the system SHALL raise `ReviewAlreadyCompletedError`

#### Scenario: Update rankings with invalid project IDs
- **WHEN** `update_rankings` is called with project IDs not in the competition
- **THEN** the system SHALL raise `InvalidProjectIdsError`

#### Scenario: Update review status
- **WHEN** `update_review_status` is called with a valid assignment
- **THEN** the system SHALL update the status field on the CompetitionReviewer record

#### Scenario: Update review status with no assignment
- **WHEN** `update_review_status` is called for a user/competition pair that has no assignment
- **THEN** the system SHALL raise `ReviewNotFoundError`

### Requirement: Django implementation of review services

The system SHALL provide `DjangoReviewQuery` and `DjangoReviewHandler` in `services/review/django_impl/` implementing `ReviewQueryInterface` and `ReviewHandlerInterface` respectively. They SHALL be registered in `QueryServices` as `REPO.review` and `HandlerServices` as `HANDLERS.review`.

#### Scenario: DjangoReviewQuery uses Django ORM
- **WHEN** any `ReviewQueryInterface` method is called via `REPO.review`
- **THEN** the system SHALL use Django ORM queries to fulfill the request

#### Scenario: DjangoReviewHandler uses Django ORM
- **WHEN** any `ReviewHandlerInterface` method is called via `HANDLERS.review`
- **THEN** the system SHALL use Django ORM to create, update, or delete review data

### Requirement: My review router uses service layer

The API router `api/routers/my_review.py` SHALL NOT import from `apps.projects.models` directly. All database queries and mutations SHALL be delegated to `REPO.review`, `HANDLERS.review`, `REPO.competitions`, and `REPO.project`.

#### Scenario: List review competitions endpoint uses service layer
- **WHEN** the list review competitions endpoint is called
- **THEN** it SHALL call `REPO.review.list_reviewer_assignments()` instead of `CompetitionReviewer.objects.filter()`

#### Scenario: Get review competition detail endpoint uses service layer
- **WHEN** the get review competition detail endpoint is called
- **THEN** it SHALL call `REPO.review.get_reviewer_assignment()` and `REPO.review.get_competition_with_projects()` and `REPO.review.get_reviewer_rankings()` instead of direct ORM queries

#### Scenario: Update rankings endpoint uses service layer
- **WHEN** the update rankings endpoint is called
- **THEN** it SHALL call `HANDLERS.review.update_rankings()` instead of `ProjectRanking.objects.filter().delete()` and `ProjectRanking.objects.bulk_create()`

#### Scenario: Update review status endpoint uses service layer
- **WHEN** the update review status endpoint is called
- **THEN** it SHALL call `HANDLERS.review.update_review_status()` instead of `CompetitionReviewer.objects.filter().update()`

#### Scenario: Get review project endpoint uses service layer
- **WHEN** the get review project endpoint is called
- **THEN** it SHALL call `REPO.review.get_review_project()` instead of `CompetitionReviewer.objects.filter().exists()` and `Project.objects.select_related().prefetch_related().get()`