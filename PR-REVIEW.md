# Review — last 3 jj changes since `main`

The three meaningful changes since `main`:

| change | what | size |
|---|---|---|
| `wqlr` | Model + slug + notification constraint tests | 7 files, +338 |
| `xyvu` | tasks.md/design.md updates only | 2 files |
| `nxoo` | Article authoring frontend (sections 11+12+12B) | 27 files, +4845 |

## What's good

- **Comments earn their keep.** The "why" is documented in the non-obvious places: plugin ordering in `ArticleRenderContent.tsx:115-120`, the sanitize-allowlist rationale in `sanitize-schema.ts:1-22`, the `bodyRef`/MDXEditor re-keying note in `ArticleAuthoringPage.tsx:52-54`, the draft-sort `updated_at` caveat in `MyProjectArticles.tsx:18-20`. This is the right level of commenting.
- **Sanitize allowlist is conservative** and the parity test (`markdown-parity.test.tsx`) actually exercises XSS vectors (`<script>`, `style=`, `javascript:` URLs, `onerror=`) rather than just happy paths. The two-pipeline split (markdown-only vs full read-page) is a good idea — when a regression appears you can tell which layer broke.
- **Server/client API split is principled** (`lib/api/server.ts` for SSR with `cache: "no-store"`, `lib/api/*Client` for the browser). `ApiNotFoundError` → `notFound()` mapping is consistent across the three new pages.
- **Tests use factories** (`ArticleFactory`, `NotificationFactory`) and per-concern test classes with descriptive names — matches the CLAUDE.md guidance.
- **Dynamic import of MDXEditor** with `ssr: false` + a skeleton fallback is right; pulling MDXEditor into the SSR bundle would be painful.

## Duplication & simplification opportunities

### 1. `uploadInlineImage` reimplements `useImageUpload`
`ArticleEditor.tsx:43-74` does the same presigned-URL → XHR → complete flow as `hooks/useImageUpload.ts:60-114`, minus progress tracking. Two paths that will drift. Suggest extracting the bare promise (without React state) into `lib/uploadProjectImage.ts` and having both the hook and the inline handler call it. Pure refactor, no behaviour change.

### 2. Three new page wrappers all repeat the same boilerplate
`articles/new/page.tsx`, `articles/edit/[articleId]/page.tsx`, and `articles/[articleSlug]/page.tsx` each do:
```ts
try { project = await fetchProject(slug); }
catch (err) { if (err instanceof ApiNotFoundError) notFound(); throw err; }
```
With the pre-existing `[slug]/page.tsx` that's now 5 callers. A one-line helper `await getProjectOr404(slug)` in `lib/api/server.ts` would remove the awkward `let project; try { … }` pattern.

### 3. Date formatting copy-pasted in three places
`{ year: "numeric", month: "long", day: "numeric" }` (and a `"short"` variant) appears in `ArticleRenderContent.tsx:78`, `ArticlesList.tsx:96`, `MyProjectArticles.tsx:127`. There's no `formatDate` in `lib/utils.ts` yet; this change is the right moment to add one. Bonus: `formatDateRange` is already duplicated between two competitions files, so the helper has more than one customer.

### 4. `ArticlesList` and `MyProjectArticles` overlap heavily
Both fetch `api.articles.list(slug)`, do their own sort + skeleton + error-banner, and render the same hero-thumb + channel + title row. They legitimately differ (public-only vs include-drafts, with-badge vs without), but the fetch/sort/error machinery and the row shape could become `useProjectArticles({ includeDrafts })` + `<ArticleRow variant="public" | "owner" />`. As written, a visual tweak needs touching both files.

### 5. `ArticleAuthoringPage` is doing too much
394 lines spanning auth gate, channels fetch, article load, form state, body-ref handling, save/publish/delete, sticky toolbar, breadcrumb, and dialog. The form/persistence half (`form`, `bodyRef`, `persistDraft`, `handleSave`, `handlePublish`, `handleDelete`) is a hook waiting to happen — `useArticleDraft({ project, mode, articleId })` returning `{ form, updateForm, save, publish, delete, status }` would leave the component as layout + wiring.

Related: `mode: "new" | "edit"` is redundant with `articleId` being present or not. Either drive it off the prop or off the URL — both is defensive overspecification, and the check on line 75 (`mode === "edit" && articleId`) shows the redundancy.

### 6. Snapshotting the form body is repeated 3×
`const current: FormState = { ...form, body: bodyRef.current }` appears in `handleSave`, `handleOpenPublish`, and `handlePublish`. Cheap to forget on a fourth handler. A `snapshotForm()` callback inside the component closes that.

### 7. Slate palette duplicated between CSS and TS
The exact same `rgb(15 23 42)`, `rgb(241 245 249)`, `rgb(148 163 184)`, etc. strings appear in `article-markdown.css:59-132` and `article-codemirror-theme.ts:17-30`. The TS file's own header comment says it's "designed to match" the CSS — that's the design intent, but no mechanism enforces it. Options: (a) lift to CSS custom properties and have the codemirror theme read them, (b) define the palette once in TS and have a small `<style>` inject the matching CSS variables, (c) accept it but add a "keep in sync with X" comment in both files. (a) is the most robust.

## Bugs / loose ends

- **`ChannelDropdown` allows publishing with no channel selected.** When `channels.length === 0` it renders an empty `<option value="">`; nothing in `ArticleAuthoringPage` gates the Save/Publish buttons on `form.channel_id`. The backend will reject it, but the UI should refuse earlier (disable the buttons, or short-circuit with a "create a channel first" panel).
- **`markdown-parity.test.tsx:44` has a dead alias** `const render = renderMarkdown;` that only exists so the first `describe` block reads `render(...)`. Either drop it and inline `renderMarkdown`, or commit to `render` and remove the indirection.
- **Two error types for "not found"** — `ApiNotFoundError` (server) vs `ApiRequestError` with `status` (client). Not new in this change, but the new code adds three more callsites of the server one. Worth unifying eventually.

## Tests (wqlr)

- Coverage is the right shape: XOR guards, partial-unique constraints on both sides (same recipient/article fine, same pair forbidden), slug transliteration + collision walk, project scoping.
- Minor inconsistency: `TestSourceExternalUrlGuard.test_internal_without_external_url_saves` uses `ArticleFactory(...)` (saves) where the failure cases use `.build()` then `.save()`. Both work; one style would read better.
- Mixing the `test_users.py` dead-assertion cleanup (the two removed `email_opt_in_*` keys, since migration 0017 dropped those fields) into a model-tests change is a small reviewability hit. Separate commit would've been clearer; not worth re-shuffling now.

## Process note

`xyvu` is a 2-file doc tweak between two implementation changesets. If you haven't pushed, fold it into `nxoo` so the history is "tests / authoring frontend" rather than "tests / doc / authoring frontend".
