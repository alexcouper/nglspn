# Project Listing Page Redesign

## Problem

The current project listing page is a flat grid of cards with tag-based filtering. As the project count grows (~10/month, heading past 100), the page needs to feel more curated and engaging for community members browsing what's new and interesting. The current tag-heavy cards feel cluttered, and there's no visual hierarchy to guide discovery.

## Goals

- Make the project listing page feel curated and dynamic, not like a database dump
- Support discovery-oriented browsing ("what's new and interesting?") over search-oriented utility
- Introduce a category system that organizes without cluttering individual cards
- Establish image artifact requirements so AI generation (Leonardo) can produce what's needed
- Scale gracefully from current project count to 100+

## Design Decisions

### Page Structure

The page uses a **Setapp-style curated sections** approach with **category tabs** for filtering.

**Two views:**

1. **Discover view** (default) — a curated homepage with editorial sections
2. **Category view** — a filtered, sortable icon-led grid (activated by clicking a category tab)

**Category tabs** are sticky below the navigation bar, using the existing underline tab pattern:

```
[Discover] [Consumer Products] [Dev Tools] [Community Boosters]
```

### Discover View Sections

The Discover view presents five section types in order:

#### 1. Featured

Editor's picks. A 2-column layout:
- **Left:** 1 large card — 16:9 hero banner image on top, dark navy (`#0f172a`) text box below containing indigo category label, white title, slate tagline
- **Right:** 2 small stacked cards — 16:9 hero banner with overlay text (scrim at `rgba(15,23,42,0.35)` + bottom gradient to `rgba(15,23,42,0.8)`)

The large card uses a dark text box rather than an image overlay because overlays don't read well at that size on a light page. The small cards work with overlays because the gradient covers proportionally more of the image.

Featured projects are selected via an `is_featured` boolean on the Project model (admin-toggled). Note: this field previously existed and was removed in migration `0023` — it should be re-added.

#### 2. New Arrivals

Horizontal scroll of image-led cards:
- 4:3 aspect ratio image (in-use screenshot or AI-generated scene)
- Subtle bottom fade on image (`rgba(0,0,0,0.15)`)
- Below image: category label (indigo, uppercase), title, 2-line tagline on white card surface
- Card width: 240px

Populated automatically from approved projects created in the last 30 days (rolling window). Falls back to most recent approved projects if fewer than 5 are within the window.

#### 3. Competition Winners

Horizontal scroll of winner cards:
- 16:9 aspect ratio **winner composite image** (AI-generated combination of app icon + competition trophy)
- Gold border (`#fde68a`), gold hover glow
- "Winner" badge (amber pill, top-right)
- Below image: title, tagline, competition name in amber
- Card width: 280px

Populated automatically from competition winner data (already exists in the data model).

#### 4. Category Rows

One horizontal scroll row per category (Consumer Products, Dev Tools, Community Boosters):
- **Icon-led compact cards**: 44px square icon + title + short tagline
- Card width: 200px
- "See all" link navigates to that category's filtered view
- Shows a representative sample, not all projects

#### 5. Most Discussed

Vertical list of top projects by discussion activity:
- 40px icon, title, tagline, comment count (indigo)
- Shows top 4-5 projects
- **New backend work required:** annotate projects with discussion count via `Project.objects.annotate(discussion_count=Count('discussions'))`, ordered descending. This annotation is also reused by the "Most discussed" sort option in the Category view.

### Category View

When a category tab is clicked (anything other than "Discover"):
- Sections disappear, replaced by a flat icon-led grid
- Sort dropdown: Newest first, Name A-Z, Most discussed
- Project count displayed
- Cards: 48px icon + title + 2-line tagline
- Grid: `repeat(auto-fill, minmax(240px, 1fr))`

This view is designed to scale to 100+ projects within a category.

### Card Types Reference

| Card Type | Used In | Image Format | Text Treatment |
|-----------|---------|-------------|----------------|
| Large hero | Featured (main) | 16:9 banner | Dark navy box below image |
| Small hero | Featured (side) | 16:9 banner | Overlay with scrim + gradient |
| Arrival card | New Arrivals | 4:3 image | Below on white card |
| Winner card | Competition Winners | 16:9 composite | Below on white, gold accent |
| Icon card | Category rows | 44px square icon | Inline next to icon |
| List item | Most Discussed | 40px square icon | Inline, with comment count |
| Filtered card | Category view | 48px square icon | Inline, 2-line description |

## Category System

Categories are a **new ForeignKey field on Project**, not part of the existing M2M tag system. This cleanly enforces "exactly one primary category per project" at the database level.

- **New model:** `ProjectCategory` with `name`, `slug`, `display_order`, `is_active` fields (similar to `TagCategory` but purpose-built)
- **New field on Project:** `category = ForeignKey(ProjectCategory, null=True, on_delete=SET_NULL)` — nullable to handle legacy projects without a category
- **Admin-controlled set** — only admins can create/modify categories
- **User-assigned** — project owners select from the available categories when creating/editing a project
- **Starting set:** Consumer Products, Dev Tools, Community Boosters (expandable by admin)
- **Relationship to existing tags:** Categories and tags are independent. The existing `project-type` TagCategory may overlap with some categories — this should be reviewed during implementation (consider migrating existing `project-type` tag assignments to the new category field and then retiring that TagCategory)

Categories provide the top-level organizer for tabs and section headers. Tags remain for more granular classification.

## Image Artifacts Required Per Project

| Artifact | Dimensions | Aspect Ratio | Used Where | Source |
|----------|-----------|-------------|------------|--------|
| App icon | 256x256px min | 1:1 square | Icon cards, list items, filtered view, winner composites | AI-generated (Leonardo) or user-provided |
| Hero banner | 1536px wide min | 16:9 | Featured section, fallback for arrivals | AI-generated (Leonardo) |
| In-use image | 1024px wide min | 4:3 | New Arrivals cards | AI-generated scene or product screenshot |
| Winner composite | 1536px wide min | 16:9 | Competition Winners section | AI-generated: app icon + competition trophy combined |

**Image type field:**

The existing `ProjectImage` model needs a new `purpose` field to distinguish image types:

```
purpose = CharField(choices=['general', 'icon', 'hero_banner', 'in_use', 'winner_composite'], default='general')
```

Existing images are `general` (the current behaviour). New purpose-specific images are queried by purpose for the appropriate card types.

**Image fallback chain:**

When a purpose-specific image is missing, the system falls back in this order:
1. Purpose-specific image (e.g. `hero_banner`) → use it
2. Main project image (`is_main=True`) → use it (for banners/in-use), or crop to square (for icons)
3. No images at all → gradient placeholder based on project title hash (matching existing `getPlaceholderColor` utility)

This is critical because on launch day, no project will have purpose-specific images. The page must look good using only existing `general` images and gradient fallbacks.

**Image generation strategy:**
- Icons and banners are generated via Leonardo AI (separate work, not part of this change)
- Image variants (thumb, medium, large as WebP) are already supported by the existing `ImageVariant` system

## What Changes vs What's Reused

### New

- `ProjectCategory` model + `category` ForeignKey on Project
- `is_featured` boolean on Project (re-added)
- `purpose` field on `ProjectImage`
- Discover view with curated sections (new frontend page/component)
- API endpoints: featured projects, new arrivals, competition winners, most discussed
- Discussion count annotation on project queries
- Category view (filtered grid with category-based filtering)
- Dark navy text box treatment for large hero card

### Reused

- Competition/winner data model
- Discussion system (comment counts as data source)
- Image storage and variant generation (S3 + WebP)
- Project data model (title, tagline, etc.)
- Existing tag system (unchanged, runs alongside categories)
- Navigation component (unchanged)
- Existing hover/transition patterns and design tokens

### Replaced

- Current flat grid project listing → Discover view + Category view
- Current competition view toggle → Competition Winners section in Discover view (existing toggle removed)

## Visual Design

The design uses the existing Naglasúpan light theme with one extension:

- **Page background:** `#f8fafc` (existing `--muted`)
- **Card surfaces:** `#ffffff` with `1px solid #e2e8f0` border
- **Large hero text box:** `#0f172a` (matches nav) with white/indigo/slate text
- **Small hero overlays:** Navy scrim + gradient over image
- **Accent colour:** `#6366f1` indigo (existing `--accent`) for category labels, active tabs, links
- **Winner accent:** `#fbbf24` amber (existing winner treatment)
- **Font:** Inter (existing)
- **Border radius:** 12px on cards (existing)
- **Hover:** translateY(-2px) + shadow lift (existing pattern)

Interactive mockup available at `design-inspo/final-mockup.html` (open in browser).

## Open Questions

- Should categories support sub-categories within "Consumer Products"? (Not needed for v1, can be added later)
- Winner composite images require a generation workflow — should this be automated (triggered on competition win) or manual?
- Scrim/gradient opacity values on small hero cards (`0.35` scrim, `0.8` gradient) are starting points — may need visual QA with real diverse imagery
- Mobile: horizontal scroll sections should show a peek of the next card to afford scrollability — exact card widths may need adjustment on viewports under 375px
