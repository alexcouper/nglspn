## 1. Registration Service

- [x] 1.1 Create `services/registration/` directory structure: `handler_interface.py`, `steps.py`, `django_impl/__init__.py`, `django_impl/handler.py`
- [x] 1.2 Define `OnboardingStep` dataclass in `steps.py` with `id: str`, `priority: int`, `check: Callable[[User], bool]`
- [x] 1.3 Create the step registry list in `steps.py` with the `verify-email` step (priority 100, check: `user.is_verified`)
- [x] 1.4 Define `RegistrationHandlerInterface` with `get_pending_steps(user) -> list[OnboardingStep]`
- [x] 1.5 Implement `DjangoRegistrationHandler.get_pending_steps` — filter registry to steps where check returns False, sort by priority
- [x] 1.6 Register `registration` service in `services/__init__.py` on `HandlerServices`
- [x] 1.7 Write tests for `get_pending_steps`: all complete, some incomplete, priority ordering, newly added step against existing user

## 2. API Changes

- [x] 2.1 Add `pending_onboarding_steps: list[str]` field to `UserResponse` schema
- [x] 2.2 Add a `resolve_pending_onboarding_steps` static method on `UserResponse` that calls `HANDLERS.registration.get_pending_steps`
- [x] 2.3 Regenerate OpenAPI spec (`make extract-openapi`)
- [x] 2.4 Regenerate TypeScript types (`npm run generate-types`)
- [x] 2.5 Write API test: `/me` returns correct `pending_onboarding_steps` for verified and unverified users

## 3. Frontend Onboarding Gate

- [x] 3.1 Update `getPostAuthDestination` in `auth-routing.ts` to check `pending_onboarding_steps` instead of `is_verified` — redirect to `/onboarding?next=<dest>` if non-empty
- [x] 3.2 Update `AUTH_PAGES` list to include `/onboarding` and keep `/verify-email`
- [x] 3.3 Update login page to use the new gate logic (should work via existing `getPostAuthDestination` call)
- [x] 3.4 Update register page to use the new gate logic

## 4. Onboarding Page

- [x] 4.1 Extract verify-email UI from `/verify-email/page.tsx` into a `VerifyEmailStep` component that accepts `onComplete: () => void` prop
- [x] 4.2 Create the step component map: `Record<string, ComponentType<OnboardingStepProps>>` with `verify-email` → `VerifyEmailStep`
- [x] 4.3 Create `/onboarding/page.tsx` — reads `pending_onboarding_steps` from user context, renders first step's component, calls `refreshUser` on `onComplete`, advances or redirects to destination
- [x] 4.4 Add `useRequireAuth` to the onboarding page to enforce authentication
- [x] 4.5 Handle unknown step IDs gracefully — log warning and skip

## 5. Backwards Compatibility

- [x] 5.1 Update `/verify-email/page.tsx` to redirect to `/onboarding` (preserve `next` param)
- [x] 5.2 Keep `is_verified` on the login token response (no changes needed — just don't remove it)

## 6. Verification

- [x] 6.1 Run backend linting and tests (`make lint && make test`)
- [x] 6.2 Run frontend linting (`npm run lint`)
- [x] 6.3 Manual test: register new user → lands on `/onboarding` → verify email step → redirected to `/my-projects`
- [x] 6.4 Manual test: login as unverified user → lands on `/onboarding` → verify email → proceeds
- [x] 6.5 Manual test: login as verified user → goes straight to `/my-projects`
- [x] 6.6 Manual test: visiting `/verify-email` redirects to `/onboarding`
