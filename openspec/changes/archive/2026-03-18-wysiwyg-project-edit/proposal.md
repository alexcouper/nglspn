## Why

The project detail page was recently reworked with a perspective image layout, title banner, and tabbed content area. The edit page (`/my-projects/[id]`) still uses a traditional form layout that looks nothing like the public page. This disconnect means authors can't see how their project will actually appear while editing. A WYSIWYG-style editor that mirrors the public page layout will make editing more intuitive and reduce the preview/edit toggle friction.

## What Changes

- **Extract shared project page component**: Break the public project detail rendering (`ProjectDetailContent` + `ProjectTitleBanner`) into a reusable component that both `/projects/[id]` and `/my-projects/[id]` preview mode can use
- **WYSIWYG edit mode**: Replace the traditional form layout with an in-place editing experience that mirrors the project page structure:
  - **Top banner area**: Title, tagline, and website URL become inline text inputs (author remains displayed but not editable)
  - **Left sidebar**: Image upload/management appears where images are displayed on the public page; tag selection appears below images where tags are shown on the public page
  - **Main content area**: Description becomes a large markdown textarea in the main content zone
  - **Tabs area**: A "Settings" tab replaces the "Discussions" tab for any additional settings that don't fit naturally into the page layout (status display, etc.)
- **Preview mode reuses public page component**: The edit/preview toggle stays, but preview renders the exact same shared component used by the public project page
- **Remove `EditProjectDetail` and `ReadOnlyProjectDetail`**: These get replaced by the new WYSIWYG layout and the shared view component respectively

## Capabilities

### New Capabilities

- `wysiwyg-project-edit`: In-place project editing that mirrors the public project page layout — editable top banner fields, inline image management in the sidebar, markdown description in the main content area, and a settings tab for tags and metadata

### Modified Capabilities

_(none — `image-variants` spec is unaffected; image upload/display mechanics stay the same, only their placement in the edit UI changes)_

## Impact

- **Frontend only**: All changes are in `src/web-ui/`
- **Files replaced**: `EditProjectDetail.tsx` and `ReadOnlyProjectDetail.tsx` will be removed or gutted
- **Files refactored**: `ProjectDetailContent.tsx` and `ProjectTitleBanner.tsx` need to be extracted into shared components that accept edit-mode props or render slots
- **File modified**: `ProjectDetail.tsx` (the edit page wrapper) will orchestrate the new WYSIWYG layout
- **No API changes**: The existing `ProjectFormData` model and API endpoints remain the same
- **No backend changes**: Django API is unaffected
