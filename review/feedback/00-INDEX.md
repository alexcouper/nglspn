# Feedback on the review — index

One document per finding Alex annotated in `review/00-SUMMARY.md`. B1, B2 and I8
carried "this is fine" comments and have no document.

**Nothing here has been applied.** Each document contains the proposed patch;
they are proposals awaiting approval.

| # | Document | Finding | Type | Effort | Recommendation |
|---|---|---|---|---|---|
| 01 | `01-prefetch-unfiltered-gallery.md` | I1 | fix | S | Replace **3** bare-string prefetches with `Prefetch(…, queryset=project_gallery_images())` |
| 02 | `02-article-delete-orphans-s3.md` | I2 | fix | M | `pre_delete` tombstone table drained by a worker; also drains the PENDING leak |
| 03 | `03-publish-fanout-async.md` | I3 | fix | S/M | Enqueue a task **inside** `publish`'s transaction |
| 04 | `04-draft-deleted-mid-upload.md` | I4 | answer | — | Narrower than reviewed — but exposes a **blocker** the review missed |
| 05 | `05-new-route-typing-lost.md` | I5 | fix | S | `window.history.replaceState` instead of `router.replace` |
| 06 | `06-listing-tab-publishes-unsaved-edits.md` | I6 | answer | S | Not as big as assumed — empty `PATCH {}`, ~half a day |
| 07 | `07-empty-follow-rule.md` | I7 | fix | M | Make the read path authoritative; no migration required |
| 08 | `08-ci-run-vitest.md` | I9 | fix | S | One line; defer Playwright, with reasons |
| 09 | `09-ci-extra-tests-stage.md` | I10 | fix | S | `EXTRA_TESTS` variable in `app-common.mk`; VCS-neutral drift check |
| 10 | `10-use-article-draft-refactor.md` | Arch 1 | proposal | L | Six units; fix I4/I5 **first**, decompose after |
| 11 | `11-repo-images.md` | Arch 2 | fix | M | `REPO.images`; scope is 8 call sites, not 4 |
| 12 | `12-derive-summary-single-home.md` | Arch 3 | fix | S | Bell uses `article.summary or derive_summary(…)`; keep `_body_excerpt` for discussions |
| 13 | `13-prism-bundle-size.md` | Minor | fix | S | `generator` + `refractor/core` with 12 grammars; ~185 kB gz off every article load |
| 14 | `14-sanitizer-classname-blast-radius.md` | Minor | answer | S | One page, nav included; defacement not XSS |
| 15 | `15-author-facing-error-messages.md` | Minor | fix | S | `describeApiError`; keep transient/invalid as a **type** |
| 16 | `16-article-serialisation-prefetch.md` | Minor | fix | S | Extract `article_detail_queryset()`; −11 queries |
| 17 | `17-untrack-vitest-artifact.md` | Minor | fix | S | Yes — jj-native, root `.gitignore` needs `node_modules/` unanchored |
| 18 | `18-remove-front-end-review.md` | Minor | fix | S | Clean deletion, no dangling refs |
| 19 | `19-claude-md-stale-docs.md` | Minor | fix | S | More is wrong than the three items; `CONTRIBUTING.md` drifts identically |
| 20 | `20-mdxeditor-dependency-weight.md` | Minor | answer | S | Nothing to do — already `ssr: false`, `yjs` never ships |
| 21 | `21-guard-test-projectimage.md` | Minor | fix | S | Ban `get_object_or_404`, not `ProjectImage.objects` |

## Where a document contradicts the review or the brief

Five documents pushed back rather than complying. Each was checked against the
code before being written up here.

- **04** — the mid-upload race is narrow (only an otherwise-empty draft, and the
  `/new` mount never sweeps). But `isUntouched` checks neither `article.state`
  nor whether the article arrived with content, so **clearing the title and body
  of a published, image-less article and navigating away deletes it from the
  server**, with no timing window and no prompt that mentions deletion. Only one
  `<Link>` on the page consults `isDirty()` (`ArticleAuthoringPage.tsx:154`);
  nav-bar links and browser Back bypass it. This is a blocker the review missed
  on a line it was already reading.
- **03** — the brief said to use `transaction.on_commit`. Wrong: `django-tasks`
  and `django-tasks-db` are both 0.12.0 and neither defines
  `ENQUEUE_ON_COMMIT`; the enqueue is an INSERT in the caller's transaction, so
  `on_commit` would open a lost-enqueue window rather than close one.
- **06** — the assumption that this needs draft revisions is wrong. The listing
  tab never needed the *body* persisted; `ArticleUpdate` is all-optional and
  `patch_article` uses `exclude_unset`, so an empty `PATCH {}` works today with
  no schema change, no OpenAPI regen and no migration.
- **21** — both the review's suggestion and the obvious fix are vacuous. The
  guard is a substring check; the router's real access is
  `get_object_or_404(ProjectImage, …)` at `articles.py:292`, which contains no
  `.objects`. Adding `"ProjectImage.objects"` passes today and forever.
- **15** — the brief said user-facing strings are Icelandic (the review skill
  says so). They are not: the only Icelandic in `src/web-ui/src` is the wordmark
  and the `layout.tsx:32-33` tagline. Proposed copy is English to match.

## Corrections to the review's own numbers

- **I1 is three sites, not two** — `handler.py:328`, `:363` (the discussion bell,
  missed), `:377`.
- **Arch 2 is eight call sites, not four** — including a router
  (`my_review.py:24,216`) and a schema (`competition.py:12,71`) importing a
  `django_impl` module directly.
- **Prism registers 333 grammars, not 297** — the barrel entry imports both
  `refractor` (common, 36) and `refractor/all` (297).
- **MDXEditor adds 186 packages, not 242** (lock 768 → 954, none removed).

## Sequencing

```
independent:  17
one edit:     08 + 09  →  then 19 (documents the result)
land together: 11 + 21 (the guard fails until the refactor lands)
               11 + 01 (01 happened because the right spelling lived elsewhere)
fix first:    04, 05   →  then 10 (decomposition fixes neither bug)
last:         18's `review/` cleanup, after every proposal here is actioned
```

## Open decisions for Alex

1. **02** — tombstones (recommended) vs deleting through
   `HANDLERS.images.delete_image`. The tombstone also drains `FOLLOW_UPS` item 5.
2. **06** — ship the empty-`PATCH` fix now and send draft revisions to
   follow-ups, or leave both.
3. **07** — whether re-following should re-enrol channels when the Follow has
   been emptied. The recommendation says yes, only when there is nothing to
   preserve.
4. **13** — option (b) now, or the structurally-right server-render (c) later.
5. **18** — whether `review/` merges at all. The recommendation is no: fold the
   durable output into `openspec/changes/*/feedback.md` and delete the directory.
