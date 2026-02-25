## ADDED Requirements

### Requirement: Above-the-fold images use eager loading with preload hints
The system SHALL render above-the-fold images with Next.js `priority` prop so they are preloaded in the HTML head and loaded eagerly.

#### Scenario: Project detail page hero image
- **WHEN** a user navigates to `/projects/[id]`
- **THEN** the main project image SHALL have a corresponding `<link rel="preload">` in the page HTML head

#### Scenario: Project listing page grid
- **WHEN** a user navigates to `/projects`
- **THEN** the first 6 project card images SHALL have `loading="eager"` and preload hints

### Requirement: Images are served in AVIF format when supported
The system SHALL configure Next.js image optimization to serve AVIF format to browsers that support it, with WebP as fallback.

#### Scenario: AVIF-capable browser requests an image
- **WHEN** a browser with AVIF support requests an optimized image via `/_next/image`
- **THEN** the response SHALL be in AVIF format

### Requirement: Optimized images are cached for at least 30 days
The system SHALL set `minimumCacheTTL` to 2592000 seconds (30 days) for optimized images to reduce server-side re-optimization frequency.

#### Scenario: Repeated image request within 30 days
- **WHEN** an optimized image is requested within 30 days of first optimization
- **THEN** the server SHALL serve the cached version without re-fetching from the origin CDN
