## Why

Community tip-off projects (projects added on behalf of someone who didn't actually make them) already round-trip through the system: the submit form sets a flag, the backend records a system-user OWNER + SUGGESTER pair, and the project detail page shows a "Community Tipoff" pill. But the feature is half-surfaced:

- Tip-offs are computed via a query annotation (`community_owned`), making admin filtering awkward and indexing impossible.
- The Django admin list view and detail page give no visual signal that a project is a tip-off.
- The "New Project submitted" notification email reads identically for self-owned projects and tip-offs.
- On the public Discover page, tip-offs sit inside "New Arrivals" — they're shown as one-of-many regular submissions, with only a small per-card pill to distinguish them.
- The "Community Tipoff" pill in the UI gives no explanation of what it means or how an actual maker can claim the project.

This change promotes the tip-off concept to a first-class, denormalized column on `Project`, restructures the Discover page to give tip-offs their own section, and adds the missing affordances (admin clarity, email cue, tooltip copy with contact email) so that staff and visitors can both reason about tip-offs at a glance.

## What Changes

### Backend

- **Add** `is_community_tipoff: BooleanField(default=False, db_index=True)` to the `Project` model. Backfill via data migration using the same logic the current annotation uses (does the project have an `OWNER` contributor whose user is a system user).
- **Add** an idempotent `Project.recompute_community_tipoff()` method that re-derives the column from the contributor truth, plus `post_save` and `post_delete` signals on `ProjectContributor` that call it. Bulk ORM paths (`bulk_create`, `qs.update()/.delete()`) are not auto-handled — callers in such paths SHALL invoke `recompute_community_tipoff()` explicitly.
- **Remove** the `_community_owned_annotation()` helper; all queries, serializers, admin code, and filters SHALL read the new column directly.
- **Rename** the public API field on `ProjectCreate`, `ProjectResponse`, `DiscoverProjectResponse`, and any other schema that exposes it: `community_owned` → `is_community_tipoff`. Regenerate the OpenAPI spec and TypeScript types.
- **Add** `GET /api/projects/recent-tipoffs` returning the most recent tip-off projects, ordered by `created_at` descending, capped at the same N as `/api/projects/new-arrivals`.
- **Modify** `list_new_arrivals` to filter `is_community_tipoff = False`. New Arrivals SHALL no longer include tip-offs.
- **Modify** the new-project notification email: the subject SHALL branch to "New tip-off submitted - Naglasúpan" when the submitted project is a tip-off, and the email body SHALL include a single line indicating the project is a community tip-off.
- **Modify** `ProjectAdmin`: `is_community_tipoff` SHALL appear in `list_display` and `list_filter`, and SHALL be visible (read-only) on the change page in the "Ownership" fieldset.

### Frontend

- **Add** `src/web-ui/src/lib/constants.ts` exporting `SITE_EMAIL = "alex@naglasupan.is"`. Migrate `/about/contact/page.tsx` to read from this constant instead of hardcoding inline.
- **Add** a small `Tooltip` component at `src/web-ui/src/components/Tooltip.tsx` supporting hover (desktop), click-toggle (touch), and focus, with `aria-describedby` for screen readers. No new third-party dependency.
- **Add** `src/web-ui/src/app/projects/sections/RecentTipoffsSection.tsx`, fetching `GET /api/projects/recent-tipoffs` via a new `recentTipoffs()` method on the Discover API client. The section header SHALL include a "?" affordance that opens the tooltip with the standard tip-off explainer copy. The section SHALL be hidden entirely (heading + list) unless the response contains at least three tip-off projects.
- **Modify** `NewArrivalsSection.tsx`: remove the per-card `TipoffBadge`, since tip-offs no longer appear in this section.
- **Modify** `RecentTipoffsSection.tsx`: do not render a per-card `TipoffBadge` in the section's hero/large card layout — the section heading already conveys the category. Smaller cards similarly omit the badge.
- **Modify** `TipoffBadge.tsx` (used on the project detail page banner): wrap the badge in the new `Tooltip` so hovering / tapping it opens the explainer copy.
- **Modify** `DiscoverView.tsx` to render `RecentTipoffsSection` below the existing `WinnersSection` (and above the category rows).
- **Sweep** all call sites of the renamed API field (`community_owned` → `is_community_tipoff`).

## Capabilities

### Modified Capabilities

- `community-submissions`: project creation, the OWNER + SUGGESTER pair, and the seed-user requirement are unchanged. New requirements cover the denormalized `is_community_tipoff` column, the signal-based sync, the renamed public API field, the `recent-tipoffs` endpoint, the admin surfacing, and the tip-off-aware email subject/body.

### New Capabilities

- `tipoff-projects-surfacing`: Discover page section restructure (tip-offs out of New Arrivals, into a dedicated "Recent Tipoffs" section), the tooltip primitive, the standard tip-off explainer copy, the site-email constant, and the badge tooltip on the project detail page.

## Impact

- **Django backend**: model migration + data migration, signals module, schema renames, new endpoint + service method, admin tweaks, email handler/template tweaks. Annotation helper deleted.
- **OpenAPI / generated types**: regenerated. Field rename ripples through the web-ui.
- **Web UI**: new constants file, new `Tooltip` component, new `RecentTipoffsSection`, edits to `NewArrivalsSection`, `DiscoverView`, `TipoffBadge`, `/about/contact`. Call-site sweep for the renamed field.
- **Tests**: signal coverage on contributor add/remove flips the column; admin filter; email subject/body branching; discover endpoint excludes/includes correctly; component tests for the tooltip; Playwright golden path covering both Discover sections and the detail-page badge tooltip.
- **Out of scope**: a "claim this project" button, the SUGGESTER's own UX beyond what's already shipped, pagination on Recent Tipoffs, any background reconciliation job, distinguishing pill colour or icon redesign.
