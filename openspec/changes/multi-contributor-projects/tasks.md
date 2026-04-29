## 1. Discovery & audit (jj change 1 prep)

- [ ] 1.1 Grep audit: list every site that references `Project.owner`, `owner_id`, `list_for_owner`, `get_for_owner`, `request.auth` paired with `owner=`, and any `project.owner ==` check. Save the list as a working note (will be used to verify the rename in jj change 2).
- [ ] 1.2 Confirm `apps/notifications/` and `api/tasks/email.py` are the only places that target `project.owner` for delivery; note any other call sites discovered.

## 2. ProjectContributor model + migration (jj change 1)

- [ ] 2.1 Add `ContributorRole` (`TextChoices`: `OWNER`, `SUGGESTER`) and `ProjectContributor` model in `apps/projects/models.py` with fields `id`, `project`, `user`, `role`, `full_edit` (default `True`), `created_at`. Set `db_table = "project_contributors"`, `unique_together = ("project", "user")`, and default `Meta.ordering` such that `OWNER` rows come before `SUGGESTER` rows then by `created_at` ascending.
- [ ] 2.2 Register `ProjectContributor` in `apps/projects/admin.py` with project, user, role, and full_edit columns visible.
- [ ] 2.3 Generate the schema migration: `makemigrations projects` → migration file with `CreateModel` for `ProjectContributor`.
- [ ] 2.4 In the same migration, add a `RunPython` data migration that, for every `Project`, inserts one `ProjectContributor(project=p, user=p.owner, role=OWNER, full_edit=True)` if a row does not already exist for `(p, p.owner)`. Provide a no-op reverse function (the `CreateModel` reversal already drops the table).
- [ ] 2.5 Add unit tests in `apps/projects/test_contributor_backfill_migration.py` (model present after migration; one OWNER row per existing project; idempotent on re-run).

## 3. Permission helper (jj change 1)

- [ ] 3.1 Add `services/project/permissions.py` (or equivalent in the project service package) exposing `user_can_edit_project(project: Project, user: User) -> bool` that returns `True` iff a `ProjectContributor` row exists with `project=project`, `user=user`, `full_edit=True`.
- [ ] 3.2 Add focused tests: returns False for anonymous, False for users with no row, False for `full_edit=False`, True for `full_edit=True`.

## 4. Switch write-access checks to the helper (jj change 1)

- [ ] 4.1 In `api/routers/my_projects.py`, replace each `get_object_or_404(Project, id=project_id, owner=request.auth)` with a fetch by id followed by a `user_can_edit_project` check; on failure return the same 404 response as today.
- [ ] 4.2 In `api/routers/my_projects.py`, replace `REPO.project.list_for_owner(request.auth.id)` semantics with the new flow described in §6 (still owner-named in this change).
- [ ] 4.3 In `api/routers/projects.py` around line 182, replace the `project.owner == user or user.is_superuser` draft-visibility check with `user_can_edit_project(project, user) or user.is_superuser`.
- [ ] 4.4 In `services/project/django_impl/handler.py`, refactor `update`, `delete`, `resubmit`, and `publish` to fetch the project by id (not by `owner_id`) and assert `user_can_edit_project(project, acting_user)`; raise the existing not-found / not-authorised exceptions on failure.
- [ ] 4.5 Update `services/project/django_impl/query.py::get_for_owner` to use the contributor lookup (still named `get_for_owner` until §8 renames it).
- [ ] 4.6 Re-run `make test` in `src/django-backend/` and confirm all owner-gated route tests still pass with no logic regressions.

## 5. Project creation inserts the OWNER contributor (jj change 1)

- [ ] 5.1 Update the `create` path in `services/project/django_impl/handler.py` so the project insert and the matching `ProjectContributor` insert happen inside one `transaction.atomic()` block.
- [ ] 5.2 Tests: `test_handler.py` covers (a) a successful create yields one OWNER contributor with `full_edit=True`, and (b) a forced exception inside the contributor insert rolls back the project insert.

## 6. Project listing returns owned projects via contributor lookup (jj change 1)

- [ ] 6.1 In `services/project/django_impl/query.py::list_for_owner`, change the implementation to filter by "user has a `ProjectContributor` row with `full_edit = True`". Keep the function name in this jj change; rename happens in §8.
- [ ] 6.2 Verify existing `/api/my-projects` listing tests still pass without modification (single-contributor projects; behaviour unchanged for backfilled data).

## 7. API responses, OpenAPI, and notifications (jj change 1)

- [ ] 7.1 In `api/schemas/project.py`, add `creator: UserSummary` and `contributors: list[ContributorSummary]` to the project response model. Define `ContributorSummary` as `{ user: UserSummary, role: str, full_edit: bool }`.
- [ ] 7.2 Populate the new fields in every router that returns a project (`projects.py`, `my_projects.py`). For all backfilled data, `creator` equals the existing `owner` field on the model and `contributors` is a single-entry list.
- [ ] 7.3 Update notification fan-out: in `apps/notifications/` (and any matching site in `api/tasks/email.py`) replace single-`project.owner` lookups with iteration over contributors with `full_edit=True`. Keep deduplication for users who appear via multiple sources (e.g. owner + discussion author).
- [ ] 7.4 Run `make extract-openapi` from `src/django-backend/` and verify the new fields appear in the spec.
- [ ] 7.5 Run `npm run generate-types` from `src/web-ui/` to regenerate TypeScript types.
- [ ] 7.6 Run `make ci` from project root to confirm linting and tests pass end-to-end.
- [ ] 7.7 Commit jj change 1 with a description that mentions the contributor model, access-control swap, and notification fan-out (field is still `owner`).

## 8. Rename owner → creator (jj change 2)

- [ ] 8.1 Generate a Django migration with `RenameField(model_name='project', old_name='owner', new_name='creator')`.
- [ ] 8.2 Rename the field on `Project` in `apps/projects/models.py`. Update `related_name="projects"` on the FK if needed (kept the same — projects still belong to creators).
- [ ] 8.3 Sweep through the audit list from §1.1 and rename every reference: `apps/projects/admin.py`, `apps/projects/signals.py`, `apps/projects/slugs.py`, `apps/projects/management/commands/seed_discover_data.py`, `apps/projects/management/commands/generate_image_variants.py`, every test in `apps/projects/`, every fixture, etc.
- [ ] 8.4 Rename in services: `services/project/handler_interface.py` (DTOs use `creator_id`), `services/project/query_interface.py` (`list_for_owner` → `list_for_creator`, `get_for_owner` → `get_for_creator`), `services/project/django_impl/handler.py`, `services/project/django_impl/query.py`, `services/project/django_impl/test_handler.py`, `services/project/django_impl/test_query.py`.
- [ ] 8.5 Rename in API: `api/routers/projects.py`, `api/routers/my_projects.py`, `api/routers/test_projects.py`, `api/routers/test_my_projects.py`, `api/routers/test_project_images.py`, `api/schemas/project.py`, `api/tasks/email.py`.
- [ ] 8.6 Update conftest / factories so any project-creation helper passes `creator=` instead of `owner=`.
- [ ] 8.7 Run `make extract-openapi` and `npm run generate-types` again so the new `creator` field surfaces under its renamed key (the FE will pick this up in the next change).
- [ ] 8.8 Run `make ci` from project root.
- [ ] 8.9 Verify the audit list from §1.1 has zero remaining references to `owner` / `owner_id` / `list_for_owner` / `get_for_owner` in the touched paths (legitimate references like `is_superuser` are unrelated).
- [ ] 8.10 Commit jj change 2 with a description that calls out the rename.

## 9. Verification

- [ ] 9.1 Run `make ci` and confirm a clean pass.
- [ ] 9.2 Manual smoke (Playwright or curl): create a project, edit it, publish it, delete a draft — all paths use the new permission helper and continue to work for the creator.
- [ ] 9.3 Confirm `/api/projects/{id}` and `/api/my-projects/{id}` responses include `creator` and `contributors` populated correctly for an existing project.
- [ ] 9.4 Run `openspec validate multi-contributor-projects --strict` and confirm validation passes.
