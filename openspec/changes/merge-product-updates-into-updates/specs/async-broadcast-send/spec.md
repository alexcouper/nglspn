## MODIFIED Requirements

### Requirement: Broadcast recipient resolution via Follow preferences

The recipient resolver for `BroadcastEmail` rows whose `email_type` is `competition_results` SHALL determine recipients by joining `Follow` and `FollowedChannel` on the Naglasúpan house project (the Project row with `is_house_project = True`).

Mapping:

- `email_type = "competition_results"` → users with a `Follow` on the house project AND a `FollowedChannel` row on the house project's "Competition Winners" channel AND `User.article_email_frequency != "never"`.

`platform_updates` is no longer a valid `email_type`. `BroadcastEmailType` SHALL expose only `competition_results`, so no new broadcast can target it. Historic `BroadcastEmail` rows retain the string `platform_updates` in the column; the resolver SHALL return an empty QuerySet for any unmapped `email_type` rather than raising.

There is no per-channel email switch any more — `FollowedChannel` existence replaces the prior `email_enabled` boolean, and `article_email_frequency` provides the global opt-out lever.

The resolver SHALL exclude:

- Inactive users (`is_active = False`).
- System users (`is_system_user = True`).
- The broadcast's `created_by` user (preserves the existing self-exclusion behaviour).

When no house project exists in the database (greenfield dev / test case), the resolver SHALL return an empty QuerySet and SHALL NOT raise.

The resolver continues to be the **recipient-set** entry point.

#### Scenario: Competition results broadcast resolves via Competition Winners channel

- **GIVEN** the house project H with channel "Competition Winners" C
- **AND** user U1 with a `Follow` on H, a `FollowedChannel(_, C)` row, and `article_email_frequency = hourly`
- **AND** user U2 with a `Follow` on H, no `FollowedChannel(_, C)` row
- **AND** user U3 with no `Follow` on H
- **AND** user U4 with a `Follow` on H, a `FollowedChannel(_, C)` row, and `article_email_frequency = never`
- **WHEN** `resolve_broadcast_recipients` runs for a `BroadcastEmail` with `email_type = "competition_results"`
- **THEN** the resulting QuerySet SHALL include U1
- **AND** SHALL NOT include U2, U3, or U4

#### Scenario: Historic platform updates broadcast resolves to nobody

- **GIVEN** a `BroadcastEmail` row with `email_type = "platform_updates"`
- **WHEN** `resolve_broadcast_recipients` runs for it
- **THEN** the resulting QuerySet SHALL be empty
- **AND** the resolver SHALL NOT raise

#### Scenario: Platform updates cannot be selected for a new broadcast

- **WHEN** an admin creates a `BroadcastEmail` in the Django admin
- **THEN** `platform_updates` SHALL NOT be offered as an `email_type` choice
