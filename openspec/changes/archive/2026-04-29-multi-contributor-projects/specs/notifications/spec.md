## MODIFIED Requirements

### Requirement: Notification recipient determination

When creating notifications for a discussion, the system SHALL notify:

1. Every `ProjectContributor` on the project the discussion belongs to whose `full_edit = True`.
2. The author of the root discussion (if the trigger is a reply).
3. All users who have previously replied to the same root discussion.

The system SHALL exclude the author of the triggering discussion/reply from the notification list. The system SHALL create at most one notification per user per triggering comment (deduplicated across all three sources above).

#### Scenario: New root discussion notifies every full-edit contributor

- **WHEN** user A creates a discussion on a project P that has two contributors B and C (both `full_edit = True`) and a third contributor D with `full_edit = False`
- **THEN** one notification is created for B and one for C
- **AND** no notification is created for D

#### Scenario: Root discussion by a project contributor creates no notifications

- **WHEN** user A is the only `full_edit = True` contributor on a project and creates a discussion on that project, and no other participants exist
- **THEN** no notifications are created (A is excluded as the triggering author)

#### Scenario: Reply notifies project contributors and discussion creator

- **WHEN** user C replies to a discussion created by user A on a project whose only `full_edit = True` contributor is user B
- **THEN** notifications are created for user A and user B (not user C)

#### Scenario: Reply notifies previous participants

- **WHEN** user D replies to a discussion where users A, B, and C have previously replied, on a project whose only `full_edit = True` contributor is user E
- **THEN** notifications are created for users A, B, C, and E (deduplicated, excluding user D)

#### Scenario: Deduplication across roles

- **WHEN** user A is both a `full_edit = True` contributor on the project and the discussion creator, and user B replies
- **THEN** exactly one notification is created for user A (not two)
