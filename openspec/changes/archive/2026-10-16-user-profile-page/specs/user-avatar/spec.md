## ADDED Requirements

### Requirement: An avatar is a separately stored image owned by one user

The system SHALL store avatars in a `UserAvatar` model with `user` (FK, non-null), `storage_key`, `content_type`, `file_size`, `width`, `height`, `upload_status` (`pending` or `uploaded`), `created_at` and `uploaded_at`. `User.avatar` SHALL be a nullable FK to the row that is current. Avatars SHALL NOT be `ProjectImage` rows. Storage keys SHALL be of the form `avatars/{user_id}/{unique}/{filename}`. The change SHALL ship the migration that adds both.

#### Scenario: Model and migration are in step
- **WHEN** `manage.py makemigrations --check --dry-run` runs after the change
- **THEN** it reports no missing migrations

#### Scenario: Key prefix
- **WHEN** an avatar upload is reserved for user U
- **THEN** its storage key begins with `avatars/{U.id}/`

### Requirement: Reserving an avatar upload returns a presigned PUT

`POST /api/auth/me/avatar/upload-url` SHALL accept `filename`, `content_type` and `file_size`, and for the authenticated user SHALL create a `pending` `UserAvatar` row and return `image_id`, `upload_url`, `method`, `headers` and `storage_key`, in the same shape as the project image upload response. It SHALL reject with 400 a `content_type` outside `image/jpeg`, `image/png`, `image/webp`, and a `file_size` above 2 MB. Reserving SHALL NOT change `User.avatar`.

#### Scenario: Valid reservation
- **WHEN** a logged-in user posts `{filename: "me.jpg", content_type: "image/jpeg", file_size: 300000}`
- **THEN** the response is 200 with a presigned PUT, a `pending` row exists for that user, and `User.avatar` is unchanged

#### Scenario: GIF rejected
- **WHEN** a logged-in user posts `content_type: "image/gif"`
- **THEN** the response is 400 and no row is created

#### Scenario: Too large
- **WHEN** a logged-in user posts `file_size: 2097153`
- **THEN** the response is 400 and no row is created

#### Scenario: Unauthenticated
- **WHEN** an anonymous client posts to the endpoint
- **THEN** the response is 401

### Requirement: Completing an upload makes it the current avatar and retires the old one

`POST /api/auth/me/avatar/{image_id}/complete` SHALL accept `width` and `height`, verify the object exists in storage, mark the row `uploaded`, set `User.avatar` to it, and delete the previously current `UserAvatar` row if there was one. It SHALL return the updated `UserResponse`, whose `avatar_url` is the new object's public URL. It SHALL return 404 for an `image_id` that is not a `pending` row belonging to the caller, and 400 when the object is missing from storage.

#### Scenario: First avatar
- **WHEN** a user with no avatar completes a reserved upload whose object is in storage
- **THEN** `User.avatar` points at the row, the row is `uploaded`, and the response's `avatar_url` is `{S3_PUBLIC_URL_BASE}/{storage_key}`

#### Scenario: Replacement
- **WHEN** a user with a current avatar completes a new upload
- **THEN** `User.avatar` points at the new row and the old row no longer exists

#### Scenario: Object never arrived
- **WHEN** a user completes a reservation whose PUT never happened
- **THEN** the response is 400 and `User.avatar` is unchanged

#### Scenario: Someone else's reservation
- **WHEN** a user completes an `image_id` reserved by another user
- **THEN** the response is 404

### Requirement: Removing the avatar

`DELETE /api/auth/me/avatar` SHALL set `User.avatar` to null and delete the row that was current, returning the updated `UserResponse` with `avatar_url = null`. It SHALL succeed with the same response when there is no avatar to remove.

#### Scenario: Remove
- **WHEN** a user with an avatar calls the endpoint
- **THEN** `avatar_url` is null in the response and the row is gone

#### Scenario: Nothing to remove
- **WHEN** a user without an avatar calls the endpoint
- **THEN** the response is 200 with `avatar_url = null`

### Requirement: Avatar objects are never orphaned in storage

Deleting a `UserAvatar` row SHALL write an `OrphanedStorageObject` tombstone for its key, and the existing sweep SHALL drain it. The sweep SHALL also reap `pending` `UserAvatar` rows older than the shared pending-upload cutoff, which tombstones their keys in turn.

#### Scenario: Replaced avatar is drained
- **WHEN** a user replaces their avatar and the sweep runs
- **THEN** the old key is deleted from storage and its tombstone is gone

#### Scenario: Abandoned reservation is reaped
- **WHEN** a `pending` `UserAvatar` row is older than the cutoff and the sweep runs
- **THEN** the row is deleted and its key is tombstoned for the same sweep's drain

#### Scenario: Fresh reservation is left alone
- **WHEN** a `pending` `UserAvatar` row is younger than the cutoff and the sweep runs
- **THEN** the row remains

### Requirement: `avatar_url` is exposed on the user schemas

`UserResponse` and `PublicUserProfile` SHALL carry `avatar_url`: the public URL of the current avatar when `User.avatar` is set and `uploaded`, else null. Resolving it SHALL NOT issue a query beyond the user row and its avatar FK.

#### Scenario: With avatar
- **WHEN** a user with an uploaded avatar is serialised as either schema
- **THEN** `avatar_url` is the object's public URL

#### Scenario: Without avatar
- **WHEN** a user with no avatar, or whose avatar row is still `pending`, is serialised
- **THEN** `avatar_url` is null

### Requirement: The edit page crops in the browser and uploads a square

On `/profile`, choosing a file SHALL open the existing image cropper locked to a 1:1 ratio. Confirming SHALL draw the chosen region to a 512×512 canvas, encode it as JPEG, reserve an upload with that blob's size and type, PUT it to the presigned URL, complete it, and show the new avatar without a page reload. A file the browser cannot decode as an image, or a reservation the API rejects, SHALL surface as an inline error and leave the current avatar in place. "Remove" SHALL call the delete endpoint and show initials.

#### Scenario: Upload
- **WHEN** a user picks a 3000×2000 JPEG, frames a region and confirms
- **THEN** the PUT body is a JPEG no larger than 2 MB, the complete call succeeds, and the header shows the new image

#### Scenario: Rejected file
- **WHEN** a user picks a file that is not an image
- **THEN** an error is shown next to the avatar and no request is made

#### Scenario: Remove
- **WHEN** a user with an avatar presses Remove
- **THEN** the delete endpoint is called and the initials fallback is shown

### Requirement: Initials stand in for a missing avatar

Wherever an avatar is rendered (the profile header, the edit page, the nav's account button), a null `avatar_url` SHALL render the person's initials — the first letter of `first_name` and of `last_name`, whichever are non-empty — in a circle of the same size. A user with neither name SHALL render a generic person glyph. The rendered element SHALL have the person's display name as its accessible label.

#### Scenario: Two names
- **WHEN** a user named "Sigrún Helgadóttir" has no avatar
- **THEN** the avatar slot shows "SH"

#### Scenario: One name
- **WHEN** a user with only a first name "Sigrún" has no avatar
- **THEN** the avatar slot shows "S"

#### Scenario: Image present
- **WHEN** `avatar_url` is set
- **THEN** an `img` with that URL fills the slot, cropped to a circle, with the display name as `alt`
