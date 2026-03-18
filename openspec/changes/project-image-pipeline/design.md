## Context

The project listing page redesign requires purpose-specific images (icon, main image, winner composite) per project. Currently `ProjectImage` has no concept of purpose — all images are interchangeable, with one flagged `is_main`. Most project owners won't proactively supply these assets, so we need to generate proposals via Leonardo AI and provide tooling for admins to trigger generation and users to review results.

The Django backend uses a service layer pattern (`services/<domain>/handler_interface.py` + `django_impl/handler.py`) with `django-tasks` for async work. Image storage uses S3 with CDN delivery and WebP variant generation via Pillow. The frontend is Next.js with server-side rendering.

## Goals / Non-Goals

**Goals:**
- Add purpose and approval tracking to project images
- Integrate Leonardo AI for generating icons, main images, and winner composites
- Provide admin pages to manage image completeness across all projects
- Let project owners view, accept, and generate their own images
- Make icon a hard requirement for listing visibility
- Reusable generation dialog with prompt editing and variant selection

**Non-Goals:**
- Hero banner generation (parked — may be derived from main image later)
- Email outreach to existing project owners (follow-up change)
- New project creation flow changes (follow-up change)
- Automated generation on project approval (manual trigger only for now)

## Decisions

### 1. New fields on ProjectImage

Add `purpose` and `approval_status` to the existing `ProjectImage` model rather than creating a separate model for purpose-specific images. This preserves compatibility with the existing variant generation, S3 storage, and API response infrastructure.

```
purpose: icon | screenshot | main_image | winner_composite  (default: screenshot)
approval_status: active | proposed  (default: active)
```

Existing images get `purpose=screenshot, approval_status=active` via data migration. The `is_main` field is kept as a fallback mechanism — the listing page design spec's fallback chain (`purpose-specific → is_main → gradient`) continues to work.

**Alternative considered:** Separate `PurposeImage` model. Rejected because it would duplicate storage/variant infrastructure and require parallel API schemas.

### 2. ImageGenerationRequest model

New model to track Leonardo AI generation lifecycle:

```
ImageGenerationRequest
├── id (UUID)
├── project (FK → Project)
├── purpose (icon | main_image | winner_composite)
├── prompt_text (TextField)
├── device_frame (nullable: mobile | laptop | watch — for main_image with screenshots)
├── reference_image (FK → ProjectImage, nullable — screenshot for main_image, icon for winner_composite)
├── leonardo_generation_id (CharField, nullable — set when API responds)
├── leonardo_model_id (CharField — Phoenix or FLUX Kontext)
├── width (int)
├── height (int)
├── num_variants (int, 1-4)
├── status (queued | generating | completed | failed)
├── error_message (TextField, nullable)
├── created_by (FK → User)
├── created_at
├── completed_at (nullable)
```

Result images are linked via `ProjectImage` rows with `approval_status=proposed` and a FK back: `generation_request = FK(ImageGenerationRequest, null=True)` on `ProjectImage`. This way generated images flow through the same storage and variant pipeline as uploads.

### 3. Leonardo AI service layer

New service following the existing pattern:

```
services/leonardo/
├── handler_interface.py   # LeonardoHandlerInterface
├── django_impl/
│   ├── handler.py         # DjangoLeonardoHandler
│   └── client.py          # LeonardoAPIClient (HTTP layer)
```

The client handles raw HTTP to Leonardo's REST API. The handler orchestrates the generation workflow:

1. Create generation request (DB record)
2. If reference image needed, upload it to Leonardo via presigned URL
3. Call `POST /generations` with prompt, dimensions, model
4. Poll `GET /generations/{id}` until complete (exponential backoff, max ~60s)
5. Download generated images from Leonardo CDN URLs
6. Upload to our S3 bucket as `ProjectImage` rows with `approval_status=proposed`
7. Trigger variant generation for each result image
8. Update generation request status

Polling is chosen over webhooks for v1 — simpler, no public endpoint needed, generations complete in seconds.

**Leonardo model selection:**
- Icons (1:1): Phoenix 1.0, 1024×1024, alchemy mode, ILLUSTRATION preset → downscale to 256×256
- Main images (4:3): Phoenix 1.0, 1024×768, alchemy mode, PHOTOGRAPHY preset
- Winner composites (16:9): FLUX Kontext, 1248×704, icon as contextImage

**API key:** Stored in Django settings via environment variable `LEONARDO_API_KEY`.

### 4. Generation as a django-task

The generation workflow runs as a `django-task` (consistent with existing `generate_image_variants` task):

```python
@task()
def generate_project_image(generation_request_id: str) -> None:
    HANDLERS.leonardo.generate(generation_request_id)
```

The API endpoint creates the `ImageGenerationRequest` record and enqueues this task. The frontend polls a status endpoint to track progress and display results.

### 5. Frontend generation dialog

A shared React dialog component used by both admin pages and project owner pages:

**Props:** project, purpose, onComplete
**State machine:**
```
idle → editing_prompt → generating → selecting → confirmed
```

**Flow:**
1. Dialog opens with pre-filled prompt based on project metadata and purpose
2. For main_image: shows screenshot selector + device frame picker (mobile/laptop/watch)
3. User can edit prompt, set variant count (1-4)
4. On generate: POST to API, dialog shows spinner
5. Poll generation status endpoint until complete
6. Show variant grid, user clicks to select
7. On confirm: POST to accept endpoint, marks selected image as `active`, discards others

### 6. Admin pages in web-ui

New admin-only section accessible via profile dropdown link:

**`/admin/projects`** — Project image completeness dashboard
- Table: project name, owner, icon status, main image status, winner composite status (if winner)
- Status indicators: ✓ active, ○ proposed, ✗ missing
- Filters: "missing images", "has proposals pending"
- Click row → navigate to `/admin/projects/{id}`

**`/admin/projects/{id}`** — Per-project image management
- Image slots: icon, main image, winner composite (if applicable)
- Each slot shows: current active image, any proposed images, generation history
- Generate button per slot → opens generation dialog
- Can accept/reject proposals on behalf of user

**Auth:** Pages check user's group membership (ADMIN group) via the existing auth system. API endpoints check the same.

### 7. Project owner image management

On the existing project edit page (My Projects), add an "Images" section:

- Shows purpose-specific image slots: icon, screenshots, main image
- Icon slot: upload or generate button → generation dialog
- Screenshots: existing upload functionality (renamed from "images")
- Main image: generate from screenshot (with device frame selector) or generate abstract
- Proposed images shown with accept/reject/regenerate actions
- Banner showing "Upload an icon to appear on the projects listing" if missing

### 8. API endpoints

New endpoints under `/api/`:

```
POST   /api/images/generate          # Create generation request + enqueue task
GET    /api/images/generate/{id}      # Poll generation status + results
POST   /api/images/{id}/accept        # Mark proposed image as active
POST   /api/images/{id}/reject        # Remove proposed image
GET    /api/projects/{id}/images      # Get images grouped by purpose
```

Admin-only endpoints:
```
GET    /api/admin/projects            # Projects with image completeness data
GET    /api/admin/projects/{id}       # Single project with full image data
```

### 9. Listing page icon gate

The project listing API query adds a filter: only return projects that have at least one `ProjectImage` with `purpose=icon, approval_status=active`. This is applied at the queryset level in `DjangoProjectQuery`.

Projects without an icon are excluded from all listing page sections (Featured, New Arrivals, Category rows, etc.) but remain accessible via direct URL.

### 10. Migration of existing images

Data migration:
1. Set `purpose='screenshot'` and `approval_status='active'` for all existing `ProjectImage` rows
2. No changes to `is_main` — it continues to work as the fallback layer

This is safe because the listing page design spec already handles the case where purpose-specific images are missing (falls back to `is_main`, then gradient).

## Risks / Trade-offs

**[Leonardo API costs]** → Each generation costs 8-34 credits depending on model. Mitigation: generation is manual (admin/user triggered), not automatic. Monitor credit usage. Start with Phoenix (cheaper) for icons and main images.

**[Leonardo API availability]** → External dependency. Mitigation: generation requests have failure status, UI shows clear error states, users can always upload manually.

**[Polling vs webhooks]** → Polling is simpler but uses more API calls. Mitigation: Leonardo generations complete in seconds; exponential backoff limits calls to ~5-8 per generation. Can switch to webhooks later if needed.

**[Icon hard gate excludes existing projects]** → All current projects lack icons. Mitigation: Admin dashboard enables bulk generation. Roll out gate only after generating icons for all active projects. Consider a grace period or staged rollout.

**[Multiple proposed images per slot]** → A project could accumulate many proposed images. Mitigation: when a new generation completes, previous proposed images for the same purpose are auto-deleted.

## Open Questions

- Should the icon gate be behind a feature flag during rollout, or do we generate all icons before enabling it?
- What's the prompt template strategy? Hardcoded templates per purpose, or configurable by admin?
- Should we store the Leonardo CDN URLs as a fallback, or always copy images to our S3?
