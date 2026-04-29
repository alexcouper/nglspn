## Context

`Project.owner` is a single FK to `User`. It serves three conflated roles today:

1. **Identity** — the human who originally submitted the project.
2. **Access control** — the only user who can edit, publish, delete, or resubmit the project.
3. **Notification target** — the user we email when something happens to the project.

Two upcoming changes need these roles separated:

- **Community submissions** introduce projects whose "owner" is a non-loggable system user (`Community/Unowned`) but whose actual editor is the human submitter (a `SUGGESTER`).
- **Group-owned projects** (later) need multiple humans with full edit rights on the same project.

Trying to model either feature with a single owner FK forces awkward branches throughout the codebase. This change collapses those branches into one rule — *"can this user edit this project?"* — backed by a real M:N table.

The current write-access pattern is repeated across:
- `api/routers/my_projects.py` — four `get_object_or_404(Project, id=..., owner=request.auth)` sites.
- `api/routers/projects.py:182` — `project.owner == user or user.is_superuser` to decide whether a draft is visible to the requester.
- `services/project/django_impl/handler.py` — `update`, `delete`, `resubmit`, `publish` all take `owner_id` and look projects up by it.
- `services/project/django_impl/query.py` — `get_for_owner` / `list_for_owner` query helpers.

Notifications today target `project.owner` directly (e.g. `api/tasks/email.py`'s discussion notification path). That single target needs to fan out.

## Goals / Non-Goals

**Goals:**
- Establish a `ProjectContributor` join model that becomes the single source of truth for write access.
- Preserve existing API response shape so the current frontend keeps working without code changes.
- Rename `owner` → `creator` everywhere it appears so the conflation is impossible to recreate by accident.
- Backfill existing data losslessly — every current owner becomes an `OWNER` contributor with `full_edit = True`.
- Lay groundwork for the next two changes (community submissions, then group-owned) without anticipating their UI.

**Non-Goals:**
- Any frontend changes. The web UI continues to read `creator` (populated from old `owner`) for the existing "by …" rendering.
- Adding `is_system_user` or the Community/Unowned seed user — that's the next change.
- Enforcing competition gating based on owner identity — also next change.
- Adding role-based or per-field permissions beyond a single `full_edit` boolean. Future changes can refine, but every contributor with `full_edit = True` has identical write rights for now.
- Edit history / version snapshots — explicitly deferred to a fast-follow.

## Decisions

### 1. Join model carries `role` *and* `full_edit`, not just `role`

Rejected: "use `role` to gate access (e.g. only `OWNER` can edit)."

Chosen: a separate `full_edit` boolean. Reasoning:

- The forthcoming community-submissions feature wants `SUGGESTER` contributors to have full edit rights on day one (because the original owner doesn't exist on the platform yet). Tying access strictly to `role` forces "well, suggesters can also edit" branches everywhere.
- Later, when an owner *claims* a community project, they'll want to revoke edit rights from a suggester without deleting the row. A boolean toggle on the relationship handles that cleanly.
- `role` therefore becomes informational / for-display ("submitter", "owner", future "invitee"), while `full_edit` is the access primitive.

This keeps the access-control predicate tiny: `ProjectContributor.objects.filter(project=p, user=u, full_edit=True).exists()`.

### 2. Keep `Project.creator` as a real FK, not derive it from contributors

Rejected: "drop the dedicated FK and compute `creator` from contributors (e.g. earliest contributor, or contributor with `is_creator=True`)."

Chosen: rename `owner` → `creator` and keep the FK on `Project`. Reasoning:

- `creator` is a *historical fact* — who first submitted this project — and it never changes after creation. Storing it as a column is cheap and unambiguous.
- For community-submitted projects in the next change, `creator` and the OWNER-contributor are deliberately *different* users (the suggester vs. the system user). Trying to encode that on a single join table makes the contributor table semantically overloaded.
- Querying "show me projects I created" stays a one-column index lookup; no join required.

### 3. Big-bang rename `owner` → `creator`

Rejected: "shim layer — keep `owner` as a property, add `creator` as the canonical field."

Chosen: rename everywhere in one change. Reasoning:

- A shim invites future contributors to keep using `owner` because it works. The whole point of the rename is to break that habit.
- Django's `RenameField` migration is mechanical and safe for a single-FK field; downtime is unaffected.
- We commit this change as two reviewable jj changes: (a) introduce the contributor model + access-control swap (still using `owner`), then (b) the pure rename. The rename diff is large but trivially reviewable on its own.

### 4. Data migration is idempotent and runs in the same migration as the model add

A single migration `XXXX_add_project_contributors.py` does:

1. `CreateModel` for `ProjectContributor`.
2. `RunPython` data migration that, for every `Project`, inserts `ProjectContributor(project=p, user=p.owner, role=OWNER, full_edit=True)` if no row already exists for `(p, p.owner)`.

Coupling them prevents the brief window where the model exists but is empty. The reverse migration drops the table; data backfill is naturally undone.

The rename migration is a separate Django migration created on top of the model add (in the second jj change). `RenameField('Project', 'owner', 'creator')` is reversible and trivial.

### 5. API additive, not breaking

Existing fields on `/api/projects/{id}` and `/api/projects/me` are preserved. New fields:

- `creator: UserSummary` — replaces the implicit "owner" semantics that the FE currently reads. For all backfilled projects, `creator` equals what the FE used to read, so nothing breaks.
- `contributors: list[ContributorSummary]` where each item is `{user: UserSummary, role: "OWNER" | "SUGGESTER", full_edit: bool}`.

If `schemas/project.py` currently includes an `owner: UserSummary` field, we keep it for one cycle and populate it from `creator` to avoid breaking the deployed FE during rollout. The next change's frontend update will consume `creator` and `contributors[]` instead, after which the duplicated `owner` field can be removed (out of scope here).

We regenerate the OpenAPI spec and TypeScript types so the FE has the new types ready when it needs them.

### 6. Notification fan-out targets `full_edit = True` contributors

Anywhere we previously looked up `project.owner` to send a notification or email (e.g. discussion notifications, project-state-change emails), we now iterate every contributor on the project where `full_edit = True` and notify each of them. With backfilled data this is a 1:1 swap (one contributor per project); the change matters only when the next change starts adding multiple contributors.

We deliberately do *not* filter by `is_system_user` in this change, because the field doesn't exist yet. Once it does (next change), the filter is added in one place.

## Risks / Trade-offs

- **[Risk] Missed write-access site after the rename.** A `project.owner == user` check buried in a template, signal, or helper that we miss leaks into the new world looking like an explicit equality check. → Mitigation: grep audit for `\bowner\b`, `owner_id`, `list_for_owner`, `get_for_owner` across `apps/`, `api/`, `services/`, and tests as a tasks-checklist step before the rename migration; CI runs the existing test suite which exercises every owner-gated route.
- **[Risk] Data migration runs on production with stale rows.** A pre-existing project with a deleted owner FK would crash the migration. → Mitigation: the migration filters `Project.objects.exclude(owner__isnull=True)` defensively; in current schema `owner` is non-nullable so this is paranoia, but cheap.
- **[Trade-off] Two new fields on the API response increases payload size.** `contributors[]` adds a list to every project response. → Acceptable: the list is short (1 element for all backfilled projects), and the FE benefits from having the data ready when it starts rendering the new project header in change 3.
- **[Risk] The deferred FE work means `contributors[]` is unused for an unknown amount of time.** → Acceptable: the field is documented in OpenAPI, types are generated, and the FE in change 3 picks it up. The dormant period is short.
- **[Risk] Writing to the contributor table from many places makes invariants slip.** Specifically the invariant "every project has at least one OWNER contributor with `full_edit=True`." → Mitigation: project creation in the service handler is the only place that inserts a contributor in this change. A future signal or check-constraint can guard the invariant if more insertion paths appear; not needed yet.

## Migration Plan

The change ships as **two jj changes** within this OpenSpec change:

**jj change 1 — contributor model and access-control swap**
1. Add `ProjectContributor` model.
2. Migration: create table + data-migrate existing owners as `OWNER` contributors.
3. Add permission helper (e.g. `services/project/permissions.py::user_can_edit_project`).
4. Replace every owner-equality access check with the helper. **Field is still called `owner` in this change.**
5. Update notifications and emails to fan out across contributors with `full_edit=True`.
6. Update `api/schemas/project.py` to include `contributors[]` (no rename yet).
7. Run `make extract-openapi` + `npm run generate-types`.
8. Tests for the helper, the migration, and updated permission scenarios.

**jj change 2 — rename `owner` → `creator`**
1. Django `RenameField('Project', 'owner', 'creator')` migration.
2. Mechanical rename across `apps/`, `api/`, `services/`, tests, fixtures, admin.
3. Service interfaces: `list_for_owner` → `list_for_creator`, `get_for_owner` → `get_for_creator`, `owner_id` → `creator_id` in DTOs and parameter lists.
4. Add `creator: UserSummary` to API responses; keep `owner: UserSummary` populated from `creator` for one cycle (optional safety; see Decision 5).
5. Re-run `make extract-openapi` + `npm run generate-types`.
6. Full test pass.

Roll-back: each migration is reversible (`migrate <app> <previous>`); jj changes can be backed out individually. The access-control swap is the only behaviour change — if a problem surfaces post-deploy, reverting jj change 1 restores the equality checks.

## Open Questions

- Should `ContributorSummary.user` be a full `UserSummary` (id, name, email-fragment, etc.) or just `{id, display_name}`? Defaulted to "the existing UserSummary serializer the codebase already uses" so the FE doesn't need a new type, but worth confirming during implementation.
- Is there a meaningful `ordering` on `ProjectContributor`? Probably "OWNER first, then SUGGESTER, then by created_at" so the upcoming top-bar UI doesn't need extra logic. Defaulted to that.
