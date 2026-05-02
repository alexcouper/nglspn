## Context

Tip-off projects already exist behaviourally. The submit form sends `community_owned: true`, the backend writes the OWNER (system user) + SUGGESTER (calling user) pair, the API exposes `community_owned: bool` on responses, and the project detail page renders a "Community Tipoff" pill. The backing query reads `community_owned` as a per-row annotation computed from a join: does this project have an OWNER contributor whose user has `is_system_user = True`?

This change addresses the gap between *recording* a tip-off and *surfacing* it. Three things are missing:

1. A queryable, indexable representation. Annotation-driven filtering forces every consumer (admin filter, list endpoint, etc.) to either re-apply the annotation or hand-write the same join. Indexable column-level filtering is materially simpler and faster.
2. Distinguishing presentation. Today, tip-offs are visually marked only with a small badge inside a generic list (Discover → New Arrivals) and an unexplained pill on the detail page. There is no path for a project's actual maker to learn "this is yours; here's how to claim it".
3. Operational visibility. Admin staff cannot filter or scan for tip-offs in the Django admin, and the new-project notification email reads identically for self-owned and tip-off submissions.

## Goals / Non-Goals

**Goals:**
- Replace the `community_owned` annotation with a denormalized `is_community_tipoff` column kept in sync via signals on `ProjectContributor`.
- Rename the public API field to `is_community_tipoff` everywhere it appears.
- Move tip-offs out of "New Arrivals" on the Discover page into a dedicated "Recent Tipoffs" section, with a tooltip explainer.
- Add tooltip explainers (with the site contact email) on both the Discover section heading and the existing detail-page badge.
- Make tip-off status visible in the Django admin list and detail views, and indicate it in the new-project notification email.

**Non-Goals:**
- A "claim this project" UI flow.
- Any change to how the OWNER + SUGGESTER rows are written at submit time (already correct).
- Pagination, infinite scroll, or filtering controls on the new Recent Tipoffs section.
- A background reconciliation job to reassert column ↔ contributor agreement.
- A redesign of the badge or pill itself (colour, icon, label) beyond wrapping it in the tooltip.

## Decisions

### 1. Denormalized column, contributor relationship remains source of truth

The `ProjectContributor` rows do real work — they gate edit permissions and surface "Community" as the credited owner. We can't drop them. So `Project.is_community_tipoff` is a one-way derived cache:

```
   ProjectContributor changes (truth) ──signals──▶ Project.is_community_tipoff (cache)
```

`Project.recompute_community_tipoff()` is the canonical recompute. It runs the same logic the annotation runs today: `is_community_tipoff = self.contributors.filter(role=OWNER, user__is_system_user=True).exists()`. It writes `self.is_community_tipoff` and saves with `update_fields=["is_community_tipoff"]` to avoid touching unrelated columns or firing unrelated signals.

### 2. Sync via Django signals, not save() overrides

`Project.save()` is the wrong hook: contributors are written *after* the project (they FK to it), so at the moment of project save the contributor rows may not exist. The reliable hook is on `ProjectContributor` — every contributor add/remove may flip the project's tip-off status, so:

- `post_save` on `ProjectContributor` calls `instance.project.recompute_community_tipoff()`.
- `post_delete` on `ProjectContributor` calls the same.

The signal handler is idempotent: it always calls recompute, which itself is a cheap exists-check + conditional write. Same project saved twice in a transaction is fine.

**Bulk ORM operations bypass signals.** `bulk_create`, `qs.update()`, `qs.delete()` skip signals by design. There are very few such paths in this codebase that touch `ProjectContributor`. Callers using bulk operations on contributors SHALL invoke `recompute_community_tipoff()` explicitly. We do not add a periodic reconciliation job.

### 3. Field name `is_community_tipoff` everywhere

We could keep the API field `community_owned` and only rename internally — but two-name systems rot. The single rename across the model, schemas, OpenAPI, and frontend is cheap to do once and saves indefinite future confusion. The naming aligns with the user-facing terminology ("Community Tipoff", "Recent Tipoffs", "tip-off project").

### 4. New endpoint `GET /api/projects/recent-tipoffs`, mirroring `/new-arrivals`

The existing convention is one endpoint per Discover surface (`/new-arrivals`, `/featured`, etc.). A new endpoint matches that convention, has its own queryset (`Project.objects.filter(is_community_tipoff=True).order_by("-created_at")[:N]`), can be cached independently, and keeps the call site on the frontend a one-line addition. The alternative — a query parameter on `/new-arrivals` — would mix concerns and force every existing caller to consider a new flag.

`list_new_arrivals` is updated to add `.filter(is_community_tipoff=False)`. New Arrivals SHALL no longer return tip-offs in any case.

### 5. Tiny custom Tooltip component, no new dependency

We use the tooltip in two places (Discover section heading, detail-page badge). Pulling in `@radix-ui/react-tooltip` for two uses is overkill. The custom component handles:

- Hover (desktop): mouseenter/leave shows/hides.
- Touch: tap toggles open; tap outside closes.
- Keyboard: focus shows; blur or Escape hides.
- Screen reader: trigger has `aria-describedby` pointing at the tooltip body, which is rendered with `role="tooltip"`.

Implementation lives in `src/web-ui/src/components/Tooltip.tsx`. Two props: `children` (the trigger) and `content` (the tooltip body, string or node).

### 6. Single source of truth for the tooltip copy

The same string appears on the Discover section heading and on the detail-page badge:

> "Community tip-offs are projects spotted and added by someone other than their makers. If this is your project, get in touch: alex@naglasupan.is"

We hold this in one constant alongside `SITE_EMAIL` so the email is composed once: `const TIPOFF_EXPLAINER = \`Community tip-offs are projects spotted and added by someone other than their makers. If this is your project, get in touch: ${SITE_EMAIL}\``. Both call sites consume the constant.

### 7. Site email lives in `src/web-ui/src/lib/constants.ts`

A small constants module with `SITE_EMAIL = "alex@naglasupan.is"`. The existing `/about/contact/page.tsx` migrates to read from this constant. Future contact-email touchpoints consult the same constant. We don't introduce a `NEXT_PUBLIC_SITE_EMAIL` env var: the address is public information, no per-environment override is needed, and a single in-repo constant is the simplest source of truth.

### 8. No per-card pill in the Recent Tipoffs section

Once tip-offs are isolated in their own section, the per-card "Tipoff" badge is redundant — the section heading already conveys the category. We drop the badge from both the hero/large card layout and any smaller cards inside Recent Tipoffs. New Arrivals also no longer renders the badge (no tip-offs reach it). The badge component itself remains in use on the project detail page banner.

### 9. Email: subject branch, single body line

Today: subject is "New project submitted - Naglasúpan", body lists project title, tagline, description, owner name, owner email, logo. After: when the submitted project is a tip-off, the subject SHALL be "New tip-off submitted - Naglasúpan" and the body SHALL include a single sentence at the top of the project block stating "This is a community tip-off — the submitter is not the project's maker." Self-owned projects render unchanged. The handler passes `is_community_tipoff` into the template context; the template branches on it.

### 10. Admin: column + filter + read-only field

`list_display` gains `is_community_tipoff` (renders as a checkmark/cross). `list_filter` gains `is_community_tipoff`. The change page surfaces the field, read-only, in the "Ownership" fieldset alongside contributors. Read-only because the column is a derived cache; staff who want to flip a project's tip-off status edit the contributor list, which the signals pick up.

## Risks / Trade-offs

- **[Risk] Signal handler runs on every contributor write.** Each save/delete triggers a recompute. The recompute is one indexed `.exists()` query and at most one one-column update, so the cost is small, but it's a per-write tax. Acceptable: contributor writes are not on a hot path.
- **[Risk] Bulk ORM contributor operations diverge silently.** Mitigation: documented in the design as a known limitation; the few existing bulk paths (if any) call `recompute_community_tipoff()` explicitly.
- **[Risk] Public API rename is breaking.** All known consumers are in this repo; the renaming sweep covers them. External API consumers, if any exist, would need a heads-up — currently there are none.
- **[Risk] Tooltip on a small "?" affordance can be missed by touch users who don't realise it's tappable.** Mitigation: the "?" affordance has a visible hover/focus state and a tap target padded to the platform minimum.
- **[Trade-off] Two Discover endpoints instead of one parameterised endpoint.** Adds a small amount of code duplication; chosen for clarity (matches existing convention) and independent caching.

## Migration Plan

1. Add the `is_community_tipoff` column with a Django migration: `BooleanField(default=False, db_index=True)`.
2. Run a data migration that loops over `Project` and calls `recompute_community_tipoff()` (or inlines the equivalent query). Wrap in a transaction.
3. Wire up the `post_save` / `post_delete` signals on `ProjectContributor`. Register them in the relevant app config.
4. Update queries: replace `_community_owned_annotation()` callers with reads of the column. Delete the helper.
5. Update schemas: rename `community_owned` to `is_community_tipoff` in `ProjectCreate`, `ProjectResponse`, `DiscoverProjectResponse`, and any other schema. Regenerate OpenAPI.
6. Add the `recent-tipoffs` endpoint and `list_recent_tipoffs` service method. Update `list_new_arrivals` to exclude tip-offs.
7. Update admin: `list_display`, `list_filter`, fieldsets.
8. Update email handler + template: subject branch, body line.
9. Frontend: regenerate types. Sweep call sites for the renamed field.
10. Add `src/lib/constants.ts` and migrate `/about/contact`.
11. Add the `Tooltip` component.
12. Add `RecentTipoffsSection`. Wire into `DiscoverView`. Drop the badge in `NewArrivalsSection`.
13. Wrap `TipoffBadge` with `Tooltip`.
14. Run `make ci` from project root; lint + tests + Playwright golden paths.

Roll-back: revert the migration (drops the column), revert the signal registration, revert the schema renames and regenerate. The annotation helper can be restored from git history if a partial revert is needed.

## Open Questions

- Should the tooltip on the section heading and the tooltip on the badge be word-for-word identical, or should the badge tooltip drop the leading definition and just say "If this is your project, get in touch: alex@naglasupan.is"? Defaulted to **identical** (single constant) for simplicity; can split later if user testing suggests it.
- Final placement of the "Recent Tipoffs" section on Discover. Placed **directly below Winners** (and above the category rows). Tip-offs are user-submitted projects we can't yet endorse the same way we do approved or competition-winning projects, so they sit further down the page where curation pressure is lower.
- Hide-when-fewer-than-N threshold for Recent Tipoffs. Set to **N = 3** so the row reads as a meaningful collection rather than a pair of stranded cards. With one or two tip-offs in the system the section stays hidden and they continue to be discoverable through the project detail pages and the my-projects "Suggested" view. The constant lives in `RecentTipoffsSection.tsx` and can be tuned as volume grows.
- Cap on Recent Tipoffs results. Defaulted to **the same N as New Arrivals** (whatever that constant is today). Independent tuning is cheap to add later.
