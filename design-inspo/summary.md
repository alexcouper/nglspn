# Project Listing Redesign — Design Inspiration Summary

## Inspiration Sources

### Setapp Marketplace (Primary influence)
- **What we took:** Category tabs as top-level navigation, curated sections (Top Rated, New Arrivals), horizontal scrolling rows, icon-led compact cards
- **Why it works:** Feels hand-picked and editorial rather than a database dump. Categories are built into the page structure (tabs + sections) rather than a separate filter sidebar

### Apple App Store "Today" Tab
- **What we took:** Mixed card sizes (large hero + smaller cards), editorial storytelling, category labels above titles (not tag badges on cards)
- **Why it works:** Visual hierarchy draws the eye. The hero card tells a story while smaller cards are scannable

### Product Hunt
- **What we took:** Icon-led compact list items, single-line taglines, minimal metadata per item
- **Why it works:** Information-dense without feeling cluttered. The icon does all the visual differentiation

### Dribbble / Behance
- **What we took:** Image-led cards for sections that need visual impact (New Arrivals, Winners)
- **Why it works:** When images are high quality, the page sells itself. Requires investment in imagery

### Vercel Marketplace
- **What we took:** Clean grid for category-filtered views, icon + 2-line description cards
- **Why it works:** Scales to hundreds of items without losing usability

## Key Design Features

1. **Dual-mode page:** Curated "Discover" homepage vs filtered category grid
2. **Mixed card formats:** Hero cards, image-led cards, icon-led cards, list items — each optimized for its context
3. **Category tabs** (not tag filters) as primary navigation
4. **Five curated sections:** Featured, New Arrivals, Competition Winners, Category Rows, Most Discussed
5. **Dark navy text box** on large hero card — solves the overlay-on-light-background problem
6. **Scrim + gradient overlay** on small hero cards — works at that scale
7. **Horizontal scroll** for all section types except Most Discussed (vertical list)

## Artifacts Needed Per Project

| Artifact | Format | How to Produce |
|----------|--------|---------------|
| **App icon** | 256x256px, square, rounded corners | AI-generated via Leonardo, or user upload |
| **Hero banner** | 16:9, min 1536px wide | AI-generated via Leonardo — scene/lifestyle representing the project |
| **In-use image** | 4:3, min 1024px wide | AI-generated scene showing product in context, or product screenshot |
| **Winner composite** | 16:9, min 1536px wide | AI-generated combination of app icon + competition trophy |
| **Tagline** | Max ~80 chars | User-provided (already exists in data model) |
| **Category** | Single selection | User-selected from admin-controlled set |

## Files in This Directory

- `patterns-scrapbook.html` — Interactive scrapbook of design patterns with wireframes, techniques, and artifact requirements for each inspiration source
- `final-mockup.html` — The approved mockup using Naglasupan's design system with real images (open in browser)
