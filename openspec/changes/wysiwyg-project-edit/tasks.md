## 1. Extract shared layout

- [x] 1.1 Create `components/ProjectPageLayout.tsx` with render slots: `banner`, `sidebar`, `tabs` (array of `{id, label, content}`), and optional `winnerBanner`. Encodes the two-column body (280px sidebar + flexible main) and tab rendering.
- [x] 1.2 Refactor `projects/[id]/ProjectDetailContent.tsx` to use `ProjectPageLayout` — move the sidebar (images, thumbnails, tags, date) and main content (winner banner, tabs, description, discussions) into the slot props. Lightbox stays in this component.
- [x] 1.3 Update `projects/[id]/page.tsx` to pass `ProjectTitleBanner` as the banner and `ProjectDetailContent` as the body, using the new layout structure.
- [x] 1.4 Verify the public project page renders identically after the refactor (no visual changes).

## 2. Editable banner

- [x] 2.1 Create `my-projects/[id]/EditableProjectBanner.tsx` with ghost-styled text inputs for title (`text-2xl sm:text-3xl font-semibold`, placeholder "Project Title"), tagline (maxLength 200), and website URL. Display author name as read-only text. Use the same `section > max-w-5xl` wrapper as `ProjectTitleBanner`.
- [x] 2.2 Wire banner inputs to `formData` via `onChange` callback, matching the existing `ProjectFormData` shape (title, tagline, website_url).

## 3. Edit-mode sidebar

- [x] 3.1 Create `my-projects/[id]/EditProjectContent.tsx` that assembles the edit-mode sidebar: `ImageGallery` (editable), `ImageDropZone`, `UploadProgress`, and `TagSidebarSelector` — stacked vertically in a 280px column matching the public sidebar layout.
- [x] 3.2 Wire image handlers (onFilesSelected, onSetMainImage, onDeleteImage) and tag handler (onTagsChange) through props from the parent `ProjectDetail` component.

## 4. Edit-mode main content

- [x] 4.1 Add the "Description" tab to `EditProjectContent` with a large markdown textarea (min-h to fill content area, markdown badge), wired to `formData.description`.
- [x] 4.2 Add the "Settings" tab to `EditProjectContent` displaying project status (pending/approved/rejected badge) and submission date.

## 5. Sticky toolbar

- [x] 5.1 Add a sticky toolbar to `ProjectDetail.tsx` (below nav at `sticky top-14`, above the banner) with edit/preview mode toggle (pencil/eye icons), save button, and delete button. Remove the old card-based toolbar.

## 6. Rewire ProjectDetail orchestration

- [x] 6.1 Rewrite `my-projects/[id]/ProjectDetail.tsx` to use `ProjectPageLayout`: in edit mode pass `EditableProjectBanner` as banner and `EditProjectContent` as body; in preview mode pass `ProjectTitleBanner` and public `ProjectDetailContent` with the `previewProject` data.
- [x] 6.2 Update `my-projects/[id]/page.tsx` to remove the static "Edit Project" header — the banner zone now handles this.
- [x] 6.3 Move the `ProjectFormData` type export to a shared location (or keep in `ProjectDetail.tsx`) since `EditProjectDetail.tsx` is being deleted.

## 7. Cleanup

- [x] 7.1 Delete `my-projects/[id]/EditProjectDetail.tsx`.
- [x] 7.2 Delete `my-projects/[id]/ReadOnlyProjectDetail.tsx`.
- [x] 7.3 Remove any dead imports referencing the deleted files.

## 8. Verify

- [x] 8.1 Run `npm run lint` in `src/web-ui/` and fix any issues.
- [x] 8.2 Verify edit mode: all fields editable in correct positions (banner inputs, sidebar images + tags, description textarea, settings tab).
- [x] 8.3 Verify preview mode: renders identically to the public project page with current form data.
- [x] 8.4 Verify mode switching preserves all form data (round-trip edit → preview → edit).
- [x] 8.5 Verify save/delete still work from the toolbar.
