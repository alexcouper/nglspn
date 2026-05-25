## Why

Naglasúpan needs to publish its product updates and competition results to the public web — not just to subscribers' inboxes. The plan (see `docs/superpowers/specs/2026-05-13-articles-following-news-design.md`) is to make Naglasúpan itself a Project on the platform, with the things we currently email about becoming Articles on that project. Subscribers continue to receive emails because they auto-follow the Naglasúpan project; visitors can read everything on the public site.

Phase 1 lays the *follow* foundations — without yet adding any user-visible new content. It introduces:

- A `Follow` primitive, scoped to Project. Each Follow owns per-channel × per-medium notification preferences (email switch, in-app switch).
- A `Channel` primitive: a named topic within a Project. Every Project gets one default channel ("Updates"). Naglasúpan additionally gets "Competition Winners" and "Product Updates" — the two existing email broadcast categories, 1:1.
- An `is_house_project` boolean on Project to identify Naglasúpan at runtime (used by auto-follow now; reused by `/news` highlights in Phase 5).
- A "Follow / Following" button on the project page that toggles a follow on/off — no settings popover yet (Phase 2 adds that).
- An auto-follow signal on user creation: every new user is automatically following the house project with all channels × mediums on.
- A one-shot data migration: every existing user is backfilled with a Follow row against the house project. The migration seeds per-channel email switches **from the legacy `email_opt_in_*` flags** rather than defaulting to on, so existing users' email preferences carry over.

Nothing fires notifications in this phase — Articles don't exist yet (Phase 3). Nothing changes about the existing email broadcast pipeline — it continues to read the legacy `email_opt_in_*` flags through Phase 2. Phase 1 is purely additive.

## What Changes

### Backend

- **Add** `is_house_project: BooleanField(default=False)` to the `Project` model. Enforce singleton-True via a DB partial unique constraint (`UNIQUE (is_house_project) WHERE is_house_project = TRUE`) plus a save-time guard for the SQLite test path.
- **Add** a `Channel` model: `id (UUID)`, `project (FK Project, CASCADE)`, `name (CharField, max_length=100)`, `created_at`, `updated_at`. Unique together: `(project, name)`.
- **Add** a `Follow` model: `id (UUID)`, `user (FK AUTH_USER_MODEL, CASCADE)`, `project (FK Project, CASCADE)`, `created_at`. Unique together: `(user, project)`.
- **Add** a `FollowChannelPreference` model: `id (UUID)`, `follow (FK Follow, CASCADE)`, `channel (FK Channel, CASCADE)`, `email_enabled (bool, default True)`, `in_app_enabled (bool, default True)`. Unique together: `(follow, channel)`.
- **Add** a `post_save` signal on `Project` (scoped to `created=True`) that creates a default "Updates" channel for the new project.
- **Add** a `post_save` signal on User (`created=True`, skipped for `is_system_user`) that creates a Follow on the house project with all channels × mediums set to on.
- **Add** a one-shot data migration that:
  - Identifies the existing Naglasúpan Project row (by slug; settled in the migration's `RunPython`) and sets `is_house_project = True`.
  - Creates "Competition Winners" and "Product Updates" channels on Naglasúpan if not already present.
  - Creates a default "Updates" channel on every other existing Project.
  - For every active non-system User, creates a Follow row against the house project and per-channel `FollowChannelPreference` rows. The email switches for "Competition Winners" and "Product Updates" are seeded from the corresponding legacy `email_opt_in_*` flags. The email switch for "Updates" defaults to True. All in-app switches default to True.
- **Add** `POST /api/projects/{slug}/follow` — idempotent; creates a Follow + default per-channel prefs if missing, returns the current follow state.
- **Add** `DELETE /api/projects/{slug}/follow` — idempotent; hard-deletes the Follow + cascaded preferences. Returns 204.
- **Modify** the project-detail response to include a boolean `is_followed` derived from the requesting user's follow state. Anonymous: always `false`.

### Frontend

- **Add** a `FollowButton` component (`src/web-ui/src/components/FollowButton.tsx`) labelled "Follow" / "Following". Click toggles state via the API. Hidden when the viewer is not authenticated.
- **Modify** the project page top-bar area to render the `FollowButton`.
- **Sweep** call sites after `npm run generate-types`.

### Explicitly out of scope (deferred to later phases)

- Any UI to view or edit the per-channel × per-medium switches (Phase 2).
- The global "My followed projects" settings page (Phase 2).
- Any change to the email broadcast send path — `services/email/django_impl/query.py::list_opted_in_for_broadcast_type` continues to read `email_opt_in_*` (Phase 3 flips it).
- Removal of the legacy `email_opt_in_*` fields (Phase 3).
- Article authoring or any notification firing (Phase 3).
- Project-owner channel-management UI (Phase 3).
- Following users, follower counts, follower lists (out of scope for v1).

## Capabilities

### New Capabilities

- `project-following`: the Follow / Channel / FollowChannelPreference primitives, the house-project flag, auto-follow on user creation, the one-shot data migration, the follow/unfollow API + button, and the legacy-flag → per-channel-preference seeding semantics.

## Impact

- **Django backend**: new models (`Channel`, `Follow`, `FollowChannelPreference`), a new boolean on `Project`, two new signal modules, three new endpoints, an addition to the project-detail response schema, schema + data migrations.
- **OpenAPI / generated types**: regenerated.
- **Web UI**: new `FollowButton` component, wired into the project page top bar.
- **Tests**: model uniqueness (`is_house_project` singleton), signal coverage (project create → channel; user create → follow), data-migration correctness against fixture users with mixed opt-in states, endpoint behaviour (idempotent POST, idempotent DELETE, GET reflects state), `FollowButton` component, Playwright golden path.
- **Unchanged**: the email broadcast pipeline (`async-broadcast-send` capability), the in-app notification system, all Article-related concepts (don't exist yet), the `notification_frequency` field, the `opt_in_to_external_promotions` field.
- **Rollback**: reverse migration drops the three new tables and the `is_house_project` column. Legacy `email_opt_in_*` flags are untouched throughout, so the legacy email pipeline remains operational at all times.
