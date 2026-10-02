# competition-reviewer-groups Specification

## Purpose
Decides who may review a competition and when. Access comes from the competition's status and its reviewer group, never from a per-user assignment, and a review record exists only once a user has started reviewing.

## Requirements
### Requirement: Reviewer groups are named sets of users

The system SHALL persist reviewer groups, each with a unique name, an `includes_all_users` flag and an explicit member list. The members of a group with `includes_all_users = True` SHALL be every user; its explicit member list SHALL be ignored. The members of any other group SHALL be its explicit member list. The change SHALL ship the migrations that add the model.

#### Scenario: Model and migration are in step
- **WHEN** `manage.py makemigrations --check --dry-run` runs after the change
- **THEN** it reports no missing migrations

#### Scenario: Panel membership is explicit
- **GIVEN** a group "Judges" with `includes_all_users = False` and members A and B
- **WHEN** a user C, who is not a member, is checked against it
- **THEN** A and B are members and C is not

### Requirement: An "Everyone" group exists and cannot be removed

A data migration SHALL create a reviewer group named "Everyone" with `includes_all_users = True`. The Django admin SHALL NOT allow the Everyone group to be deleted. A reviewer group that any competition references SHALL NOT be deletable.

#### Scenario: Everyone is seeded
- **WHEN** migrations have run on an empty database
- **THEN** exactly one reviewer group named "Everyone" exists, with `includes_all_users = True`

#### Scenario: A referenced group is protected
- **GIVEN** a competition whose reviewer group is "Judges"
- **WHEN** "Judges" is deleted
- **THEN** the deletion is refused and the group remains

### Requirement: Every competition has a reviewer group, defaulting to Everyone

Every competition SHALL reference exactly one reviewer group. A competition created without one SHALL get Everyone. The migration SHALL set every existing competition to Everyone. The Django admin competition form SHALL show the reviewer group and allow it to be changed.

#### Scenario: New competition defaults to Everyone
- **WHEN** a competition is created without a reviewer group
- **THEN** its reviewer group is Everyone

#### Scenario: Existing competitions are backfilled
- **GIVEN** competitions that exist before the migration
- **WHEN** the migration runs
- **THEN** each of them has Everyone as its reviewer group

### Requirement: Review access is derived from the competition

A user SHALL be able to review a competition when all of these hold: the competition's status is `voting`; the user is active and not a system user; and the user is a member of the competition's reviewer group. No stored per-user record SHALL grant or deny access. While access holds, the user SHALL be able to list the competition, open its ballot, view its projects, save rankings and set their review status.

#### Scenario: A newly registered user can review an open competition
- **GIVEN** a competition in `voting` whose reviewer group is Everyone
- **AND** a user who registered after the competition moved to `voting`
- **WHEN** the user lists their review competitions
- **THEN** the competition is listed with `my_review_status` `in_progress`

#### Scenario: Panel competitions admit only the panel
- **GIVEN** a competition in `voting` whose reviewer group is "Judges", and a user C who is not a member of "Judges"
- **WHEN** C opens the competition's ballot
- **THEN** the response is 404

#### Scenario: Inactive and system users have no access
- **GIVEN** a competition in `voting` whose reviewer group is Everyone
- **WHEN** a system user, or a user with `is_active = False`, asks for its ballot
- **THEN** access is refused

#### Scenario: Competitions not yet voting are not reviewable
- **GIVEN** a competition in `pending` or `accepting_applications` whose reviewer group is Everyone
- **WHEN** a user with no review record for it lists their review competitions, opens its ballot, or saves rankings for it
- **THEN** it is not listed, and the ballot and the save both return 404

### Requirement: Reviewing closes when the competition leaves voting

Once a competition's status is anything other than `voting`, whether it was changed by hand or set to `closed` by assigning a winner, the system SHALL refuse to save rankings or change review status for it. A user who has a review record for the competition SHALL still be able to read their ballot and the projects in it. A user without one SHALL get 404.

#### Scenario: Assigning a winner shuts reviewing
- **GIVEN** a competition in `voting` where user A has saved rankings
- **WHEN** an admin assigns a winner
- **AND** A then saves rankings, or sets their status to `completed`
- **THEN** both requests return 400 and nothing is stored

#### Scenario: A past reviewer can read a closed competition
- **GIVEN** a `closed` competition where user A has a review record with rankings
- **WHEN** A opens its ballot
- **THEN** the response is 200 with A's ranked projects in order

#### Scenario: A non-reviewer gets 404 on a closed competition
- **GIVEN** a `closed` competition where user B has no review record
- **WHEN** B opens its ballot
- **THEN** the response is 404

### Requirement: A review record is created on the first write

A review record SHALL be created the first time a user with access saves rankings or sets their review status for a competition, and never on a read. A user with access but no record SHALL see every eligible project in the pool, none ranked, and `my_review_status` `in_progress`. At most one record SHALL exist per user and competition, including under concurrent first writes.

#### Scenario: Opening a ballot writes nothing
- **GIVEN** a user with access to a competition in `voting` and no review record for it
- **WHEN** the user opens its ballot and views one of its projects
- **THEN** both succeed and no review record exists for the user

#### Scenario: Saving rankings creates the record
- **GIVEN** a user with access and no review record
- **WHEN** the user saves a ballot ranking two projects
- **THEN** a review record in `in_progress` exists and holds those two rankings

#### Scenario: Completing without ranking is an abstention
- **GIVEN** a user with access and no review record
- **WHEN** the user sets their status to `completed`
- **THEN** a `completed` review record with no rankings exists, and the competition's tally counts one ballot

### Requirement: The ended status is derived from the competition

A review record SHALL store only `in_progress` or `completed`. The API SHALL report `my_review_status` as `ended` when the competition is not in `voting` and the user's record is not `completed`; otherwise it SHALL report the stored value. Clients SHALL still be unable to submit `ended` as a status.

#### Scenario: Unfinished review reads as ended after close
- **GIVEN** a `closed` competition where user A's record is `in_progress`
- **WHEN** A lists their review competitions
- **THEN** that competition's `my_review_status` is `ended`

#### Scenario: Completed review stays completed after close
- **GIVEN** a `closed` competition where user A's record is `completed`
- **WHEN** A lists their review competitions
- **THEN** that competition's `my_review_status` is `completed`

### Requirement: Existing assignment-only records are removed

A data migration SHALL delete every existing review record that is not `completed` and has no rankings for its competition. It SHALL convert every remaining `ended` record to `in_progress`. It SHALL NOT change `completed` records or any ranking. Every competition's tally SHALL be the same after the migration as before it.

#### Scenario: Untouched assignments are deleted
- **GIVEN** a record in `in_progress` or `ended` with no rankings
- **WHEN** the migration runs
- **THEN** the record no longer exists

#### Scenario: Started and completed reviews survive
- **GIVEN** an `ended` record with rankings, and a `completed` record with no rankings
- **WHEN** the migration runs
- **THEN** the first is `in_progress` with its rankings intact, and the second is unchanged

#### Scenario: Tallies are preserved
- **GIVEN** a competition with a mix of completed, in-progress and ended records
- **WHEN** the migration runs
- **THEN** its tally's counted ballots and project order are unchanged

### Requirement: Manual reviewer assignment is gone

The Django admin SHALL NOT offer a way to assign all users as reviewers, nor an "End review period" action. Reviewing SHALL be opened and closed only by the competition's status.

#### Scenario: The competition admin has neither control
- **WHEN** an admin opens a competition's change page and the competition list's actions menu
- **THEN** neither an "Add all users as reviewers" button nor an "End review period" action is present
