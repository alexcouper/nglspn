## MODIFIED Requirements

### Requirement: Broadcast recipient resolution via Follow preferences

The recipient resolver for `BroadcastEmail` rows whose `email_type` is `competition_results` or `platform_updates` SHALL determine recipients by joining `Follow` and `FollowedChannel` on the Naglasúpan house project (the Project row with `is_house_project = True`).

Mapping:

- `email_type = "competition_results"` → users with a `Follow` on the house project AND a `FollowedChannel` row on the house project's "Competition Winners" channel AND `User.article_email_frequency != "never"`.
- `email_type = "platform_updates"` → users with a `Follow` on the house project AND a `FollowedChannel` row on the house project's "Product Updates" channel AND `User.article_email_frequency != "never"`.

There is no per-channel email switch any more — `FollowedChannel` existence replaces the prior `email_enabled` boolean, and `article_email_frequency` provides the global opt-out lever.

The resolver SHALL exclude:

- Inactive users (`is_active = False`).
- System users (`is_system_user = True`).
- The broadcast's `created_by` user (preserves the existing self-exclusion behaviour).

When no house project exists in the database (greenfield dev / test case), the resolver SHALL return an empty QuerySet and SHALL NOT raise.

The resolver continues to be the **recipient-set** entry point. Broadcast emails are sent through the per-user article-digest path on each recipient's cadence; there is no longer a synchronous send-to-everyone behaviour (see Decision in `simplify-follow-and-cadence/design.md`). Practically, the broadcast task fans each resolved recipient into the article-digest queue and the digest workers deliver them on each user's chosen cadence.

#### Scenario: Competition results broadcast resolves via Competition Winners channel

- **GIVEN** the house project H with channel "Competition Winners" C
- **AND** user U1 with a `Follow` on H, a `FollowedChannel(_, C)` row, and `article_email_frequency = hourly`
- **AND** user U2 with a `Follow` on H, no `FollowedChannel(_, C)` row
- **AND** user U3 with no `Follow` on H
- **AND** user U4 with a `Follow` on H, a `FollowedChannel(_, C)` row, and `article_email_frequency = never`
- **WHEN** `resolve_broadcast_recipients` runs for a `BroadcastEmail` with `email_type = "competition_results"`
- **THEN** the resulting QuerySet SHALL include U1
- **AND** SHALL NOT include U2, U3, or U4

#### Scenario: Platform updates broadcast resolves via Product Updates channel

- **GIVEN** the house project H with channel "Product Updates" C
- **AND** user U1 with a `Follow` on H, a `FollowedChannel(_, C)` row, and `article_email_frequency = weekly`
- **AND** user U2 with a `Follow` on H, no `FollowedChannel(_, C)` row
- **WHEN** `resolve_broadcast_recipients` runs for a `BroadcastEmail` with `email_type = "platform_updates"`
- **THEN** U1 is included
- **AND** U2 is not included

#### Scenario: Inactive users excluded

- **GIVEN** user U with a `Follow` on H, a `FollowedChannel(_, the relevant channel)` row, and `article_email_frequency = hourly`, but `is_active = False`
- **WHEN** `resolve_broadcast_recipients` runs
- **THEN** U is not included

#### Scenario: Broadcast author excluded

- **GIVEN** a `BroadcastEmail` with `created_by = U` and `email_type = "platform_updates"`
- **AND** U has a `Follow` on H, a `FollowedChannel` on the relevant channel, and `article_email_frequency = daily`
- **WHEN** `resolve_broadcast_recipients` runs
- **THEN** U is not included

#### Scenario: Users on never excluded

- **GIVEN** user U with a `Follow` on H, a `FollowedChannel` on the relevant channel, and `article_email_frequency = never`
- **WHEN** `resolve_broadcast_recipients` runs
- **THEN** U is not included

#### Scenario: No house project returns empty

- **GIVEN** a database with no Project where `is_house_project = True`
- **WHEN** `resolve_broadcast_recipients` runs for any `BroadcastEmail`
- **THEN** the resulting QuerySet is empty and no exception is raised
