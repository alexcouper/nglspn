## Why

The project listing page is a flat grid of cards with tag-based filtering. As project count grows (~10/month, heading past 100), the page feels like a database dump rather than a curated discovery experience. The tag-heavy cards are cluttered, there's no visual hierarchy, and there's no way to browse by "what's new and interesting". The page needs to shift from search-oriented utility to discovery-oriented curation.

## What Changes

- **Replace** the current flat grid project listing with a two-view system:
  - **Discover view** (default): curated homepage with editorial sections — Featured, New Arrivals, Competition Winners, Category Rows, Most Discussed
  - **Category view**: filtered, sortable icon-led grid activated by clicking a category tab
- **Add** a `ProjectCategory` model with a ForeignKey on `Project` — enforces exactly one primary category per project (separate from existing tags)
- **Re-add** `is_featured` boolean on `Project` (previously removed in migration `0023`)
- **Add** `purpose` field on `ProjectImage` to distinguish image types (`icon`, `hero_banner`, `in_use`, `winner_composite`, `general`)
- **Add** image fallback chain: purpose-specific → main project image → gradient placeholder
- **Add** new API endpoints: featured projects, new arrivals, competition winners, most discussed
- **Add** discussion count annotation on project queries (`Count('discussions')`)
- **Remove** current competition view toggle (replaced by Competition Winners section in Discover view)

## Capabilities

### New Capabilities
- `project-categories`: Category model, ForeignKey on Project, admin-managed category set, category assignment by project owners
- `project-listing-discover`: Discover view with curated sections — Featured (editor's picks), New Arrivals (rolling 30-day window), Competition Winners, Category Rows, Most Discussed
- `project-listing-category-view`: Filtered icon-led grid per category with sort options (Newest, Name A-Z, Most discussed) and project count
- `project-image-purposes`: Purpose field on ProjectImage, image type distinction, fallback chain for missing purpose-specific images

### Modified Capabilities
- `project-page-layout`: Project listing page structure is being replaced — the flat grid and tag filter are removed in favour of Discover + Category views
- `image-variants`: ProjectImage gains a `purpose` field; existing images become `general` purpose; variant generation unchanged but now serves purpose-specific queries
- `discussions`: Discussion counts are exposed as a queryable annotation for the "Most Discussed" section and sort option

## Impact

- **Django models**: New `ProjectCategory` model; new fields on `Project` (`category`, `is_featured`) and `ProjectImage` (`purpose`); new migration(s)
- **Django API**: New endpoints for discover sections (featured, new arrivals, winners, most discussed, category-filtered listing); existing project list endpoint may be modified or replaced
- **Web UI**: New page components for Discover view sections, Category view grid, category tabs; existing project listing page replaced
- **Admin**: Category management UI; `is_featured` toggle on projects
- **Data**: Existing projects will have `category=null` and `purpose='general'` images — fallback behaviour is critical for launch
- **Existing tags**: Tag system unchanged but `project-type` TagCategory may overlap with new categories — review during implementation
