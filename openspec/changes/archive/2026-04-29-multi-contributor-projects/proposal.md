## Why

Today every project has exactly one `owner` user and write-access is gated on owner-equality. Two near-term needs (Community/Unowned submissions, group-owned projects) require multiple users to share write access to a project, with future-flexible per-relationship permissions. Continuing to bolt features onto a single-FK owner model is unworkable; we need a many-to-many relationship between projects and users now, before community submissions or invited contributors can land.

This change is a foundational backend-only refactor. It does not introduce any user-visible feature on its own; it makes the next two changes possible without each one carrying its own access-control rewrite.

## What Changes

- **Add** `ProjectContributor` join model between `Project` and `User` with fields `role` (`OWNER` | `SUGGESTER`), `full_edit: bool` (default `True`), `created_at`. `unique_together (project, user)`.
- **BREAKING (internal)** Rename `Project.owner` → `Project.creator`. The field still points at the user who originally submitted the project; callers that previously meant "person with write access" must now consult contributors instead. This is a big-bang rename across Django models, services, routers, schemas, admin, signals, fixtures, and tests.
- **Replace** every existing write-access check (`project.owner == request.user`, `Project.objects.filter(owner=request.auth)`, handler `owner_id` checks) with a single permission helper backed by `ProjectContributor.full_edit = True`.
- **Add** a data migration that creates one `ProjectContributor` row per existing project (`role=OWNER`, `full_edit=True`, `user=<old owner>`). Idempotent on re-run.
- **Extend** `/api/projects/{id}` and `/api/projects/me` (and any related project responses) with two new fields: `creator: UserSummary` and `contributors: list[ContributorSummary]`. All previously-present fields stay, populated unchanged, so the current frontend keeps working without modification.
- **Update** project-related notifications: any code that currently targets `project.owner` SHALL fan out to every contributor with `full_edit = True`. (System-user filtering is intentionally deferred to the next change.)
- **Regenerate** OpenAPI schema and TypeScript types so downstream consumers can opt in to the new fields when they choose.

## Capabilities

### New Capabilities
- `project-contributors`: the `ProjectContributor` model, role + `full_edit` semantics, contributor-based write-access rule, and the API surface that exposes contributors on project responses.

### Modified Capabilities
- `project-draft-publish`: write-access language ("the owner") is replaced by "a contributor with `full_edit = True`"; all scenarios referencing "non-owner" rejection are updated to describe non-contributor rejection.
- `project-slugs`: mentions of "the owner" updating titles or non-owners viewing drafts are reworded against the contributor permission rule.
- `notifications`: project notifications target every contributor with `full_edit = True`, not just the owner; existing "project owner" wording in scenarios is updated.

## Impact

- **Django models**: new `ProjectContributor` model + migration; rename migration on `Project.owner`; data migration to backfill contributors.
- **Django services**: `services/project/django_impl/handler.py` and `query.py` rename `owner_id` → `creator_id` parameters and switch their access checks to the contributor helper. Interfaces in `services/project/query_interface.py` and `handler_interface.py` rename `list_for_owner`/`get_for_owner` to `list_for_creator`/`get_for_creator`.
- **Django API**: `api/routers/projects.py` and `api/routers/my_projects.py` swap owner-equality lookups for the permission helper. `api/schemas/project.py` gains `creator` and `contributors` payloads. `api/tasks/email.py` notification targeting fans out across contributors.
- **OpenAPI / web-ui types**: `make extract-openapi` + `npm run generate-types` after the API change; web-ui code itself is not touched in this change.
- **Tests**: every test that creates or filters projects by `owner=` is renamed to `creator=`; new tests cover the contributor permission helper, the access-rule swap, and the data migration.
- **Out of scope**: the Community/Unowned system user, the "I own this project" submit-form flag, competition-entry gating, the `/my-projects` suggestions list, any frontend rendering changes, and any project edit-history / version snapshot work.
