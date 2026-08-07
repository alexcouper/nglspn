# Article Image Insert — Design

Date: 2026-08-05
Status: design (pre-implementation)

## Summary

Replace MDXEditor's stock image dialog in the article editor. The toolbar image
button opens the OS file picker directly — pick a file, it uploads and inserts.
Alt text moves to a minimal dialog reached from an existing image's settings
button. Upload progress and failures get a visible home, which they do not have
today.

Addresses "The select image dialog that appears from the library is ugly" in
`openspec/changes/archive/2026-08-07-add-article-authoring/feedback.md`.

Frontend only. No backend change, so no OpenAPI regeneration and no migration.

## Why the stock dialog is wrong

`imagePlugin()` in `src/web-ui/src/app/projects/[slug]/articles/ArticleEditor.tsx:76`
uses MDXEditor's built-in `ImageDialog`. It presents five fields (file, URL with
autocomplete, Alt, Title, and optionally Width/Height) for what is nearly always
"insert this file". Its container class is shared with the small link popover —
`display: flex; align-items: center` with `--spacing-1` padding — so a
five-field form renders vertically centred in a cramped box.

The deeper point: `imagePlugin` already registers `DROP_COMMAND` and
`PASTE_COMMAND` on the editor surface (`plugins/image/index.js:112,119`), both
routed through the same `imageUploadHandler`. Dragging or pasting a file into the
article body already works. The dialog was never the main path — it is the
discoverable path, and it does not need to be a dialog to be discoverable.

## Insert path — no dialog

Remove `<InsertImage />` from the toolbar; add a local `InsertImageButton`.

- Renders a hidden `<input type="file" accept="image/jpeg,image/png,image/webp,image/gif">`
  next to a button built from MDXEditor's exported `ButtonWithTooltip`
  primitive, so it inherits toolbar button styling and hover/disabled states.
  MDXEditor's own icon registry (`iconComponentFor$`) is not part of its public
  type surface, so supply the icon ourselves: `PhotoIcon` from
  `@heroicons/react/24/outline` at `w-5 h-5`, matching `HeroImageUploader.tsx`.
- Click opens the OS file picker.
- On `change`, publish `insertImage$` with `{ file }`. That signal runs the file
  through the configured `imageUploadHandler` (our `uploadProjectImage`) and
  inserts the node with empty alt text. No upload or Lexical code of our own.
- Reset `input.value` after each pick, or re-selecting the same file will not
  fire `change`.

`usePublisher` and `useCellValue` are re-exported from `@mdxeditor/editor`
itself (`dist/index.js:2`), so `@mdxeditor/gurx` does not become a direct
dependency.

## Edit path — alt text only

Pass `imagePlugin({ ImageDialog: ArticleImageDialog })`.

`ArticleImageDialog` returns `null` unless `imageDialogState$.type === 'editing'`.
The `'new'` state can no longer occur — nothing publishes `openNewImageDialog$`
once the stock toolbar button is gone.

For `'editing'` it renders the house `components/Dialog.tsx` (native `<dialog>` +
`showModal()`, so no portal handling) containing one labelled alt-text input
prefilled from `state.initialValues.altText`, with Save/Cancel styled after
`PublishDialog.tsx`.

**Save must pass src and title through.** The plugin's editing branch calls
`imageNode.setSrc(values.src)` and `imageNode.setTitle(values.title)`
unconditionally (`plugins/image/index.js:55-61`). Publish
`saveImage$` with `{ src: state.initialValues.src, title: state.initialValues.title ?? "", altText }`
— omitting either field blanks it on the node. Leave `file` undefined so the
signal takes its `values.src` branch rather than attempting an upload.

Cancel publishes `closeImageDialog$`.

`disableImageSettingsButton` stays false: the settings button is now the only
route to alt text.

## Upload feedback

Today `handleImageUpload` logs to the console and rethrows, because MDXEditor
swallows the error (see the comment at `ArticleEditor.tsx:54`). A rejected upload
— wrong file type, over the 10MB limit, network failure — is invisible to the
author. Removing the dialog removes the last surface that could have shown it.

Wrap `handleImageUpload` so it tracks `uploading` and `error` state in
`ArticleEditor`, and render a status line: "Uploading image…" while in flight,
or the error message with a dismiss control.

The strip sits at the top of the editor's bordered box, above the toolbar —
MDXEditor owns the DOM between its toolbar and its content, so there is no seam
to render into there. Above the toolbar also keeps it on screen; the content
area is `min-h-[60vh]`, so a strip below it would often be scrolled out of view.

Because all three upload routes — toolbar button, drag-onto-body, paste — go
through that one handler, one status line covers all of them. The edit dialog
uploads nothing and needs no indicator.

`uploadProjectImage` exposes an `onProgress` callback, so a percentage is
available if the plain "Uploading image…" proves too coarse in use. Start
without it.

## Dropped

URL field, Title, Width/Height, src autocomplete, and the file input inside a
dialog. `allowSetImageDimensions` stays at its default of false.

Inserting an image by URL is no longer possible. Article images live in project
storage. Existing markdown containing external image URLs still renders and can
have its alt text edited; only the authoring affordance is gone.

## Testing

`src/app/projects/[slug]/articles/image-insert.test.tsx` (vitest):

- `buildAltTextSavePayload` echoes `src` and `title` back. This is the
  regression that matters — getting it wrong silently blanks the image.
- `ImageAltDialog` prefills, saves, and cancels.
- `useImageUploadStatus` moves through uploading → idle, surfaces a rejected
  upload's message, and clears on dismiss.

Testing anything built on `components/Dialog.tsx` needs an `HTMLDialogElement`
polyfill — jsdom ships the element but not `showModal`/`close`. Added to
`src/test/setup.ts` for all specs, not just this one.

`e2e/article-images.spec.ts` (playwright, needs the app and backend running):
insert from the toolbar picker, edit alt text and assert `src` survives, and
assert a rejected upload reaches the status strip. Two constraints shape it —
projects cap at 10 images so each test deletes the images it uploaded, and
`/api/auth/login` is rate limited to 5/minute per IP (`api/routers/auth.py:106`)
so the file logs in once and runs serially.
