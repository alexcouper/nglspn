# Owner-reference audit (working note for §1.1, §1.2)

This is a transient note used to verify §8.9 after the rename. It can be deleted when the change is archived.

## Models / migrations

- `apps/projects/models.py:101` — `Project.owner` field definition (FK to AUTH_USER_MODEL).
- `apps/projects/migrations/0002_initial.py:31` — migration historical reference; do NOT change historic migrations.

## Admin

- `apps/projects/admin.py:189` — fieldset label "Ownership" with `("owner",)`.
- `apps/projects/admin.py:198–200` — link to owner's user admin.
- `apps/projects/admin.py:209–210` — uses `obj.owner.opt_in_to_external_promotions`.
- `apps/projects/admin.py:221, 253` — `select_related("owner", ...)` on querysets.

## Management commands

- `apps/projects/management/commands/seed_discover_data.py:196,198,200,207,247,257,297,316` — local variable names and `owner=` kwargs in factories.

## Services — project (write/read paths)

- `services/project/handler_interface.py:10,42,46,49,52` — DTOs and method signatures use `owner_id`.
- `services/project/query_interface.py:68,84` — `get_for_owner`, `list_for_owner` interface methods.
- `services/project/django_impl/handler.py:69,96,99,141,143,148,150,164,166` — `owner_id` parameters and `Project.objects.get(id=..., owner_id=...)` calls.
- `services/project/django_impl/query.py:36,48,170,172,222,223,230,236,237` — `select_related("owner")`, `get_for_owner`, `list_for_owner`, `project.owner.email/first_name`.
- `services/project/django_impl/test_handler.py` — many `owner=user` / `owner_id=user.id` test setups.
- `services/project/django_impl/test_query.py` — `owner=user` factory args; `get_for_owner`, `list_for_owner` calls.

## Services — notifications & email (delivery targets)

- `services/notifications/django_impl/handler.py:33-34` — `project_owner = discussion.project.owner`. **This is the contributor fan-out site for §7.3.**
- `services/email/django_impl/handler.py:167,182,189,192,194,199,202,209,210,216` — uses `project.owner` for new-project admin email; new-project notification routes; etc. **Also a fan-out target for §7.3.**
- `services/email/django_impl/test_handler.py:57,80,81,87` — tests that assert `email.to == [project.owner.email]` — these will need to be updated when notification fan-out changes.
- `services/notifications/django_impl/test_handler.py` — many `owner=` factory args and assertions referencing `owner.id`.

## API routers

- `api/routers/projects.py:182` — `if user and (project.owner == user or user.is_superuser):` — draft-visibility check (§4.3).
- `api/routers/my_projects.py:58,72,100,206,273,317,356` — `list_for_owner`, `owner_id=`, `get_for_owner`, `owner=request.auth` access checks (§4.1, §4.2, §6.1).
- `api/routers/my_review.py:231` — `select_related("owner")` (read-only, kept).
- `api/tasks/email.py:33,45` — `Project.objects.select_related("owner").get(...)` reads.

## API schemas

- `api/schemas/project.py:78` — `owner: PublicUserProfile` field on response (kept populated from creator after rename; new `creator` and `contributors` fields added in §7.1).
- `api/schemas/my_review.py:99` — `owner: UserResponse` on review-screen schema.

## Tests (factories, fixtures, assertions)

- `api/routers/test_my_projects.py` — many `owner=user`, `owner=` filter args, `_ready_draft(owner=user, ...)`.
- `api/routers/test_projects.py` — `ProjectFactory(owner=...)`.
- `api/routers/test_project_images.py:139` — `ProjectFactory(owner=user)`.

## Discovered call-site notes for §1.2

The notification/email fan-out (§7.3) lives in **two** places, not one:

1. `services/notifications/django_impl/handler.py::create_notifications_for_discussion` reads `discussion.project.owner` to determine the project-owner recipient.
2. `services/email/django_impl/handler.py` uses `project.owner` in multiple email-sending paths (admin notifications + project-state-change notifications).

§7.3 needs to update both. `api/tasks/email.py:33,45` also calls `select_related("owner")` but only uses the project itself afterwards — those select_related calls remain valid (we still want to prefetch the FK), they just become `select_related("creator")` after §8.
