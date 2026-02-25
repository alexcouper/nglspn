## Why

Users appear as "Anonymous" in discussions, project ownership, and public profiles because first/last names are optional and most users never fill them in. This undermines community trust and makes the platform feel impersonal.

## What Changes

- **`profile_action_required` flag**: Add a generic boolean field on the User model. When `True`, the frontend redirects the user to `/complete-profile` on login before they can proceed. The flag is cleared automatically when profile requirements are satisfied.
- **Mandatory name fields**: Make first_name and last_name required on the profile save endpoint when `profile_action_required` is set. The profile edit page enforces this in the UI.
- **`/complete-profile` page**: A focused page with just first name and last name fields, shown to users who need to complete their profile. Submits to the existing `PUT /api/auth/me`.
- **Data migration**: Set `profile_action_required=True` for all existing users who have empty first_name or last_name.
- **New registrations**: New users are created with `profile_action_required=True` by default, so they hit the same enforcement on first login after verifying email.

## Capabilities

### New Capabilities

- `mandatory-profile-names`: Covers the `profile_action_required` flag, the login redirect logic, the `/complete-profile` page, and mandatory field enforcement on profile save.

### Modified Capabilities

_(none — no existing specs are affected at the requirement level)_

## Impact

- **Django backend**: User model migration (new field), login API response change, profile update endpoint validation
- **Web UI**: New `/complete-profile` page, profile form validation changes, auth routing updates (`getPostAuthDestination`)
- **Emails**: No changes needed — templates already handle names gracefully with fallbacks
- **Data**: One-time migration to flag existing users with missing names
