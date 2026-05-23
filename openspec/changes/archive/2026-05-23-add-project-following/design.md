## Context

This implements Phase 1 of the design at `docs/superpowers/specs/2026-05-13-articles-following-news-design.md`. The design covers six phases; Phase 1 lays the data-model foundations for following, channels, and the per-channel notification preference store, without yet exposing the preferences in the UI or wiring them to any notification firing path.

Key constraints from the design that shape this change:

- Existing users' email preferences must carry over (no inbox regression). They had two flags: `email_opt_in_competition_results` and `email_opt_in_platform_updates`. These are seeded into the new per-channel preference rows for the Naglasúpan follow, rather than defaulted to on.
- The legacy email broadcast pipeline keeps reading those flags through Phase 2. Phase 1 does not touch the send path.
- Auto-follow on user creation needs a stable way to find "the Naglasúpan project". A new `is_house_project` boolean on Project (default `False`, exactly one `True`) serves this. The reserved highlight slot on `/news` in Phase 5 will reuse the same flag.

## Goals / Non-Goals

**Goals:**

- Stand up the `Follow`, `Channel`, and `FollowChannelPreference` models.
- Seed channels per project; seed Naglasúpan's two channels matching legacy email categories 1:1.
- Backfill Follow rows + preferences for existing users from legacy flags.
- Auto-follow new users to the house project.
- Render a working Follow/Unfollow button on project pages.

**Non-Goals:**

- Any UI for the per-channel × per-medium preferences (deferred to Phase 2).
- Notification firing (deferred to Phase 3 — no Article model yet).
- Changing the email broadcast send path (deferred to Phase 3).
- Project-owner channel management UI (deferred to Phase 3).
- Any `/news` page work (Phase 5).
- Following users (out of scope for v1).

## Decisions

### 1. `is_house_project` boolean on Project, not a hardcoded slug

Auto-follow needs to find the Naglasúpan project at runtime. Options considered: hardcode slug, hardcode UUID, env var, boolean flag.

We use a boolean. The flag is self-describing (a future developer reading the model sees what it means), survives slug renames, and works across environments (dev/staging/prod) without an env-specific config. The DB partial unique constraint prevents two rows being flagged True.

Postgres supports partial unique indexes directly:

```sql
CREATE UNIQUE INDEX project_house_singleton
  ON projects (is_house_project) WHERE is_house_project = TRUE;
```

SQLite (test/dev) doesn't enforce partial unique indexes the same way, so we also add a save-time guard on `Project.save()` that raises if `is_house_project=True` is being set on a row when another row already has it. The guard is also safe in Postgres — it just runs slightly before the DB constraint.

### 2. Three models, not one

Follow and Channel are separate concepts that the design treats independently:

- Channels exist regardless of follows. A project always has channels — even an unfollowed project.
- A Follow exists regardless of channels. The mediums (email, in-app) are global to the platform; the channels are per-project.

`FollowChannelPreference` is the join between a (Follow, Channel) pair carrying the two switches. This three-model layout keeps each model with a clear independent reason to exist, and the per-(Follow, Channel) row can carry future fields (e.g. per-channel cadence in v2).

```
   ┌────────┐         ┌─────────────────────┐         ┌─────────┐
   │  User  │────────▶│       Follow        │◀────────│ Project │
   └────────┘         └──────────┬──────────┘         └────┬────┘
                                 │                         │
                                 ▼                         ▼
                  ┌─────────────────────────┐         ┌─────────┐
                  │ FollowChannelPreference │────────▶│ Channel │
                  │  email_enabled          │         │  name   │
                  │  in_app_enabled         │         └─────────┘
                  └─────────────────────────┘
```

### 3. App location: a new `follows` app

The new models don't fit cleanly in `apps/projects` (would inflate an already-large app and the Follow is owned by the user) or `apps/users` (Channels are project concepts). Creating a new `apps/follows` app keeps the related models together and gives the auto-follow signal a sensible home. `Channel` also lives here — it exists only because Follows need it.

### 4. Migration seeds preferences from legacy flags

The design's Phase 1 backfill must produce the same effective email subscription state for existing users — they should not start receiving emails they had opted out of, nor stop receiving ones they had opted in to.

```python
for user in User.objects.filter(is_active=True, is_system_user=False):
    follow, _ = Follow.objects.get_or_create(user=user, project=naglasupan)
    FollowChannelPreference.objects.update_or_create(
        follow=follow, channel=competition_winners,
        defaults={
            "email_enabled": user.email_opt_in_competition_results,
            "in_app_enabled": True,
        },
    )
    FollowChannelPreference.objects.update_or_create(
        follow=follow, channel=product_updates,
        defaults={
            "email_enabled": user.email_opt_in_platform_updates,
            "in_app_enabled": True,
        },
    )
    FollowChannelPreference.objects.update_or_create(
        follow=follow, channel=updates,
        defaults={"email_enabled": True, "in_app_enabled": True},
    )
```

The "Updates" channel doesn't have a legacy correlate — it defaults to `email_enabled=True`. This is harmless because: (a) Naglasúpan's Phase 4 content backfill targets the two named channels, not Updates; (b) the email send path doesn't read these preferences until Phase 3.

In-app switches default to True because there's no prior signal to migrate from (today's in-app notifications don't have a per-category opt-in).

### 5. Channel-seeding signal is project-creation only

Newly-created Projects get a default "Updates" channel via a `post_save` signal scoped to `created=True`. We don't recompute on every save — seeding is one-time at create.

`Project.objects.bulk_create()` skips signals; the existing codebase's bulk-create paths (fixtures, tests) invoke the seeding helper explicitly or rely on test factories that handle it.

### 6. Auto-follow signal on user creation, not migration

For new users (post-deploy), the auto-follow runs from a `post_save` signal on User (`created=True`, `is_system_user=False`). For existing users, the one-shot data migration does the same work. Both paths converge on the same helper — written once, called from both places.

System users (community user, etc.) skip auto-follow: they are not subscribers and should not receive notifications.

### 7. Unfollow is hard delete

The design specifies hard delete. Re-following starts fresh with defaults-on. Soft delete would preserve prior tweaks across an unfollow/re-follow cycle, but adds a `deleted_at` column and complicates every query. The user's intent on unfollow is "remove me"; honour it.

`FollowChannelPreference` rows cascade-delete from Follow.

### 8. API shape: follow lives on the project, not standalone

The endpoints are nested under the project — `POST /api/projects/{slug}/follow` — rather than a standalone `/api/follows` resource. Following is always *of* a project; this matches the URL semantics. The DELETE method on the same URL is idiomatic for removing the follow.

We don't add a GET endpoint at this URL in Phase 1 — instead, the project-detail response is augmented with an `is_followed` boolean. This avoids an extra round-trip on the project page and matches existing patterns (the project-detail response already carries derived per-user fields).

### 9. POST and DELETE are both idempotent

A double-click on the Follow button is the common failure mode. POST returns the existing follow if one already exists; DELETE returns 204 even when there is no follow row. Same for offline / retry scenarios.

## Risks / Trade-offs

### Risk: greenfield dev DB without the data migration

The data migration that flips `is_house_project=True` runs against an existing row identified by slug. On a brand-new dev DB seeded from scratch (no prod data dump), the Naglasúpan Project row may not exist when the migration runs. The migration must no-op cleanly in that case; the auto-follow signal must tolerate the house project being absent (skip silently, log a warning).

The seed/fixture path that creates the Naglasúpan project on dev DBs should set `is_house_project=True` at creation. Document this in the seed runbook.

### Risk: ordering between schema and data migrations

The schema migration adds the column and the new tables; the data migration backfills. Django runs them in dependency order, so this is fine as long as the data migration depends on the schema migration. Both live in the `follows` app's migrations directory; the data migration depends on the projects-app migration that adds `is_house_project`.

### Risk: large user table

The data migration iterates every active non-system user, creating up to four rows each (Follow + three FollowChannelPreferences). At present this is a small user base, but the migration uses `bulk_create` in batches of 1000 to keep transaction size bounded.

### Trade-off: signal vs. explicit call for auto-follow

A signal handler is "magic" — easy to miss. The alternative is to call an explicit helper from the user create flow (`apps/users/views.py` and any management commands).

We choose the signal because: (a) there are multiple user-creation entry points (registration view, admin, management commands, test factories) and centralising in a signal avoids missing one; (b) test factories that need to bypass the side-effect can use Django's `mute_signals` context manager.

## Migration Plan

The change ships in one deploy:

1. Schema migrations:
   - `projects`: add `is_house_project` boolean with partial unique constraint.
   - `follows`: create `Channel`, `Follow`, `FollowChannelPreference` tables.
2. Data migration (lives in the `follows` app, depends on the projects-app migration above):
   - Flip `is_house_project=True` on the Naglasúpan row (identified by slug; if not found, log a warning and skip — dev/test DB case).
   - Seed channels: every existing Project gets "Updates"; Naglasúpan additionally gets "Competition Winners" and "Product Updates".
   - For every active non-system User, create the Follow + per-channel-preference rows for the house project, seeded from legacy flags.
3. Code: signals (project channel seed, user auto-follow), endpoints, frontend button.

**Rollback**: a reverse migration that drops the three new tables and the `is_house_project` column. The legacy `email_opt_in_*` flags are untouched throughout, so rollback is safe — the email pipeline continues from the legacy flags as if nothing happened.
