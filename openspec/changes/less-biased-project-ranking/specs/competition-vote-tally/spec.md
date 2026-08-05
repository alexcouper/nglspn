## ADDED Requirements

### Requirement: Ballots reduce to pairwise preferences

Each ballot SHALL be reduced to a set of pairwise preferences. A ranked project SHALL be counted as preferred over every project ranked below it and over every project the reviewer left unranked. Two projects both left unranked SHALL contribute nothing for that ballot.

#### Scenario: Full ballot

- **GIVEN** a competition with projects A, B, C
- **WHEN** a reviewer submits the ballot [A, B, C]
- **THEN** the ballot contributes A over B, A over C, and B over C

#### Scenario: Partial ballot

- **GIVEN** a competition with projects A, B, C, D
- **WHEN** a reviewer submits the ballot [C, A]
- **THEN** the ballot contributes C over A, C over B, C over D, A over B, and A over D
- **AND** it contributes nothing between B and D

#### Scenario: Empty ballot

- **WHEN** a reviewer submits an empty ballot
- **THEN** the ballot contributes no pairwise preferences

### Requirement: Truncating a ballot does not alter expressed preferences

Omitting lower-preference projects from a ballot SHALL NOT change any pairwise comparison between projects the reviewer did rank. This is the property that makes a partial ballot safe to submit.

#### Scenario: Shortening a ballot leaves ranked comparisons intact

- **GIVEN** a reviewer whose ballot is [A, B, C, D]
- **WHEN** the same reviewer instead submits [A, B]
- **THEN** the contribution to A over B is identical in both cases

#### Scenario: Ranking one project only

- **GIVEN** a competition with projects A through H
- **WHEN** a reviewer submits the ballot [A]
- **THEN** A is preferred over each of B through H
- **AND** no preference is recorded between any pair drawn from B through H

### Requirement: Only completed reviews are counted

The tally SHALL include ballots only from reviewers whose `CompetitionReviewer.status` is `completed`. Ballots from reviewers in `in_progress` or `ended` status SHALL be excluded.

#### Scenario: In-progress reviewer excluded

- **GIVEN** a reviewer with a saved ballot and status `in_progress`
- **WHEN** the tally is computed
- **THEN** their preferences do not appear in the pairwise matrix

#### Scenario: Ended reviewer excluded

- **GIVEN** a reviewer with a saved ballot and status `ended`
- **WHEN** the tally is computed
- **THEN** their preferences do not appear in the pairwise matrix

### Requirement: Ineligible projects are excluded from the tally

Projects with status `rejected` or `ice_box` SHALL be excluded from the tally entirely, including from the pairwise matrix, even if a stored ballot references them.

#### Scenario: Ballot references a rejected project

- **GIVEN** a ballot [A, R, B] where R was subsequently rejected
- **WHEN** the tally is computed
- **THEN** R appears nowhere in the results
- **AND** the ballot still contributes A over B

### Requirement: Pairwise results are recorded as margins

For each ordered pair of projects, the system SHALL record the number of counted ballots preferring the first over the second. The margin between two projects SHALL be the difference between the two opposing counts.

#### Scenario: Computing a margin

- **GIVEN** 9 ballots prefer A over B and 3 prefer B over A
- **WHEN** the tally is computed
- **THEN** the margin of A over B is 6
- **AND** the margin of B over A is -6

#### Scenario: A pair nobody compared

- **GIVEN** no counted ballot ranks either A or B
- **WHEN** the tally is computed
- **THEN** the margin between A and B is 0

### Requirement: Final ordering is computed by the Schulze method

The system SHALL order projects using the Schulze method over the pairwise margin matrix: strongest-path strengths SHALL be computed between every pair, and a project SHALL be ordered above another when its strongest path to that project is stronger than the reverse.

#### Scenario: Condorcet winner is ranked first

- **GIVEN** one project beats every other project head to head
- **WHEN** the tally is computed
- **THEN** that project is ranked first

#### Scenario: Cyclic result is resolved

- **GIVEN** A beats B by 8, B beats C by 6, and C beats A by 4
- **WHEN** the tally is computed
- **THEN** the ordering is A, then B, then C

#### Scenario: Genuine tie shares a rank

- **GIVEN** two projects whose strongest paths to each other are equal
- **WHEN** the tally is computed
- **THEN** they are displayed at the same rank

### Requirement: The ordering rule is defined behind an interface

Ordering SHALL be expressed as a named interface taking a pairwise margin matrix and returning ranked tiers, with the Schulze implementation as one conforming member. Ballot reduction SHALL NOT depend on any concrete ordering rule.

Adopting a different rule remains a change to this specification, because the ordering below the winner is observable. The interface exists so that such a change is confined to one implementation, not so that the rule is unspecified.

#### Scenario: Ballot reduction is independent of ordering

- **WHEN** ballot reduction is exercised
- **THEN** it produces a complete pairwise margin matrix without invoking any ordering rule

#### Scenario: Ordering is exercised without ballots

- **WHEN** an ordering rule is given a pairwise margin matrix directly
- **THEN** it returns ranked tiers without reference to ballots, reviewers or competitions

#### Scenario: Tied projects share a tier

- **GIVEN** two projects the ordering rule cannot separate
- **WHEN** ordering is computed
- **THEN** both appear in the same tier of the returned result

### Requirement: Results view shows support signals alongside the ordering

The competition results view SHALL present, for every eligible project: its computed rank, how many counted ballots placed it first, how many counted ballots ranked it at all, its mean position among ballots that ranked it, and the pairwise grid of margins against every other project.

#### Scenario: Thin support is visible

- **GIVEN** a project ranked by only 2 of 15 counted reviewers
- **WHEN** an admin views the results
- **THEN** the view shows that 2 of 15 reviewers ranked it

#### Scenario: Pairwise grid rendered

- **WHEN** an admin views the results for a competition with 8 eligible projects
- **THEN** the view shows the margin for every ordered pair of those projects

#### Scenario: No counted ballots

- **GIVEN** a competition where no reviewer has completed their review
- **WHEN** an admin views the results
- **THEN** the view reports that there are no counted ballots rather than an ordering

### Requirement: The tally is advisory

Computing the tally SHALL NOT set `Competition.winner` or change competition status. Selecting a winner remains a manual admin action.

#### Scenario: Viewing results does not pick a winner

- **GIVEN** a competition with a clear Schulze winner and no winner set
- **WHEN** an admin views the results
- **THEN** `Competition.winner` is still unset

### Requirement: Results view is restricted to staff

The competition results view SHALL be accessible only to staff users.

#### Scenario: Non-staff access

- **WHEN** a non-staff user requests the results view
- **THEN** access is denied
