## ADDED Requirements

### Requirement: Broadcast recipient resolution via Follow preferences

The recipient resolver for `BroadcastEmail` rows whose `email_type` is `competition_results` or `platform_updates` SHALL determine recipients by joining `Follow` and `FollowChannelPreference` on the Naglasúpan house project (the Project row with `is_house_project = True`) rather than by reading the legacy `User.email_opt_in_*` fields (which no longer exist after this change).

Mapping:

- `email_type = "competition_results"` → users with a `Follow` on the house project AND a `FollowChannelPreference` on the house project's "Competition Winners" channel with `email_enabled = True`.
- `email_type = "platform_updates"` → users with a `Follow` on the house project AND a `FollowChannelPreference` on the house project's "Product Updates" channel with `email_enabled = True`.

The resolver SHALL exclude:
- Inactive users (`is_active = False`).
- System users (`is_system_user = True`) — though system users have no Follow row by construction, the explicit filter is retained as a safety net.
- The broadcast's `created_by` user (preserves the existing self-exclusion behaviour).

When no house project exists in the database (greenfield dev / test case), the resolver SHALL return an empty QuerySet and SHALL NOT raise.

#### Scenario: Competition results broadcast resolves via Competition Winners channel
- **GIVEN** the house project H with channel "Competition Winners" C
- **AND** user U1 with a Follow on H and `FollowChannelPreference(channel=C, email_enabled=True)`
- **AND** user U2 with a Follow on H and `FollowChannelPreference(channel=C, email_enabled=False)`
- **AND** user U3 with no Follow on H
- **WHEN** `resolve_broadcast_recipients` runs for a `BroadcastEmail` with `email_type = "competition_results"`
- **THEN** the resulting QuerySet SHALL include U1
- **AND** SHALL NOT include U2 or U3

#### Scenario: Platform updates broadcast resolves via Product Updates channel
- **GIVEN** the house project H with channel "Product Updates" C
- **AND** user U1 with a Follow on H and `FollowChannelPreference(channel=C, email_enabled=True)`
- **AND** user U2 with a Follow on H and `FollowChannelPreference(channel=C, email_enabled=False)`
- **WHEN** `resolve_broadcast_recipients` runs for a `BroadcastEmail` with `email_type = "platform_updates"`
- **THEN** U1 is included
- **AND** U2 is not included

#### Scenario: Inactive users excluded
- **GIVEN** user U with a Follow on H and the relevant channel `email_enabled = True`, but `is_active = False`
- **WHEN** `resolve_broadcast_recipients` runs
- **THEN** U is not included

#### Scenario: Broadcast author excluded
- **GIVEN** a `BroadcastEmail` with `created_by = U` and `email_type = "platform_updates"`
- **AND** U has a Follow on H and the relevant channel `email_enabled = True`
- **WHEN** `resolve_broadcast_recipients` runs
- **THEN** U is not included

#### Scenario: No house project returns empty
- **GIVEN** a database with no Project where `is_house_project = True`
- **WHEN** `resolve_broadcast_recipients` runs for any `BroadcastEmail`
- **THEN** the resulting QuerySet is empty and no exception is raised

#### Scenario: Pre-flip / post-flip recipient parity
- **GIVEN** a snapshot of users whose pre-flip recipient resolution (via legacy `email_opt_in_*` flags) selects them for a `platform_updates` broadcast
- **AND** the same database with the legacy fields dropped and the new Follow-based path in place
- **WHEN** the post-flip resolver runs for the same broadcast type
- **THEN** the resulting recipient set SHALL match the pre-flip snapshot (a regression test enabled by Phase 1's data migration having seeded preferences from those legacy flags)
