## ADDED Requirements

### Requirement: Discussion count annotation for project queries

The system SHALL support annotating project querysets with a top-level discussion count using `Count('discussions', filter=Q(discussions__parent__isnull=True))`. This annotation SHALL be used by the most-discussed endpoint and category view sort. Only top-level discussions (parent is null) SHALL be counted — replies are excluded.

#### Scenario: Project with discussions and replies
- **WHEN** a project has 3 top-level discussions and 7 replies across them
- **THEN** the discussion_count annotation returns 3

#### Scenario: Project with no discussions
- **WHEN** a project has no discussions
- **THEN** the discussion_count annotation returns 0

#### Scenario: Discussion count used in most-discussed sort
- **WHEN** the most-discussed endpoint queries projects
- **THEN** projects are annotated with discussion_count and ordered by it descending
