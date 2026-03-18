## 1. Model Changes & Migration

- [x] 1.1 Add `purpose` field (CharField with choices: icon, screenshot, main_image, winner_composite; default screenshot) and `approval_status` field (CharField with choices: active, proposed; default active) to `ProjectImage` model
- [x] 1.2 Add `generation_request` nullable FK from `ProjectImage` to `ImageGenerationRequest`
- [x] 1.3 Create `ImageGenerationRequest` model with fields: project FK, purpose, prompt_text, device_frame (nullable), reference_image FK (nullable), leonardo_generation_id, leonardo_model_id, width, height, num_variants, status, error_message, created_by FK, created_at, completed_at
- [x] 1.4 Write data migration: set all existing `ProjectImage` rows to `purpose=screenshot`, `approval_status=active`
- [x] 1.5 Run migrations and verify existing images are correctly migrated

## 2. Leonardo AI Service

- [x] 2.1 Create `services/leonardo/handler_interface.py` with `LeonardoHandlerInterface` defining `generate(generation_request_id: str)` method
- [x] 2.2 Create `services/leonardo/django_impl/client.py` — `LeonardoAPIClient` handling HTTP calls: create generation, poll generation status, upload init image (presigned URL flow), download image from CDN URL
- [x] 2.3 Create `services/leonardo/django_impl/handler.py` — `DjangoLeonardoHandler` orchestrating: create DB record → upload reference if needed → call Leonardo API → poll → download results → save to S3 as ProjectImage rows → trigger variant generation → update request status
- [x] 2.4 Add `LEONARDO_API_KEY` to Django settings and environment configuration
- [x] 2.5 Register `LeonardoHandlerInterface` in `services/__init__.py` HandlerServices
- [x] 2.6 Create `api/tasks/leonardo.py` with `generate_project_image` django-task that calls the handler
- [x] 2.7 Write tests for LeonardoAPIClient (mocked HTTP) and DjangoLeonardoHandler (mocked client)

## 3. Backend API Endpoints

- [x] 3.1 Create `api/schemas/image_generation.py` — request/response schemas for generation requests and image purpose data
- [x] 3.2 Create `POST /api/images/generate` endpoint: validates input, creates ImageGenerationRequest, enqueues django-task, returns request ID
- [x] 3.3 Create `GET /api/images/generate/{id}` endpoint: returns generation status and result images when completed
- [x] 3.4 Create `POST /api/images/{id}/accept` endpoint: sets proposed image to active, displaces previous active image for same purpose
- [x] 3.5 Create `POST /api/images/{id}/reject` endpoint: deletes proposed image and its S3 files/variants
- [x] 3.6 Create `GET /api/projects/{id}/images` endpoint: returns images grouped by purpose with active and proposed status
- [x] 3.7 Create `GET /api/admin/projects` endpoint: returns all projects with image completeness summary (admin-only)
- [x] 3.8 Create `GET /api/admin/projects/{id}` endpoint: returns full project data with all images by purpose (admin-only)
- [x] 3.9 Update existing `GET /api/projects` listing query to filter by projects having an active icon

## 4. Frontend: Generation Dialog Component

- [x] 4.1 Create `GenerationDialog` component with states: idle, editing_prompt, generating, selecting, confirmed
- [x] 4.2 Implement prompt pre-fill logic based on project metadata and purpose (icon template, main image template, abstract template, winner composite fixed template)
- [x] 4.3 Implement screenshot selector and device frame picker (mobile/laptop/watch) for main_image purpose
- [x] 4.4 Implement variant count selector (1-4)
- [x] 4.5 Implement generation progress polling — call status endpoint until completed/failed, show spinner
- [x] 4.6 Implement variant grid display with selectable images and confirm action
- [x] 4.7 Wire confirm action to accept endpoint

## 5. Frontend: Admin Pages

- [ ] 5.1 Create `/admin/projects` page with project table showing image completeness indicators (active/proposed/missing per slot)
- [ ] 5.2 Add filtering controls: "missing images" and "has proposals" filters
- [ ] 5.3 Create `/admin/projects/{id}` page showing image slots (icon, main image, screenshots, winner composite) with current images, proposals, and generation history
- [ ] 5.4 Wire generate buttons to open GenerationDialog for each purpose
- [ ] 5.5 Wire accept/reject actions for proposals
- [ ] 5.6 Add admin auth guard — check ADMIN group membership, redirect non-admins
- [ ] 5.7 Add "Admin" link to profile dropdown, visible only to ADMIN group members

## 6. Frontend: Project Owner Image Management

- [ ] 6.1 Add image management section to project edit page with purpose-specific slots: icon, screenshots, main image
- [ ] 6.2 Rename existing image upload UI labels from "images" to "Screenshots" and "Set as main image" to "Set as primary screenshot"
- [ ] 6.3 Add icon slot with upload and generate buttons, wired to GenerationDialog
- [ ] 6.4 Add main image slot with generate button, wired to GenerationDialog (with screenshot/device frame selection when screenshots exist)
- [ ] 6.5 Display proposed images in each slot with accept/reject actions
- [ ] 6.6 Add icon-missing banner: "Upload an icon to appear on the projects listing" with CTA buttons

## 7. OpenAPI & Type Generation

- [ ] 7.1 Run `make extract-openapi` from django-backend to regenerate OpenAPI spec
- [ ] 7.2 Run `npm run generate-types` from web-ui to regenerate TypeScript types

## 8. Testing & Verification

- [ ] 8.1 Run `make lint` in django-backend and fix any issues
- [ ] 8.2 Run `make test` in django-backend and fix any failures
- [ ] 8.3 Run `npm run lint` in web-ui and fix any issues
- [ ] 8.4 Verify admin pages are accessible only to ADMIN group users
- [ ] 8.5 Verify generation dialog works end-to-end for icon generation
- [ ] 8.6 Verify projects without icons are excluded from listing API
- [ ] 8.7 Verify existing images show as screenshots after migration
