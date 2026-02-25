## ADDED Requirements

### Requirement: Authors can edit their own discussions and replies

The system SHALL allow the author of a discussion or reply to update its body text. Only the author SHALL be permitted to edit. The system SHALL track whether a post has been edited by comparing `updated_at` to `created_at` (with a tolerance of ~1 second for auto_now timing).

#### Scenario: Author edits their own discussion
- **WHEN** an authenticated user sends PATCH to `/projects/{project_id}/discussions/{discussion_id}` with a new body, and the user is the author
- **THEN** the system updates the discussion body and returns the updated discussion with 200 status

#### Scenario: Author edits their own reply
- **WHEN** an authenticated user sends PATCH to `/projects/{project_id}/discussions/{reply_id}` with a new body, and the user is the author of the reply
- **THEN** the system updates the reply body and returns the updated reply with 200 status

#### Scenario: Non-author cannot edit
- **WHEN** a user who is not the author sends PATCH to `/projects/{project_id}/discussions/{discussion_id}`
- **THEN** the system returns 403 status

#### Scenario: Edit non-existent discussion
- **WHEN** a user sends PATCH to `/projects/{project_id}/discussions/{discussion_id}` for a discussion that does not exist
- **THEN** the system returns 404 status

### Requirement: Edit service layer method

The discussions handler interface SHALL support an `update_discussion(discussion_id, requesting_user_id, body)` method that updates the discussion body if the requesting user is the author. It SHALL raise `DiscussionNotFoundError` if the discussion does not exist and `NotDiscussionAuthorError` if the user is not the author.

#### Scenario: Service updates discussion body
- **WHEN** `update_discussion` is called with a valid discussion_id, the author's user_id, and a new body
- **THEN** the discussion's body is updated and the updated discussion is returned

#### Scenario: Service rejects non-author edit
- **WHEN** `update_discussion` is called with a user_id that is not the author
- **THEN** `NotDiscussionAuthorError` is raised

### Requirement: Edited indicator in API responses

The discussion and reply API response schemas SHALL include an `is_edited` boolean field. This field SHALL be `true` when `updated_at` is more than 1 second after `created_at`, and `false` otherwise.

#### Scenario: Unedited discussion shows is_edited as false
- **WHEN** a discussion that has never been edited is returned from the API
- **THEN** `is_edited` SHALL be `false`

#### Scenario: Edited discussion shows is_edited as true
- **WHEN** a discussion whose body has been updated via the edit endpoint is returned from the API
- **THEN** `is_edited` SHALL be `true`

### Requirement: Inline edit UI for discussions and replies

The frontend SHALL display an "Edit" button (pencil icon) next to the delete button for the author's own posts. Clicking "Edit" SHALL replace the post body with a pre-filled auto-expanding textarea and Save/Cancel buttons. Pressing Save SHALL call the PATCH endpoint and update the displayed body. Pressing Cancel SHALL discard changes and restore the original body display.

#### Scenario: Author sees edit button on their post
- **WHEN** a discussion or reply is rendered and the current user is the author
- **THEN** an edit button (pencil icon) is displayed alongside the delete button

#### Scenario: Non-author does not see edit button
- **WHEN** a discussion or reply is rendered and the current user is not the author
- **THEN** no edit button is displayed

#### Scenario: Clicking edit enters inline edit mode
- **WHEN** the author clicks the edit button on their post
- **THEN** the post body text is replaced with a textarea pre-filled with the current body, plus Save and Cancel buttons

#### Scenario: Saving an edit updates the post
- **WHEN** the author modifies the body in the edit textarea and clicks Save
- **THEN** the system sends a PATCH request and updates the displayed body with the response

#### Scenario: Cancelling an edit restores original text
- **WHEN** the author clicks Cancel while in edit mode
- **THEN** the textarea is removed and the original body text is restored

### Requirement: Edited indicator display

The frontend SHALL display "(edited)" as muted text next to the timestamp on posts where `is_edited` is `true`.

#### Scenario: Edited post shows indicator
- **WHEN** a discussion or reply with `is_edited: true` is rendered
- **THEN** "(edited)" is displayed next to the timestamp in muted text

#### Scenario: Unedited post shows no indicator
- **WHEN** a discussion or reply with `is_edited: false` is rendered
- **THEN** no edited indicator is displayed
