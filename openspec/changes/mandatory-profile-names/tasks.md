## 1. Backend Model & Migration

- [ ] 1.1 Add `profile_action_required` BooleanField (default=True) to User model
- [ ] 1.2 Generate and apply schema migration
- [ ] 1.3 Create data migration: set `profile_action_required=True` for users with empty first_name or last_name, `False` for users with both names set

## 2. Backend API Changes

- [ ] 2.1 Add `profile_action_required` to `UserResponse` schema
- [ ] 2.2 Add `profile_action_required` to login `Token` response schema (read from authenticated user)
- [ ] 2.3 Update `PUT /api/auth/me` to evaluate and clear `profile_action_required` after save (clear when both first_name and last_name are non-empty after strip)
- [ ] 2.4 Update `PUT /api/auth/me` to require first_name and last_name when `profile_action_required` is True, returning 400 if missing or blank
- [ ] 2.5 Regenerate OpenAPI spec and TypeScript types

## 3. Backend Tests

- [ ] 3.1 Test new user created with `profile_action_required=True`
- [ ] 3.2 Test login response includes `profile_action_required` field
- [ ] 3.3 Test profile save clears flag when both names provided
- [ ] 3.4 Test profile save keeps flag when names still empty
- [ ] 3.5 Test profile save rejects missing names when flag is True
- [ ] 3.6 Test profile save allows partial updates (email prefs only) when flag is False

## 4. Frontend Auth Routing

- [ ] 4.1 Update `getPostAuthDestination` to check `profile_action_required` after `is_verified` gate, redirecting to `/complete-profile` with `next` param preserved
- [ ] 4.2 Add `/complete-profile` to `AUTH_PAGES` list so it's excluded from safe redirects
- [ ] 4.3 Update login page to pass `profile_action_required` from token response into routing

## 5. Frontend Complete Profile Page

- [ ] 5.1 Create `/complete-profile` page with first name and last name form fields (both required)
- [ ] 5.2 Add client-side validation (non-empty, not whitespace-only)
- [ ] 5.3 Submit to `PUT /api/auth/me` on form submit
- [ ] 5.4 On success, redirect to `next` query param or `/my-projects`
- [ ] 5.5 Add auth guard (redirect unauthenticated users to login)

## 6. Frontend Profile Edit Page

- [ ] 6.1 Make first_name and last_name required fields in the profile edit form
- [ ] 6.2 Add validation errors for empty/whitespace-only name fields
- [ ] 6.3 Prevent form submission when name fields are invalid

## 7. Verification

- [ ] 7.1 Test full new-user flow: register → verify email → redirected to complete-profile → fill names → arrive at my-projects
- [ ] 7.2 Test existing-user flow: login with missing names → redirected to complete-profile → fill names → arrive at destination
- [ ] 7.3 Test that profile edit page prevents clearing names
- [ ] 7.4 Test that login with complete profile skips complete-profile page
