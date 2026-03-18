## Why

The redesigned project listing page requires purpose-specific image assets (icons, main images, winner composites) that most projects don't have. Users aren't proactive about uploading these, and without them the listing page degrades to placeholder gradients. We need to help projects meet the image bar by providing AI-generated proposals via Leonardo AI, with admin tooling to trigger generation and user-facing UI to review and accept suggestions.

## What Changes

- Add `purpose` field to `ProjectImage` model distinguishing `icon`, `screenshot`, `main_image`, and `winner_composite` image types
- Add `approval_status` field (`proposed`, `active`) to track AI-generated images awaiting user acceptance
- New `ImageGenerationRequest` model to track Leonardo AI generation requests, prompts, and results
- Leonardo AI service integration for generating icons (1:1), main images (4:3 with device frame options), and winner composites (16:9 with icon reference)
- Shared generation dialog component: shows pre-filled prompt, allows editing, supports multiple variants, user picks and confirms
- Admin pages at `/admin/projects` (project list with image completeness) and `/admin/projects/{id}` (per-project image management and generation)
- Project owner image management section: view current images, see proposals, accept/reject, generate or upload their own
- Icon becomes a hard gate for listing page visibility — projects without an icon don't appear on `/projects`
- Migrate existing `general` purpose images to `screenshot`
- Rename "Set as main image" UI to "Set as primary screenshot"

## Capabilities

### New Capabilities
- `image-generation`: Leonardo AI integration for generating project images (icons, main images, winner composites) with prompt editing, variant selection, and async generation tracking
- `image-purposes`: Purpose-typed project images (icon, screenshot, main_image, winner_composite) with approval workflow for AI-generated proposals
- `admin-image-management`: Admin-only pages for viewing project image completeness and triggering image generation across projects

### Modified Capabilities
- `image-variants`: Generated images need variant creation (thumb/medium/large WebP) just like uploaded images
- `project-page-layout`: Project detail page gains an image management section for owners to view, accept, and generate purpose-specific images

## Impact

- **Django backend**: New model, new fields on `ProjectImage`, new Leonardo service, new API endpoints for generation and approval
- **Web UI**: New admin pages, generation dialog component, project owner image management section, listing page icon gate
- **External dependency**: Leonardo AI API (requires API key, has per-image credit costs)
- **Data migration**: Existing `ProjectImage` rows get `purpose='screenshot'` and `approval_status='active'`
- **Listing visibility**: Projects without an icon will no longer appear on the projects listing page
