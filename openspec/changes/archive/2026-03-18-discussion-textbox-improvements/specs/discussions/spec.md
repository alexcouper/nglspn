## ADDED Requirements

### Requirement: Auto-expanding textareas for discussion input

All discussion and reply textareas SHALL auto-expand as the user types, growing to fit content up to a maximum height of `12rem`. Beyond the maximum height, the textarea SHALL scroll. The textarea SHALL also shrink when content is deleted. The minimum size SHALL be the original row count (3 rows for new discussions, 2 rows for replies).

#### Scenario: Textarea grows as user types
- **WHEN** a user types text that exceeds the visible rows of a discussion or reply textarea
- **THEN** the textarea height increases to fit the content without scrolling

#### Scenario: Textarea stops growing at max height
- **WHEN** the content height exceeds `12rem`
- **THEN** the textarea height is capped at `12rem` and the content scrolls within it

#### Scenario: Textarea shrinks when content is deleted
- **WHEN** a user deletes text so the content fits in fewer rows
- **THEN** the textarea height decreases to fit the content, but not below the minimum row count

### Requirement: Discussion response includes is_edited field

The `DiscussionResponse` and `ReplyResponse` API schemas SHALL include an `is_edited` boolean field indicating whether the post has been modified after creation.

#### Scenario: Discussion response shape includes is_edited
- **WHEN** a discussion or reply is returned from any API endpoint
- **THEN** it SHALL include `is_edited` (boolean) alongside id, body, created_at, author, and replies
