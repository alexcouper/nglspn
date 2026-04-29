## 1. User model: is_system_user field

- [ ] 1.1 Add `is_system_user = models.BooleanField(default=False)` to `apps/users/models.py::User`. Place it near the other booleans (`is_active`, `is_staff`).
- [ ] 1.2 Generate the migration: `makemigrations users` → migration adds the field with `default=False`.
- [ ] 1.3 Tests in `apps/users/`: a new user has `is_system_user = False` by default; setting it to `True` does not change any other behaviour at the model level.

## 2. Authentication-backend gate

- [ ] 2.1 Add a single helper, e.g. `services/users/auth_gate.py::reject_system_user(user)` (or a function on the existing auth helper module) that raises (or returns the failure sentinel used by the call site) when `user.is_system_user is True`.
- [ ] 2.2 Identify every code path that issues a session, JWT, or otherwise treats a user as authenticated post-credential-check. At minimum: password-login endpoint, email-verification-code endpoint, password-reset-code endpoint, JWT issuance helper(s) used after registration. Document each location in this task list as a sub-bullet for traceability before editing.
- [ ] 2.3 Wire `reject_system_user` into each identified path so that a system user fails authentication identically to an unknown user / wrong code. The check happens after the credential is recognised and before the token is minted.
- [ ] 2.4 Tests: for each gated path (password login, email verification, password reset, JWT issuance), assert that a system user attempting that path receives the same failure response as a regular failure case, and that no token / session is produced.

## 3. Community/Unowned seed user

- [ ] 3.1 Add a Django data migration in `apps/users/migrations/` that idempotently creates the seed user using `RunPython`. The function uses the historical `User` model and sets: `email = "community@naglasupan.is"`, `kennitala = "7777777777"`, `is_system_user = True`, `is_active = True`, `is_verified = True`, `info = "Projects submitted by community members but owned by people outside of Naglasúpan."`, and unusable password. It SHALL `get_or_create` keyed on `kennitala = "7777777777"` and only update fields if the row was just created.
- [ ] 3.2 Add a management command `apps/users/management/commands/ensure_community_user.py` that delegates to the same idempotent helper as the data migration (extract the logic into `apps/users/seed.py::ensure_community_user`). Useful for tests, local seeding, and recovery.
- [ ] 3.3 Tests: migration test that runs the data migration on an empty DB and asserts exactly one row with the documented properties; second run does not create a duplicate. Management-command test that calls the command and asserts the same.
- [ ] 3.4 Add a typed accessor `apps/users/seed.py::get_community_user() -> User` that fetches the seed user by `kennitala = "7777777777"` (or `is_system_user = True` filtered to the documented email — pick one and use it consistently). Raise a clear exception if the user does not exist.

## 4. Project service: community-owned create

- [ ] 4.1 Extend the `CreateProjectInput` DTO in `services/project/handler_interface.py` with `community_owned: bool = False`.
- [ ] 4.2 In `services/project/django_impl/handler.py::create`, branch on `community_owned`:
  - When `False`: existing behaviour from the previous change (creator is the calling user; one OWNER contributor inserted for the calling user).
  - When `True`: set `creator = calling user`; insert two contributors atomically — the seed user as `OWNER` (`full_edit=True`), the calling user as `SUGGESTER` (`full_edit=True`).
- [ ] 4.3 Use the `get_community_user()` accessor; if it raises, propagate the failure as a 5xx so operators see it in logs.
- [ ] 4.4 Tests in `services/project/django_impl/test_handler.py` covering: self-owned create unchanged; community-owned create produces the documented two contributors with the correct roles and `full_edit=True`; rollback on a forced exception leaves no rows.

## 5. Publish: competition-entry gate

- [ ] 5.1 In `services/project/django_impl/handler.py::publish`, after the existing publish state transition and before `competition.projects.add(project)`, check whether any `ProjectContributor` with `role = OWNER` belongs to a user with `is_system_user = True`. If so, skip the competition add.
- [ ] 5.2 Tests: publishing a community-owned project does not add it to an open `ACCEPTING_APPLICATIONS` competition; publishing a self-owned project under the same conditions still does (existing behaviour preserved).

## 6. API: schema and routes

- [ ] 6.1 In `api/schemas/project.py`, add `community_owned: bool = False` to the create-project request schema.
- [ ] 6.2 In `api/routers/my_projects.py`, plumb the new flag through to the service handler.
- [ ] 6.3 Add the `GET /api/my-projects/suggestions` route in `api/routers/my_projects.py`. Implement it as a query for `Project.objects.filter(contributors__user=request.auth, contributors__role=SUGGESTER, contributors__full_edit=True).distinct()`. Return the same item shape as `GET /api/my-projects`.
- [ ] 6.4 Confirm that `GET /api/my-projects` continues to filter by `creator = request.auth` (creator-scoped, not contributor-scoped). Add an explicit test if one does not already exist.
- [ ] 6.5 Tests in `api/routers/test_my_projects.py`: empty suggestions list; single community-owned project appears in suggestions and not in `/my-projects`; self-owned project appears in `/my-projects` and not in `/suggestions`; authentication is required for `/suggestions`; SUGGESTER row with `full_edit=False` is excluded.

## 7. Notifications: filter system users

- [ ] 7.1 In `apps/notifications/` (and `api/tasks/email.py` if it has its own contributor-fan-out path), update the contributor recipient queryset added in the previous change to also `.exclude(user__is_system_user=True)`.
- [ ] 7.2 Tests in `apps/notifications/`: a project whose only OWNER is the seed user does not produce a notification for the seed user when a discussion is created; a multi-contributor project (real user + seed user) produces a notification only for the real user.

## 8. OpenAPI + types regeneration

- [ ] 8.1 Run `make extract-openapi` from `src/django-backend/`. Verify the spec includes the new `community_owned` request flag and the `/api/my-projects/suggestions` endpoint.
- [ ] 8.2 Run `npm run generate-types` from `src/web-ui/` to regenerate TypeScript types. The next change consumes them.

## 9. Verification

- [ ] 9.1 Run `make ci` from project root.
- [ ] 9.2 Manual smoke (curl or a quick test script): create a community-owned project; confirm contributors via `/api/my-projects/{id}`; publish it; confirm it does not appear under any competition's project list; confirm it appears in `/api/my-projects/suggestions` for its suggester.
- [ ] 9.3 Manual confirm: log in as a regular user, then attempt password login as `community@naglasupan.is` — must fail. Attempt password reset for that address — request must succeed (we don't disclose existence) but no usable code is sent / consuming a forced code fails.
- [ ] 9.4 Run `openspec validate community-project-suggestions --strict` and confirm validation passes.
