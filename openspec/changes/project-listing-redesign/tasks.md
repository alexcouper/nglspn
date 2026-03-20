## 1. Django Models & Migrations

- [x] 1.1 Create `ProjectCategory` model with fields: id (UUID), name, slug (unique), display_order, created_at. Add ordering by display_order then name.
- [x] 1.2 Add `category` nullable ForeignKey to `ProjectCategory` on the `Project` model (on_delete SET_NULL)
- [x] 1.3 Add `is_featured` BooleanField (default=False) on the `Project` model via a new migration
- [x] 1.4 Add `purpose` CharField with choices (general, icon, hero_banner, in_use, winner_composite, default=general) on `ProjectImage` model
- [x] 1.5 Generate and run migrations for all model changes
- [x] 1.6 Register `ProjectCategory` in Django admin with list display: name, slug, display_order, project count. Add `is_featured` toggle and `category` to Project admin.

## 2. Backend Service & Image Resolution

- [x] 2.1 Add image-by-purpose resolution method: given a project and purpose, return the purpose-specific image → main image → None fallback chain
- [x] 2.2 Add resolved image URL fields to project list serialisation: `icon_url`, `hero_banner_url`, `in_use_image_url` (each resolved via the fallback chain)
- [x] 2.3 Add discussion count annotation helper: `Count('discussions', filter=Q(discussions__parent__isnull=True))` for use in querysets

## 3. API Endpoints

- [x] 3.1 `GET /api/projects/categories` — list all categories with project_count (approved projects), ordered by display_order
- [x] 3.2 `GET /api/projects/featured` — approved projects with is_featured=True, ordered by updated_at desc, with resolved image URLs
- [x] 3.3 `GET /api/projects/new-arrivals` — approved projects from last 30 days (fallback to 5 most recent if <5 qualify), with resolved image URLs
- [x] 3.4 `GET /api/projects/winners` — projects that won competitions, with competition name/date, ordered by competition end_date desc
- [x] 3.5 `GET /api/projects/most-discussed` — approved projects with discussion_count > 0, ordered by discussion_count desc, with resolved image URLs
- [x] 3.6 `GET /api/projects/by-category/{slug}` — approved projects in a category, with sort param (newest/name/most-discussed), 404 for invalid slug

## 4. OpenAPI & Type Generation

- [x] 4.1 Run `make extract-openapi` to generate updated OpenAPI spec
- [x] 4.2 Run `npm run generate-types` in web-ui to generate TypeScript types for new endpoints

## 5. Frontend: Page Shell & Routing

- [x] 5.1 Create Next.js page at `src/app/preview/projects/page.tsx` with server component fetching initial data
- [x] 5.2 Create `ProjectsPage` client component managing tab state (Discover vs category) from URL search params
- [x] 5.3 Create `CategoryTabs` component: sticky underline tab bar with Discover tab + one tab per category with projects. Fetch categories from API. Hide categories with 0 projects.

## 6. Frontend: Discover View

- [x] 6.1 Create `DiscoverView` component that renders non-empty sections with independent data fetching and skeleton placeholders
- [x] 6.2 Create `FeaturedSection` — 2-column layout: 1 large hero card (16:9 banner + dark navy text box) and 2 small hero cards (16:9 banner + scrim overlay). Only renders when data exists.
- [x] 6.3 Create `NewArrivalsSection` — horizontal scroll of 240px arrival cards (4:3 image, bottom fade, category label + title + tagline on white). Only renders when data exists.
- [x] 6.4 Create `WinnersSection` — horizontal scroll of 280px winner cards (16:9 composite, gold border/glow, amber "Winner" badge, competition name). Only renders when data exists.
- [x] 6.5 Create `CategoryRowsSection` — one horizontal scroll row per category with icon cards (44px icon + title + tagline, 200px wide) and "See all" link. Only renders for categories with projects.
- [x] 6.6 Create `MostDiscussedSection` — vertical list of top 5 projects (40px icon, title, tagline, indigo comment count). Only renders when data exists.

## 7. Frontend: Category View

- [x] 7.1 Create `CategoryView` component with icon-led grid (`repeat(auto-fill, minmax(240px, 1fr))`), 48px icon cards, and project count display
- [x] 7.2 Add sort dropdown (Newest, Name A-Z, Most Discussed) with default Newest, triggering re-fetch from by-category endpoint

## 8. Frontend: Shared Components

- [x] 8.1 Create gradient placeholder component for null image URLs using existing `getPlaceholderColor` utility
- [x] 8.2 Create API client functions for all new endpoints (featured, new-arrivals, winners, most-discussed, by-category, categories)
- [x] 8.3 Apply visual design tokens: card surfaces (#fff, 1px #e2e8f0 border, 12px radius), hover (translateY -2px + shadow), accent colours (indigo #6366f1, amber #fbbf24)

## 9. Testing & Verification

- [x] 9.1 Add Django tests for new model fields, migrations, and the image purpose fallback chain
- [x] 9.2 Add Django tests for each new API endpoint (featured, new-arrivals, winners, most-discussed, by-category, categories) including empty-data cases
- [x] 9.3 Run full backend lint and test suite (`make lint && make test` in django-backend)
- [x] 9.4 Run frontend lint (`npm run lint` in web-ui)
- [ ] 9.5 Visual verification with Playwright: load /preview/projects/, confirm sections render with seed data, confirm empty sections are hidden, confirm category tab switching works
