## Context

The public project page (`/projects/[id]`) has a distinct layout: a `ProjectTitleBanner` (title, tagline, author, URL) followed by a two-column body with a 280px left sidebar (images, thumbnails, tags, date) and a main content area (tabs for description/discussions, markdown rendering, winner banner).

The edit page (`/my-projects/[id]`) currently uses a completely different layout — a white card with a toolbar, containing either `EditProjectDetail` (traditional form) or `ReadOnlyProjectDetail` (a separate read-only renderer). Neither matches the public page visually.

The goal is to make editing feel like you're on the project page itself, with editable fields appearing exactly where their read-only counterparts live.

## Goals / Non-Goals

**Goals:**

- Edit mode mirrors the public project page layout (banner → two-column body)
- Each editable field appears in the same position as its read-only version
- Preview mode renders the exact same component as the public page
- The edit/preview toggle, save, and delete actions remain accessible
- Existing functionality (image upload/delete/reorder, tag selection, markdown description) is preserved

**Non-Goals:**

- Rich text / WYSIWYG markdown editor — description remains a plain textarea with markdown support
- Inline editing on the actual public page (this is still `/my-projects/[id]`)
- Changes to the Django API or data model
- Mobile-optimized edit layout (functional on mobile is fine, but the WYSIWYG spatial mapping is a desktop-first concern)

## Decisions

### 1. Extract a shared `ProjectPageLayout` component

**Decision:** Create a `ProjectPageLayout` component that encodes the page structure (banner + two-column body) and accepts render slots for each zone.

**Rationale:** Both the public page and edit preview need identical layout. Rather than duplicating the structure or adding `isEditing` conditionals throughout `ProjectDetailContent`, a layout component with slots keeps each concern clean. The public page passes read-only content into slots; the edit page passes form fields.

**Alternatives considered:**
- *Add `isEditing` props to existing components* — Would litter `ProjectDetailContent` and `ProjectTitleBanner` with conditionals, making them harder to maintain.
- *Reuse `ProjectDetailContent` directly for preview and build edit separately* — Still results in two parallel layout implementations that drift.

**Shape:**

```tsx
<ProjectPageLayout
  banner={<ProjectTitleBanner project={...} />}   // or editable banner
  sidebar={<>images, tags, date</>}
  tabs={[{ id, label, content }]}
  winnerBanner={...}
/>
```

### 2. Editable banner component

**Decision:** Create an `EditableProjectBanner` that renders the same `section > max-w-5xl` wrapper as `ProjectTitleBanner` but with text inputs for title, tagline, and website URL. Author remains displayed as text (derived from the current user, not editable).

**Rationale:** Keeps the banner zone visually consistent — same padding, same vertical rhythm — while swapping display elements for inputs. The inputs should be styled to blend in (minimal borders, same font sizes) so it feels like editing the page itself.

### 3. Sidebar: images + tags in-place

**Decision:** In edit mode the sidebar renders the same 280px sticky column but with:
- `ImageGallery` in editable mode (existing `editable` prop) plus `ImageDropZone` below it
- `TagSidebarSelector` below images, where `TagGroup` displays in the public view

**Rationale:** These components already exist and have the right edit/view modes. Placing them in the sidebar position achieves the WYSIWYG effect with no new UI to build. The tag selector fits naturally here since tags display in the sidebar on the public page.

### 4. Main content area: description textarea + settings tab

**Decision:** The main content area uses the same tab system. In edit mode:
- "Description" tab shows a large markdown textarea (instead of rendered markdown)
- "Settings" tab (replacing "Discussions") shows status display and any future settings

**Rationale:** Keeps the tab structure consistent. Description is the primary content on the public page and should remain the primary editing area. Settings tab is a catch-all for metadata that doesn't map to a specific page zone (currently just status — may grow later).

### 5. Toolbar placement

**Decision:** Move the edit/preview toggle and action buttons (save, delete) into a sticky toolbar above the banner, styled as a thin bar. This replaces the current card-based toolbar.

**Rationale:** The old toolbar lived inside a white card wrapper that no longer exists in the new layout. A top toolbar (below the nav, above the banner) keeps actions accessible without breaking the page-like feel. It can use `sticky top-14` to stay visible during scroll (14 = nav height).

### 6. Preview mode reuses public page components

**Decision:** When toggled to preview, render the actual `ProjectTitleBanner` + `ProjectDetailContent` with the current form data assembled into a `Project` object (the existing `previewProject` pattern in `ProjectDetail.tsx`).

**Rationale:** Guarantees pixel-perfect preview. The `previewProject` assembly already exists — we just need to pass it to the public components instead of `ReadOnlyProjectDetail`.

### 7. Files to create / modify / delete

| Action | File | Notes |
|--------|------|-------|
| Create | `components/ProjectPageLayout.tsx` | Shared layout shell with slots |
| Create | `my-projects/[id]/EditableProjectBanner.tsx` | Editable version of the title banner |
| Create | `my-projects/[id]/EditProjectContent.tsx` | Edit-mode main content (sidebar + tabs) |
| Modify | `my-projects/[id]/page.tsx` | Remove static "Edit Project" header, use new layout |
| Modify | `my-projects/[id]/ProjectDetail.tsx` | Orchestrate new layout, remove old card wrapper |
| Modify | `projects/[id]/page.tsx` | Use `ProjectPageLayout` for structure |
| Modify | `projects/[id]/ProjectDetailContent.tsx` | Extract layout into `ProjectPageLayout`, keep content logic |
| Delete | `my-projects/[id]/EditProjectDetail.tsx` | Replaced by `EditProjectContent` + `EditableProjectBanner` |
| Delete | `my-projects/[id]/ReadOnlyProjectDetail.tsx` | Replaced by reusing public components for preview |

## Risks / Trade-offs

**Sidebar gets tall in edit mode** — Image gallery + drop zone + tag selector is more content than the read-only sidebar. → Mitigation: the sidebar is already `sticky` with scroll. On short viewports, users scroll the sidebar naturally. Can cap tag selector height with overflow-auto if needed.

**Form field styling must match page aesthetics** — Inputs that look too "formy" break the WYSIWYG illusion. → Mitigation: Use borderless/ghost-style inputs that match the text styling (same font-size, font-weight, color) with subtle focus indicators.

**`ProjectPageLayout` extraction is a refactor of the public page** — Touching the working public page introduces regression risk. → Mitigation: The public page's rendered output should be identical after the refactor. Verify visually before moving to edit mode work.

**Mobile edit experience is functional but not WYSIWYG** — The two-column layout collapses on mobile, so the spatial mapping breaks down. → Mitigation: This is explicitly a non-goal. The stacked mobile layout still works for editing; it just doesn't feel like "editing the page".
