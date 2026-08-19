## ADDED Requirements

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
