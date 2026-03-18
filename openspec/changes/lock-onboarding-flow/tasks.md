## 1. Route enforcement

- [ ] 1.1 Update `useRequireAuth` hook to read `user` from `useAuth()` and redirect to `/onboarding` when `pending_onboarding_steps` is non-empty and `pathname !== "/onboarding"`
- [ ] 1.2 Add test for `useRequireAuth` verifying redirect to `/onboarding` when user has pending steps
- [ ] 1.3 Add test for `useRequireAuth` verifying no redirect when already on `/onboarding`

## 2. Navigation

- [ ] 2.1 Update `Navigation` component to hide My Projects, My Reviews links (desktop and mobile) when `user.pending_onboarding_steps` is non-empty
- [ ] 2.2 Update mobile menu to hide Profile link during onboarding while keeping logout visible
- [ ] 2.3 Add test for Navigation verifying authenticated links are hidden during onboarding
- [ ] 2.4 Add test for Navigation verifying logout remains accessible during onboarding

## 3. Verification

- [ ] 3.1 Run linting (`npm run lint` from web-ui)
- [ ] 3.2 Run existing tests to confirm no regressions
