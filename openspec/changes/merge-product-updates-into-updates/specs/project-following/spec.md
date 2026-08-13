## MODIFIED Requirements

### Requirement: Naglasúpan has the two seeded channels

The Naglasúpan project (the project with `is_house_project = True`) SHALL have, in addition to the default "Updates" channel, one further channel named "Competition Winners".

The name SHALL match the sole remaining `BroadcastEmailType` value 1:1 in concept: "Competition Winners" corresponds to `competition_results`.

The house project SHALL NOT have a "Product Updates" channel. Where one exists, the data migration `follows/0006_merge_product_updates_into_updates` SHALL merge it into "Updates" by reassigning the house project's articles from "Updates" onto it, deleting the "Updates" channel, and renaming it to "Updates". The surviving channel therefore carries the "Product Updates" subscriber list.

#### Scenario: Naglasúpan has two channels after the merge migration

- **GIVEN** the Naglasúpan Project row exists with channels "Updates", "Competition Winners" and "Product Updates"
- **WHEN** the merge migration runs
- **THEN** Naglasúpan has exactly two channels: "Updates" and "Competition Winners"

#### Scenario: Surviving Updates channel carries the Product Updates subscribers

- **GIVEN** user U1 has a `FollowedChannel` row on "Product Updates" and on "Updates"
- **AND** user U2 has a `FollowedChannel` row on "Updates" only
- **WHEN** the merge migration runs
- **THEN** U1 has a `FollowedChannel` row on the surviving "Updates" channel
- **AND** U2 has no `FollowedChannel` row on any house channel

#### Scenario: Articles from both channels survive the merge

- **GIVEN** article A on the house project's "Updates" channel and article B on its "Product Updates" channel
- **WHEN** the merge migration runs
- **THEN** both A and B reference the surviving "Updates" channel
- **AND** no `Notification` row referencing A or B is deleted

#### Scenario: Merge migration is idempotent

- **GIVEN** the merge migration has already run
- **WHEN** it runs again
- **THEN** it SHALL make no changes and SHALL NOT raise

#### Scenario: Merge migration no-ops without a house project

- **GIVEN** no Project has `is_house_project = True`
- **WHEN** the merge migration runs
- **THEN** it SHALL log a warning, make no changes, and SHALL NOT raise

#### Scenario: Other projects have only Updates

- **GIVEN** a non-Naglasúpan Project P existing prior to migration
- **WHEN** the data migration runs
- **THEN** P has exactly one channel: "Updates"
