## Context

The project listing page (`/projects`) currently renders a flat paginated grid of `ProjectCard` components with tag-based filtering and a sort dropdown. A separate "competition" view mode shows projects grouped by competition. The Django API serves a single `GET /api/projects` endpoint with tag, search, and sort parameters.

The page needs to become a discovery-oriented experience with two views: a curated Discover view (default) and a category-filtered grid view. This touches Django models, API endpoints, and the entire web-ui project listing page.

All existing projects have `category=null` and no purpose-specific images at launch — the design must degrade gracefully.

## Goals / Non-Goals

**Goals:**
- Curated, section-based Discover view that surfaces featured, new, winning, and popular projects
- Category system (one category per project) with tab-based navigation
- Purpose-typed images with a reliable fallback chain
- API endpoints that serve each Discover section independently (composable, cacheable)
- Launch-day readiness with no purpose-specific images and no categories assigned

**Non-Goals:**
- Sub-categories within a category (deferred)
- AI image generation workflow (separate initiative)
- Mobile app support (web only)
- Search within category view (existing tag search remains separate)
- Pagination within Discover sections (horizontal scroll, not paginated)

## Decisions

### 1. Separate section endpoints vs. single aggregated endpoint

**Decision:** Separate endpoints per Discover section (`/api/projects/featured`, `/api/projects/new-arrivals`, `/api/projects/winners`, `/api/projects/most-discussed`, `/api/projects/by-category/{slug}`).

**Why:** Each section has different query logic (annotation, date filtering, boolean flag, FK join). Separate endpoints are independently cacheable, testable, and allow the frontend to load sections progressively. A single aggregated endpoint would couple all section logic and make partial failures harder to handle.

**Alternative considered:** Single `/api/projects/discover` endpoint returning all sections — rejected because it serializes all data upfront, blocks on the slowest query, and can't be individually cached.

### 2. ProjectCategory as a new model vs. reusing TagCategory

**Decision:** New `ProjectCategory` model with a ForeignKey on `Project`, not reusing the existing tag system.

**Why:** Categories enforce "exactly one per project" at the database level (FK vs. M2M). The tag system is user-extensible with approval workflows — categories are admin-controlled with a fixed set. Mixing these concerns would complicate both systems.

**Alternative considered:** Adding a `is_primary_category` flag to the M2M tag relationship — rejected because it doesn't enforce single-category constraint and couples category logic to the tag approval workflow.

### 3. Image purpose field vs. separate image models per type

**Decision:** Add a `purpose` CharField with choices to the existing `ProjectImage` model. Default is `general` (preserving current behaviour for all existing images).

**Why:** All image types share the same storage, variant generation, and upload flow. A `purpose` field is a simple discriminator that avoids duplicating the image infrastructure. The existing `ImageVariant` system already handles size variants — purpose is orthogonal.

**Alternative considered:** Separate `HeroBannerImage`, `IconImage` models — rejected as unnecessary model proliferation for what is fundamentally the same entity with a type tag.

### 4. Image fallback chain in frontend vs. backend

**Decision:** Backend API returns resolved image URLs per purpose with fallback applied server-side. The API response includes `icon_url`, `hero_banner_url`, `in_use_image_url` fields — each already resolved through the fallback chain (purpose-specific → main image → null). Frontend applies gradient placeholder when URL is null.

**Why:** Centralises fallback logic in one place. Frontend doesn't need to know about image purposes or fallback rules — it gets a URL or null and renders accordingly. The gradient placeholder is purely visual and belongs in the frontend.

### 5. Discussion count: annotation vs. denormalized field

**Decision:** Use `Count('discussions')` annotation on querysets that need it (most-discussed endpoint, category view with "most discussed" sort). No denormalized counter field.

**Why:** Discussion volume is low enough that `COUNT` aggregation is fast. A denormalized field would require signals or triggers to keep in sync, adding complexity for a marginal performance gain. If this becomes a bottleneck, a materialized view or cached count can be added later.

**Alternative considered:** `discussion_count` IntegerField updated via post_save signal — rejected as premature optimisation.

### 6. Frontend architecture: replace page vs. add views

**Decision:** Replace the existing `ProjectsListing.tsx` component with a new page structure containing `DiscoverView` and `CategoryView` components, switched by the active category tab. The competition view toggle is removed.

**Why:** The current component is tightly coupled to the flat grid + tag filter pattern. Retrofitting sections into it would be more complex than a clean replacement. The competition view becomes a section within Discover rather than a separate mode.

**Component structure:**
- `ProjectsPage` — tab state, data fetching coordination
- `CategoryTabs` — sticky tab bar (Discover + one tab per active category)
- `DiscoverView` — renders sections (Featured, NewArrivals, Winners, CategoryRows, MostDiscussed)
- `CategoryView` — filtered grid with sort dropdown
- Section-specific card components (HeroCard, ArrivalCard, WinnerCard, IconCard, etc.)

### 7. Graceful section visibility — data-gated rendering

**Decision:** Every Discover section is gated by data existence. If the API returns an empty list for a section, that section is not rendered at all — no placeholder, no empty state, no "coming soon". Sections materialise as content is added over time.

**Why:** Images and curation (featured flags, categories, winner composites) will be populated in stages after the page ships. The page must look intentional at every stage — showing only what has content, rather than exposing unfilled sections that signal incompleteness.

**Section visibility rules:**
- **Featured (hero):** Renders only if ≥1 project has `is_featured=True`
- **New Arrivals:** Always renders (falls back to most recent N if <5 in 30-day window) — hidden only if zero approved projects exist
- **Competition Winners:** Renders only if ≥1 competition has a winner assigned
- **Category Rows:** Each row renders only if that category has ≥1 project. No categories assigned = no category rows
- **Most Discussed:** Renders only if ≥1 project has >0 discussions

### 8. Staging URL: `/preview/` prefix

**Decision:** The new page is built at `/preview/projects/` rather than replacing `/projects`. The existing project listing remains untouched until the new page is ready for cutover.

**Why:** This is a large change and content (images, categories, featured flags) will be populated incrementally. A separate preview URL allows building and testing against real data without disrupting the live page. The `/preview/` prefix is a reusable convention for staging any future page redesigns.

**Cutover:** When ready, move the page component from `src/app/preview/projects/` to `src/app/projects/` and delete the preview route.

**Routing note:** Category tabs use search params (`/preview/projects?category=dev-tools`), consistent with Decision 9 below.

### 9. Category tab routing: URL params vs. path segments

**Decision:** Use URL search params (`/projects?category=dev-tools`) rather than path segments (`/projects/dev-tools`).

**Why:** The Discover view is the default at `/projects` with no params. Category filtering is a view state toggle, not a separate page. Search params keep the URL structure flat and consistent with existing tag filtering (`/projects?tags=...`). Path segments would require new Next.js route definitions.

### 10. New Arrivals window: fixed 30 days vs. configurable

**Decision:** Fixed 30-day rolling window, with fallback to most recent N approved projects if fewer than 5 qualify.

**Why:** Simplicity. The 30-day window is a product decision, not a per-deployment config. If it needs tuning, it's a one-line code change. Exposing it as config adds complexity for a knob nobody will turn.

### 11. Re-adding is_featured: new migration vs. migration surgery

**Decision:** New migration adding `is_featured = BooleanField(default=False)` to Project. Don't try to reverse migration `0023` — just add a fresh field.

**Why:** Migration history is append-only in practice. A new migration is clean, safe, and doesn't require understanding why the field was originally removed.

## Risks / Trade-offs

**N+1 queries on Discover view** — Five section endpoints means five API calls on page load. → Mitigation: Sections load independently with skeleton placeholders. Use `Promise.all` for parallel fetching. Individual endpoints are cacheable (featured/winners change rarely).

**Empty sections on launch** — No featured projects flagged, no categories assigned, possibly no recent winners. → Mitigation: Each section hides itself when empty. Discover view degrades gracefully — even with zero sections, the category rows will show all projects (uncategorised row as fallback). Admin needs to flag featured projects before launch.

**Category migration effort** — All existing projects start with `category=null`. → Mitigation: Category view shows "Uncategorised" projects. Admin bulk-assignment tool or management command for initial categorisation. Not blocking launch.

**project-type tag overlap** — The existing `project-type` TagCategory may conflict with the new category system. → Mitigation: Defer tag retirement to a follow-up. Both systems coexist — categories for page organisation, tags for detailed classification. Document the overlap for future cleanup.

**Image aspect ratio mismatch** — Existing `general` images may not suit 16:9 hero or 1:1 icon crops. → Mitigation: Use `object-fit: cover` with appropriate focal point (center). Accept some cropping — purpose-specific images will replace these over time. Gradient placeholders for projects with no images at all.

## Migration Plan

1. **Database migrations** — Add `ProjectCategory` model, `category` FK on `Project`, `is_featured` on `Project`, `purpose` on `ProjectImage`. All fields nullable/defaulted — no data loss, backward compatible.
2. **API endpoints** — Add new section endpoints alongside existing `/api/projects`. Existing endpoint unchanged initially.
3. **Frontend** — Build new page at `/preview/projects/`. Existing `/projects` page remains untouched.
4. **Admin setup** — Create initial categories (Consumer Products, Dev Tools, Community Boosters). Flag 3 featured projects. Bulk-assign categories to existing projects.
5. **Cutover** — Move page component from `src/app/preview/projects/` to `src/app/projects/`, delete preview route.
6. **Rollback** — Revert cutover PR to restore old listing page. New API endpoints and models are additive and harmless if unused.

## Open Questions

- Should the "Most Discussed" section count only top-level discussions or include replies? (Leaning: top-level only, as reply count inflates threads that happen to be contentious)
- Winner composite images need a generation workflow — manual upload for now, automate later?
- Exact card widths on mobile viewports under 375px — needs visual QA with real content
