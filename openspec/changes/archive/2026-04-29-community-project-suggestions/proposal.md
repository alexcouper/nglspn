## Why

Naglasúpan currently only accepts projects whose creator is also the project's owner — i.e. someone with a Naglasúpan account who has made the thing themselves. The community has obvious appetite for *suggesting* projects made by people outside the platform (a friend's app, a student's portfolio, an Icelandic dev-tool whose author isn't on the site). Today, the only way to surface those is for the creator-of-record to also be a Naglasúpan user, which is wrong on two counts: it overstates ownership (the suggester didn't make it) and it inflates the suggester's competition standing (community-suggested work shouldn't compete on equal footing with author-submitted work).

This change adds backend support for *community-suggested* projects on top of the contributor model introduced by `multi-contributor-projects`. A non-loggable system user owns the project; the human submitter is recorded as a `SUGGESTER` contributor with full edit rights; the project goes through the normal draft → publish flow but is excluded from competition entry; and the API gains a way to list "projects I've suggested" alongside "projects I own".

The frontend (checkbox, top-bar rendering, my-projects section) is intentionally split into a follow-on change so this one stays focused on the data model and API surface.

## What Changes

- **Add** a `User.is_system_user: bool` field (default `False`) to mark accounts that exist for the platform's own bookkeeping rather than human use.
- **Add** an authentication backend gate so that any user with `is_system_user = True` cannot complete login by any path (password, email verification code, password reset code, JWT issuance).
- **Add** a Django management command and matching data migration that ensures a single `Community/Unowned` system user exists with: `email = "community@naglasupan.is"` (or an equivalent reserved address — finalised during implementation), `kennitala = "7777777777"` (a sentinel that never occurs in real life), `is_system_user = True`, an unusable password, `info` set to `"Projects submitted by community members but owned by people outside of Naglasúpan."`, and `is_active = True`. The seed is idempotent.
- **Add** an optional `community_owned: bool` field on the project-creation request (`POST /api/my-projects`) that defaults to `False`. When `True`, the project is created with `creator = <calling user>` and two `ProjectContributor` rows: `OWNER = Community/Unowned (full_edit=True)` and `SUGGESTER = <calling user> (full_edit=True)`. When `False`, behaviour is unchanged from the previous change.
- **Modify** the publish path: if any `ProjectContributor` with `role = OWNER` on the project belongs to a user with `is_system_user = True`, the project SHALL NOT be added to a currently-open competition. All other publish behaviour (state transition, slug, notification email) is unchanged.
- **Modify** notification fan-out: the contributor-level recipient set established in `multi-contributor-projects` is filtered to exclude users with `is_system_user = True`. (In practice: don't email the Community/Unowned account.)
- **Add** `GET /api/my-projects/suggestions` returning the list of projects on which the calling user is a `SUGGESTER` contributor (with `full_edit = True`). Response shape mirrors the existing `/api/my-projects` listing so the frontend can reuse rendering. The list MAY be empty.
- **Regenerate** OpenAPI spec and TypeScript types for the new endpoint, the new request flag, and the new model field.

## Capabilities

### New Capabilities
- `system-users`: the `is_system_user` flag, login gating, and the Community/Unowned seed user.
- `community-submissions`: the `community_owned` create flag, the contributor allocation rule, the competition-entry gate at publish time, and the `/api/my-projects/suggestions` endpoint.

### Modified Capabilities
- `project-draft-publish`: the publish behaviour gains a competition-entry exclusion when the project is community-owned.
- `notifications`: the contributor recipient set is filtered to exclude system users.

## Impact

- **Django models**: `User.is_system_user` field + migration; data migration / management command for the Community/Unowned seed user.
- **Auth backends**: existing password and code-based auth paths gain an `is_system_user` rejection so login attempts against the system account fail uniformly. Token issuance also rejects system users.
- **Django services**: `services/project/django_impl/handler.py::create` accepts a `community_owned` parameter and, when true, attaches OWNER+SUGGESTER contributors accordingly. The publish path consults the contributors to decide competition entry. `services/users/` (or a new helper) provides a typed accessor for the seed user.
- **Django API**: `api/schemas/project.py` adds the optional `community_owned` flag; `api/routers/my_projects.py` surfaces the new `/suggestions` endpoint; `api/tasks/email.py` and notification fan-out filter out system users.
- **OpenAPI / web-ui types**: `make extract-openapi` + `npm run generate-types`; the web-ui change that consumes these types is the *next* change.
- **Tests**: model-level tests for the flag and login gate; service tests for the create + publish branches; API tests for the new endpoint and the new flag; migration test for the seed user.
- **Out of scope**: any frontend rendering or form changes (deferred to `community-suggestions-ui`); the future "claim" button; suggesting edits on existing projects; edit history / version snapshots; unique behaviour for the SUGGESTER role beyond what `full_edit` already grants.
