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

Featured projects are selected by admin (editorial control).

#### 2. New Arrivals

Horizontal scroll of image-led cards:
- 4:3 aspect ratio image (in-use screenshot or AI-generated scene)
- Subtle bottom fade on image (`rgba(0,0,0,0.15)`)
- Below image: category label (indigo, uppercase), title, 2-line tagline on white card surface
- Card width: 240px

Populated automatically from recent approved projects.

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
- Leverages the existing discussions feature as a signal
- Shows top 4-5 projects

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

Categories are implemented as a **special type of tag** within the existing tag system:

- **Admin-controlled set** — only admins can create/modify category tags
- **User-assigned** — project owners select from the available categories
- **Single primary category per project** — used for tab filtering and category labels on cards
- **Starting set:** Consumer Products, Dev Tools, Community Boosters (expandable by admin)

Categories live alongside the existing tag system. Tags remain for more granular classification; categories provide the top-level organizer.

## Image Artifacts Required Per Project

| Artifact | Dimensions | Aspect Ratio | Used Where | Source |
|----------|-----------|-------------|------------|--------|
| App icon | 256x256px min | 1:1 square | Icon cards, list items, filtered view, winner composites | AI-generated (Leonardo) or user-provided |
| Hero banner | 1536px wide min | 16:9 | Featured section, fallback for arrivals | AI-generated (Leonardo) |
| In-use image | 1024px wide min | 4:3 | New Arrivals cards | AI-generated scene or product screenshot |
| Winner composite | 1536px wide min | 16:9 | Competition Winners section | AI-generated: app icon + competition trophy combined |

**Image generation strategy:**
- Icons and banners are generated via Leonardo AI (separate work, not part of this change)
- The system should gracefully degrade when images are missing (fall back to existing project images or gradient placeholders)
- Image variants (thumb, medium, large as WebP) are already supported by the existing `ImageVariant` system

## What Changes vs What's Reused

### New

- Category system (admin-controlled tag subtype)
- Discover view with curated sections
- Featured section with editorial selection (admin)
- Most Discussed section (query by discussion count)
- Hero banner and app icon image types
- Winner composite images
- Category view (filtered grid)
- Dark navy text box treatment for large hero card

### Reused

- Existing tag infrastructure (categories extend it)
- Competition/winner data model
- Discussion system (comment counts)
- Image storage and variant generation (S3 + WebP)
- Project data model (title, tagline, etc.)
- Navigation component (unchanged)
- Existing hover/transition patterns and design tokens

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

Interactive mockup available at `.superpowers/brainstorm/45178-1773840531/layout-naglasupan-v2.html`.

## Open Questions

- How are "Featured" projects selected? Manual admin toggle, or a separate admin UI?
- Should categories support sub-categories within "Consumer Products"?
- What's the fallback when a project has no icon or banner image?
- How frequently should "New Arrivals" rotate? Calendar month, rolling 30 days, or manual?
