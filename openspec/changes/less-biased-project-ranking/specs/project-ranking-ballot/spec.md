## ADDED Requirements

### Requirement: Projects start unranked

A reviewer's ballot SHALL begin empty. No project is assigned a position until the reviewer explicitly adds it. The system SHALL NOT seed a ballot from any default ordering.

#### Scenario: First visit to a competition with no saved ballot

- **WHEN** a reviewer opens a competition they have never ranked
- **THEN** the ranked list is empty
- **AND** every eligible project appears in the unranked pool

#### Scenario: Returning to a partially ranked competition

- **WHEN** a reviewer who previously ranked 2 of 8 projects reopens the competition
- **THEN** those 2 projects appear in the ranked list in their saved positions
- **AND** the other 6 appear in the unranked pool

### Requirement: Reviewer adds a project to their ranking

The system SHALL let a reviewer move any unranked project into their ranked list. The added project SHALL be appended below all currently ranked projects.

#### Scenario: Adding the first project

- **WHEN** a reviewer adds a project from the pool to an empty ranking
- **THEN** that project occupies position 1
- **AND** it no longer appears in the unranked pool

#### Scenario: Adding to a non-empty ranking

- **GIVEN** a reviewer has 2 projects ranked
- **WHEN** they add a third from the pool
- **THEN** it occupies position 3
- **AND** the existing positions 1 and 2 are unchanged

#### Scenario: Adding does not change the active view on mobile

- **GIVEN** a reviewer is viewing the pool tab on a small screen
- **WHEN** they add a project
- **THEN** the pool tab remains active
- **AND** the ranked-list tab's count indicator increases by one

### Requirement: Reviewer removes a project from their ranking

The system SHALL let a reviewer remove any ranked project. Remaining ranked projects SHALL close the gap so positions stay contiguous from 1.

#### Scenario: Removing a middle entry

- **GIVEN** a reviewer has projects A, B, C at positions 1, 2, 3
- **WHEN** they remove B
- **THEN** A is at position 1 and C is at position 2
- **AND** B returns to the unranked pool at its stable pool position

### Requirement: Reviewer reorders ranked projects

The system SHALL let a reviewer change the order of ranked projects by drag-and-drop and by up/down controls. Reordering SHALL affect only the ranked list.

#### Scenario: Moving a project up

- **GIVEN** a reviewer has projects A, B, C at positions 1, 2, 3
- **WHEN** they move C up one place
- **THEN** the order is A, C, B

#### Scenario: Keyboard reordering is available

- **WHEN** a reviewer focuses a ranked project's up or down control and activates it
- **THEN** the project moves one position in that direction

### Requirement: Unranked pool has a stable per-reviewer order

The unranked pool SHALL be ordered by a deterministic function of the reviewer, the competition, and the project, so that the order is stable for a given reviewer across reloads and devices, and uncorrelated between reviewers. The system SHALL NOT order the pool by project creation date or any other ordering shared across reviewers.

#### Scenario: Order is stable for one reviewer

- **WHEN** the same reviewer loads the same competition twice
- **THEN** the unranked pool is in the same order both times

#### Scenario: Order differs between reviewers

- **WHEN** two different reviewers load the same competition
- **THEN** their unranked pools are in different orders

#### Scenario: Order is independent of creation date

- **WHEN** a new project is added to a competition
- **THEN** it does not systematically appear at the top of any reviewer's pool

### Requirement: Ballot size is unconstrained

The system SHALL NOT impose a minimum or maximum number of ranked projects. A reviewer MAY rank one project, all projects, or none.

#### Scenario: Ranking a single project

- **WHEN** a reviewer ranks exactly one project and submits
- **THEN** the submission is accepted

#### Scenario: Ranking every project

- **WHEN** a reviewer ranks all 8 projects and submits
- **THEN** the submission is accepted

### Requirement: An empty ballot is a valid abstention

The system SHALL accept a submission with no ranked projects, but SHALL require explicit confirmation before submitting one.

#### Scenario: Submitting with nothing ranked

- **GIVEN** a reviewer has ranked no projects
- **WHEN** they choose to submit
- **THEN** a confirmation explains that no projects will be ranked
- **AND** the review is marked completed only after they confirm

#### Scenario: Cancelling an empty submission

- **WHEN** a reviewer cancels the empty-ballot confirmation
- **THEN** the review status is unchanged

### Requirement: Submission persists only ranked projects

`PUT /api/my/reviews/competitions/{id}/rankings` SHALL store one `ProjectRanking` row per submitted project, with positions numbered contiguously from 1 in payload order. Projects absent from the payload SHALL have no row.

#### Scenario: Partial ballot persisted

- **WHEN** a reviewer submits 2 project IDs for a competition with 8 projects
- **THEN** exactly 2 `ProjectRanking` rows exist for that reviewer and competition
- **AND** their positions are 1 and 2

#### Scenario: Empty payload clears the ballot

- **GIVEN** a reviewer has a saved ballot
- **WHEN** they submit an empty list of project IDs
- **THEN** no `ProjectRanking` rows remain for that reviewer and competition

### Requirement: Ballot writes are atomic

Replacing a ballot SHALL be atomic. A failure part-way through SHALL leave the reviewer's previously saved ballot intact.

#### Scenario: Write failure preserves the previous ballot

- **GIVEN** a reviewer has a saved ballot of 3 projects
- **WHEN** a submission fails while writing the replacement
- **THEN** the reviewer's original 3 rankings are still present

### Requirement: Duplicate project IDs are rejected

The system SHALL reject a submission containing the same project ID more than once with a 400 response, without modifying the stored ballot.

#### Scenario: Repeated ID in payload

- **WHEN** a reviewer submits a payload listing the same project twice
- **THEN** the response is 400 with a message identifying the duplicate
- **AND** the reviewer's existing ballot is unchanged

### Requirement: Ranking updates are blocked for closed reviews

The system SHALL reject ranking updates when the reviewer's `CompetitionReviewer.status` is `completed` or `ended`.

#### Scenario: Update after submitting

- **GIVEN** a reviewer's review status is `completed`
- **WHEN** they submit a ranking update
- **THEN** the response is 400

#### Scenario: Update after an admin ends the review period

- **GIVEN** a reviewer's review status is `ended`
- **WHEN** they submit a ranking update
- **THEN** the response is 400

### Requirement: Pending ballot changes are saved before submission

The client SHALL flush any pending debounced ranking save before requesting the status change to `completed`, so that a change made immediately before submitting is not lost.

#### Scenario: Reorder then immediately submit

- **WHEN** a reviewer reorders their ranking and submits before the autosave interval elapses
- **THEN** the reordered ballot is persisted
- **AND** the review is marked completed

### Requirement: Ranked list and pool adapt to screen size

The ranked list and the unranked pool SHALL both be reachable at every screen size: presented side by side on wide screens and as two switchable tabs on narrow screens.

#### Scenario: Wide screen

- **WHEN** a reviewer views the competition on a wide screen
- **THEN** the ranked list and unranked pool are both visible at once

#### Scenario: Narrow screen

- **WHEN** a reviewer views the competition on a narrow screen
- **THEN** a tab control switches between the ranked list and the unranked pool
- **AND** the ranked-list tab shows how many projects are ranked
