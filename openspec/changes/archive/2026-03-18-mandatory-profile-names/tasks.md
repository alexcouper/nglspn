## 1. Backend: Register Onboarding Step

- [x] 1.1 Add `complete-profile` step to `ONBOARDING_STEPS` in `services/registration/steps.py` with priority 200 and check: `lambda user: bool(user.first_name.strip()) or bool(user.last_name.strip())`
- [x] 1.2 Add tests for the step check function: no names → pending, first name only → complete, last name only → complete, both names → complete, whitespace-only → pending
- [x] 1.3 Add test that `complete-profile` is ordered after `verify-email` in pending steps

## 2. Backend: Profile Save Validation

- [x] 2.1 Add validation to `PUT /api/auth/me` that rejects saves resulting in both first_name and last_name being empty (400 error)
- [x] 2.2 Test: saving with at least one name succeeds
- [x] 2.3 Test: saving with both names empty returns 400
- [x] 2.4 Test: partial update (e.g. notification_frequency only) with existing names preserved succeeds

## 3. Backend: Regenerate Types

- [x] 3.1 Regenerate OpenAPI spec (`make extract-openapi`) and TypeScript types (`npm run generate-types`) — no schema changes expected but verify

## 4. Frontend: CompleteProfileStep Component

- [x] 4.1 Create `CompleteProfileStep` component in `components/onboarding/` with first name and last name inputs
- [x] 4.2 Add client-side validation: at least one field must be non-empty (not whitespace-only)
- [x] 4.3 Submit to `PUT /api/auth/me` on form submit, call `onComplete` on success
- [x] 4.4 Register `"complete-profile"` → `CompleteProfileStep` in `ONBOARDING_STEP_COMPONENTS`

## 5. Frontend: Profile Edit Page Validation

- [x] 5.1 Add validation to profile edit form preventing save when both name fields would be empty
- [x] 5.2 Show validation error message when both names are cleared

## 6. Verification

- [x] 6.1 Test new-user flow: register → verify email → complete-profile step shown on onboarding page → fill name → arrive at my-projects
- [x] 6.2 Test existing-user flow: login with no names → onboarding page shows complete-profile step → fill name → arrive at destination
- [x] 6.3 Test user with existing first name skips complete-profile step entirely
- [x] 6.4 Test profile edit page prevents clearing both names
