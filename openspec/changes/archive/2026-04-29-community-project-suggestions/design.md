## Context

This change builds directly on `multi-contributor-projects`. That change established:

- A `ProjectContributor` join model with `role` (`OWNER` | `SUGGESTER`) and `full_edit: bool`.
- The rule that *any* contributor with `full_edit = True` has full write access to the project.
- A renamed `Project.creator` field (the original submitter, never changes).
- API responses that already include `creator` and `contributors[]`.

What's missing is the actual *use case* that motivated those primitives: a project that is suggested by a Naglasúpan user but owned by someone who isn't on the platform. To make that work cleanly, we need a non-loggable account to act as the OWNER, and a small amount of policy on top (don't enter competitions; don't email the system user; let users see their suggestions).

The seed-user approach is simpler than introducing an "owner is null" concept: it avoids null branches in queries, contributor-counting code, and serialisers. The `Community/Unowned` user is just a user — every place we already handle users handles it correctly except for two: login (must reject) and notifications (must skip). Both are short, localised changes.

The frontend change that consumes the new flag, hides the owner line for community-owned projects, and renders the new "Suggested" section is deliberately split out so this PR can land and be tested as a backend-only deployment.

## Goals / Non-Goals

**Goals:**
- Add `is_system_user` as a generic platform primitive — the Community/Unowned user is its first instance, but the flag is reusable for future system accounts (bots, automated tooling).
- Make the Community/Unowned user un-loggable on every code path that issues an authentication token, including obscure ones like password reset and email verification, so it cannot be hijacked.
- Allow community-suggested projects to flow through the existing draft → publish lifecycle unchanged in everything except competition entry.
- Expose a `/api/my-projects/suggestions` endpoint with a response shape compatible with the existing `/api/my-projects` listing, so the upcoming UI work is a small render-time addition rather than a new data path.

**Non-Goals:**
- Any frontend code (checkbox, my-projects "Suggested" section, top-bar rendering): out of scope for this change.
- Multiple system users today. Designed for, but not exercising, the multi-system-user case.
- A "claim this project" button or any flow that lets the absent real owner take over their listing — explicitly future work.
- Suggesting edits on an *existing* project owned by someone else — also future work.
- Differentiating role-level permissions (`OWNER` vs `SUGGESTER`) beyond what the `full_edit` boolean already controls. SUGGESTERs in this change have full edit, full stop.

## Decisions

### 1. Seed user, not nullable owner

Rejected: "make `ProjectContributor.user` nullable for OWNER rows on community projects".

Chosen: a real `Community/Unowned` user backed by `is_system_user = True`. Reasoning:

- All existing code that iterates contributors expects a real user; a nullable user would force a thicket of `if c.user is not None` branches.
- The seed user has a stable id, which we can reference from documentation, admin, and tests.
- Telling the system "this is owned by Community/Unowned" is more truthful than "this has no owner": the project *does* have an owner, just one outside the platform that we represent with a placeholder. That semantic shows up clearly in the UI later.

### 2. Reserved sentinel kennitala (`7777777777`)

Rejected: making `kennitala` nullable on User just for the system account, or auto-generating a unique sentinel per system user.

Chosen: hard-code `"7777777777"`. Reasoning:

- `User.kennitala` is `unique=True` and conceptually a real-life identifier. We don't want to weaken that constraint for one row.
- Real Icelandic kennitölur encode birth date and a checksum; ten of the same digit isn't a valid kennitala by construction, so the value can never collide with a real person's kt now or ever.
- One sentinel for one system user is fine. If we add a second system account, we pick another all-same-digit sentinel (`8888888888`, etc.) — it's not a scheme worth automating.

### 3. Login gate via auth backend, not via `is_active`

Rejected: setting `is_active = False` on the seed user.

Chosen: `is_active = True`, an unusable password, and an explicit `is_system_user` rejection in every authentication entry point. Reasoning:

- `is_active = False` already has a meaning in this codebase (account deactivated/disabled, see `inactive-account-exclusion` spec). Reusing it to mean "system account" would muddle reporting, lifecycle counts, and the existing inactive-account exclusions.
- Unusable password covers password login, but the codebase has at least three other auth paths: `EmailVerificationCode`, `PasswordResetCode`, and JWT issuance via the registration flow. A central `is_system_user` check at every token-minting entry point is auditable and self-documenting.
- The check belongs on the *issuance* side, not the request side, so an old token can't continue working after we add the flag (it can't, because the only way to get a token in the first place is via the login paths we're gating).

Concretely the gate is added to:
- The password-login endpoint (return the same generic auth error as a wrong password).
- The email-verification-code submit path (treat a system user's code attempts as expired/invalid).
- The password-reset-code submit path (likewise).
- Any JWT-issuance helper used post-registration (the seed user is created without going through registration, but defence in depth).

### 4. `community_owned` is a single boolean on the create request

Rejected: a new endpoint (`POST /api/my-projects/community`); an enum (`ownership: "self" | "community"`).

Chosen: adding an optional `community_owned: bool` (default `False`) to the existing create request. Reasoning:

- Two future ownership modes (group-owned, claimed-then-released) plausibly add more cases, but neither is in scope. Until we have ≥3 modes, a boolean is the right primitive.
- A separate endpoint would duplicate validation, slug logic, and image-upload coordination for what is otherwise the same create path.
- The default is `False`, so every existing client that doesn't know about the flag continues to work unchanged.

### 5. Competition-entry gate keys off OWNER's `is_system_user`

Rejected: a separate `Project.community_owned` boolean column; storing the gate decision on the project at create time.

Chosen: at publish time, check `project.contributors.filter(role=OWNER, user__is_system_user=True).exists()`. If true, skip the `competition.projects.add(project)` call. Reasoning:

- A separate column would let the project's "community-ness" drift from the actual contributor configuration. Source of truth should be one place, and contributors is already the place.
- The check is one query, scoped to a small related set per project. Performance is fine.
- Forward-compatible with the future "claim" feature: a real owner replacing the system user as OWNER causes future operations on that project to start treating it as an owned project automatically — no extra column to update.

### 6. `/api/my-projects/suggestions` is a sibling of `/api/my-projects`

Rejected: returning suggestions inside the existing `/api/my-projects` response under a new key.

Chosen: a separate endpoint with the same response shape. Reasoning:

- The existing endpoint returns a flat list. Adding a key would either break the contract or require a wrapper object that's awkward for everyone.
- The two lists have similar but not identical filters (creator vs SUGGESTER role) and the upcoming UI may paginate them independently.
- Frontend can call them in parallel cheaply.

### 7. Notification system-user filter is one-line

The existing fan-out in `apps/notifications/` (introduced in the previous change) iterates `project.contributors.filter(full_edit=True)`. We add `.exclude(user__is_system_user=True)`. That's the entire change. Existing dedupe logic is unaffected.

## Risks / Trade-offs

- **[Risk] A future code path accidentally treats the system user like a real one** (e.g. a "send weekly summary to all users" task emails the seed account). → Mitigation: the `is_system_user` field is queryable, and we add a single `User.exclude_system_users()` queryset helper as the recommended way to filter recipient lists. Adoption is opportunistic; an audit task is included to grep current bulk-recipient code.
- **[Risk] Login backend forgets to gate one path.** → Mitigation: the implementation tasks list every known auth entry point explicitly, and a single shared check function (`reject_system_user(user)`) is reused at each. Tests assert that login fails for the seed user via every path.
- **[Risk] The `community_owned` default flips by accident in a future API change.** → Mitigation: default `False` is the safer side (a missed flag means the project is *attributed to the submitter*, not attributed to a non-existent stranger). Tests pin the default.
- **[Trade-off] The seed user appears in admin user lists and could be selected in pickers.** → Acceptable for now. Admin templates and any user-picker the codebase has can filter on `is_system_user=False` opportunistically. The risk of an admin clicking it is low and the consequences (assigning something to the seed) are reversible.
- **[Risk] Notifications dedupe behaves oddly when the same user is both SUGGESTER and discussion creator.** → Already covered by the existing dedupe rule from the previous change; SUGGESTERs are reachable via the contributor branch and the discussion-creator branch and get one notification.
- **[Risk] Renaming `info` to "description" semantically.** → The User model's `info` field is being repurposed to carry the seed-user description. This is fine for a single seed; we don't introduce a new field. If we later want a user-visible "description" in the admin, we can rename then.

## Migration Plan

This change ships as a single jj change (it's all backend, all internally consistent, and the frontend that exposes it ships separately).

1. Migration: add `User.is_system_user` (default `False`).
2. Migration / management command: idempotently create the Community/Unowned user. The migration is the simpler choice because it executes automatically on deploy. The management command (`python manage.py ensure_community_user`) is added as a fallback / test-fixture utility that wraps the same logic.
3. Auth backend: add the `reject_system_user` check; wire it into password login, email verification, password reset, and JWT issuance.
4. Service: extend project create signature with `community_owned: bool = False`; add the contributor allocation branch; extend publish to check OWNER's `is_system_user`.
5. API: extend create schema with `community_owned`; add `/api/my-projects/suggestions` route + handler.
6. Notifications: add `.exclude(user__is_system_user=True)` to the fan-out queryset.
7. `make extract-openapi` and `npm run generate-types`.
8. `make ci`.

Roll-back: the migration adds a column with a default, which is reversible. The seed user's data migration adds at most one row; the reverse direction can leave it (it's harmless without the gating code). The auth-backend changes are additive — removing them restores prior behaviour.

## Open Questions

- Final email address for the seed account. Options: `community@naglasupan.is`, `community-unowned@naglasupan.is`, `noreply+community@naglasupan.is`. Defaulted to `community@naglasupan.is` in implementation tasks; trivial to change in the seed migration.
- Should `/api/my-projects` *exclude* projects where the calling user is only a SUGGESTER, or include them under the same list? Defaulted to **exclude**: the existing endpoint stays "projects I created", suggestions are only on the new endpoint. UI work in the next change can choose to merge or keep separate.
- Should the seed user's password be left literally unset (Django's "unusable password" sentinel), or set to a random unguessable value at creation? Defaulted to the standard `set_unusable_password()` API; functionally identical and idiomatic.
