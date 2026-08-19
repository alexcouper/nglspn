# competition-lifecycle-dates Specification

## Purpose
TBD - created by syncing change competition-date-model-refactor. Update Purpose after archive.
## Requirements
### Requirement: Competition has distinct submission and voting deadlines

A Competition SHALL have a `submission_deadline` date field representing when project submissions close, and a `voting_end_date` nullable date field representing when voting ends and the competition closes.

#### Scenario: Competition with both dates set
- **WHEN** a competition has `submission_deadline` of 2026-03-15 and `voting_end_date` of 2026-03-31
- **THEN** the submission phase ends on 2026-03-15 and the voting phase ends on 2026-03-31

#### Scenario: Competition with no voting end date
- **WHEN** a competition has `submission_deadline` of 2026-03-15 and `voting_end_date` is null
- **THEN** the competition uses `submission_deadline` as the fallback for any voting-end calculations

### Requirement: Existing competitions backfill voting_end_date

All existing competitions SHALL have `voting_end_date` set to the value of their `submission_deadline` via a data migration.

#### Scenario: Migration of existing data
- **WHEN** the migration runs on a database with competitions that have `end_date` values
- **THEN** the field is renamed to `submission_deadline` and `voting_end_date` is set to the same value for every row

### Requirement: Context-aware deadline in API responses

All competition API response schemas that include date fields SHALL expose both `submission_deadline` and `voting_end_date` (where applicable). The former `end_date` field SHALL be renamed to `submission_deadline` across all response schemas.

#### Scenario: Competition summary includes both dates
- **WHEN** the API returns a competition summary
- **THEN** the response includes `submission_deadline` (string) and `voting_end_date` (string or null)

#### Scenario: Full competition response includes both dates
- **WHEN** the API returns a full competition response
- **THEN** the response includes `submission_deadline` and `voting_end_date` alongside `start_date`

### Requirement: Frontend displays context-aware days remaining

The frontend SHALL compute "days remaining" based on competition status:
- When status is `accepting_applications`: days until `submission_deadline`
- When status is `voting`: days until `voting_end_date` (falling back to `submission_deadline` if null)
- When status is `closed`: time elapsed since `voting_end_date` (falling back to `submission_deadline` if null)

#### Scenario: Days remaining during accepting applications
- **WHEN** a competition has status `accepting_applications` and `submission_deadline` is 5 days from now
- **THEN** the UI displays "5 days remaining"

#### Scenario: Days remaining during voting
- **WHEN** a competition has status `voting` and `voting_end_date` is 3 days from now
- **THEN** the UI displays "3 days remaining"

#### Scenario: Time since closed
- **WHEN** a competition has status `closed` and `voting_end_date` was 10 days ago
- **THEN** the UI displays "10d ago"

#### Scenario: Voting with null voting_end_date
- **WHEN** a competition has status `voting` and `voting_end_date` is null and `submission_deadline` is 2 days from now
- **THEN** the UI displays "2 days remaining" (falls back to `submission_deadline`)

### Requirement: Date range display uses submission_deadline

Wherever a competition's date range is displayed (e.g., "Jan 1, 2026 - Mar 15, 2026"), the range SHALL use `start_date` through `submission_deadline`.

#### Scenario: Competition detail page date range
- **WHEN** a competition has `start_date` of 2026-01-01 and `submission_deadline` of 2026-03-15
- **THEN** the date range displays "January 1, 2026 - March 15, 2026"

### Requirement: Competition records when winners were announced

A Competition SHALL record `winner_announced_at`, set the first time a `winner`
is assigned. The field is nullable: a competition with no winner has none.

Re-assigning the winner SHALL NOT move `winner_announced_at`. Clearing the
winner SHALL clear it, so that a later re-assignment records the new time.

Existing competitions SHALL be backfilled from `voting_end_date`, falling back to
`submission_deadline` where `voting_end_date` is null, and left null where the
competition has no winner.

This exists because winner assignment previously recorded no time at all — it
flipped `status` to `CLOSED` and nothing else — leaving the Latest feed with no
honest timestamp for the winners-announced event.

#### Scenario: Winner assigned for the first time
- **GIVEN** a competition with no winner
- **WHEN** a winner is assigned
- **THEN** `winner_announced_at` is set to the current time

#### Scenario: Winner re-assigned
- **GIVEN** a competition whose winner was announced last week
- **WHEN** the winner is changed to a different project
- **THEN** `winner_announced_at` is unchanged

#### Scenario: Winner cleared then re-assigned
- **GIVEN** a competition with a winner and `winner_announced_at` set
- **WHEN** the winner is cleared
- **THEN** `winner_announced_at` is null
- **AND** assigning a winner again sets it to the new current time

#### Scenario: Backfill of existing competitions
- **GIVEN** a closed competition with a winner, `voting_end_date` set, and no
  `winner_announced_at`
- **WHEN** the migration runs
- **THEN** `winner_announced_at` is set from `voting_end_date`

#### Scenario: Backfill without a voting end date
- **GIVEN** a closed competition with a winner, `voting_end_date` null, and
  `submission_deadline` set
- **WHEN** the migration runs
- **THEN** `winner_announced_at` is set from `submission_deadline`

#### Scenario: Competition with no winner
- **GIVEN** a competition with no winner
- **WHEN** the migration runs
- **THEN** `winner_announced_at` remains null

