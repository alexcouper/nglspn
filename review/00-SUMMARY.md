# Review — article authoring branch (`main`..`swzk` / `7a20fb38`)

49 commits, 208 files, ~21.8k insertions. Reviewed fresh, without reference to
the branch's own `REVIEW.md` / `FRONT_END_REVIEW.md` / `FOLLOW_UPS.md`; those
were read afterwards, only to check which findings they already claim closed.

| Document | Contents |
|---|---|
| `01-features-articles.md` | Feature map: authoring, markdown, images, listing image, cropper, summaries. 10 diagrams. |
| `02-features-follows-notifications.md` | Feature map: follows simplification, notifications, cadence split, digest, scheduling. 9 diagrams. |
| `03-backend-review.md` | Backend architecture + latent bugs. |
| `04-frontend-review.md` | Frontend architecture + latent bugs. |
| `05-crosscutting-review.md` | OpenAPI sync, migrations, security, hygiene, CI (commands actually run). |

## What the branch does

Three changes landed on top of each other rather than in sequence:

1. **Article authoring** — a full MDXEditor-based authoring surface under
   `/projects/{slug}/articles`, article rendering, slugs, summaries, inline
   image upload, and a per-project article listing.
2. **Article images separated from project images** — `ProjectImage.article` FK
   as the sole discriminator, `services/image` → `services/images` with split
   gallery/article upload paths and caps (10 project / 30 article).
3. **Follows and cadence simplified** — `FollowChannelPreference`'s two booleans
   collapse into row existence (`FollowedChannel`); `notification_frequency`
   splits into `discussion_email_frequency` + `article_email_frequency`;
   per-article email becomes a batched digest with a management-command
   scheduling seam.

The branch also changed direction twice mid-flight (hero image → listing image;
MDXEditor's insert dialog → direct file picker). Both pivots are complete;
residue is catalogued in `01-features-articles.md` §10.

## Verification performed

All run against the branch, output in `05-crosscutting-review.md`:

- `make lint` (backend) — pass, 353 files formatted.
- `make test` (backend) — **1111 passed** in 4m41s.
- `npm run lint` (web-ui, = eslint + `tsc --noEmit`) — pass.
- `npx vitest run` — 153 passed, 11 files.
- `make extract-openapi` — regenerated spec is **byte-identical** to the
  committed `backend-openapi.json`. The contract is in sync.
- `makemigrations --check --dry-run` — `No changes detected`. No missing
  migration.

The house checklist's usual blockers are all clean: no stale OpenAPI, no missing
migration, no authorisation hole (all ten article endpoints go through
`require_full_edit` / `resolve_visible_project_or_404`, and every id-addressed
object is re-checked against the project in the URL), no kennitala exposure, no
new `X-Forwarded-For` reader, no hardcoded secrets, no `naglasupan.com`.

## Blockers — release sequencing, not code

### B1. Digests stop silently on deploy unless the infra repo ships first

Alex: this is fine. Already sorted

`api/tasks/notifications.py` — `send_hourly_notifications` and
`send_daily_notifications` are deleted, replaced by five per-kind tasks.
Verified: nothing in this repo enqueues them. The schedule lives in the
`naglasupan-hq` infra repo, whose CronJobs `INSERT` a hard-coded `task_path`
straight into `django_tasks_database_dbtaskresult`. That INSERT succeeds
whatever string it carries; only the worker discovers the path no longer
resolves. Every digest email stops, and nothing fails visibly.

`apps/notifications/management/commands/enqueue_digest.py` is the correct fix —
the cron names a stable CLI, an unknown `--kind`/`--cadence` is a non-zero exit
on the job itself. It just isn't wired up.
`openspec/changes/simplify-follow-and-cadence/tasks.md:51` is unticked.

`send_article_digest_weekly` has never been scheduled at all.

### B2. Two column drops with no drain window

`follows/0005` (drops `email_enabled`, `in_app_enabled`) and `users/0019`
(drops `notification_frequency`) run from `entrypoint.sh:8` in the new
container while old containers are still serving. Old code `SELECT`s those
columns explicitly, so the old pods 500 for the length of the rollout. Both
openspec task lists flag this; both entries are unticked.

Either split into deploy-then-drop, or accept a maintenance window
deliberately. It is currently neither.


Alex: this is fine. maintenance window scheduled.

## Important

### I1. Two prefetch sites still hand the icon resolver an unfiltered gallery

`services/notifications/django_impl/handler.py:328` (digest) and `:377` (bell)
prefetch the bare string `"article__project__images__variants"` rather than
going through `project_gallery_images()`. `get_project_icon_url` →
`resolve_image_by_purpose` ends its fallback chain at
`images[0]` (`services/project/django_impl/query.py:105`) with no filtering at
all. So a project whose first image is an article figure, or a `PENDING` row
whose S3 object was never written, gets that as its icon — a wrong or broken
`<img>` in the digest email and the notification dropdown.

This is the same defect the branch already fixed on the Following page
(`REVIEW.md` finding 4). Two sites were missed.

Alex: fix this

### I2. Deleting an article orphans its S3 objects irrecoverably

`services/articles/django_impl/handler.py:169` —
`Article.objects.filter(pk=…).delete()` cascades the `ProjectImage` rows
(`apps/projects/models.py:238`, `on_delete=CASCADE`). Storage cleanup lives
only in `HANDLERS.images.delete_image`, which this path never calls. Unlike the
known `PENDING`-row leak (`FOLLOW_UPS.md` item 5), the `storage_key`s go with
the rows, so no future sweep can find the objects.

Alex: What do you suggest here?

### I3. Article publish fans out notifications inline in the request

`services/articles/django_impl/handler.py:160`. Discussions enqueue a task
(`services/discussions/django_impl/handler.py:45`); articles call
`HANDLERS.notifications.create_notifications_for_article` directly. Every
active user auto-follows the house project, so a house-channel publish is ~2N
queries inside the POST — precisely the "ranking day" case the new logging at
`:232` was added to measure. House rule: heavy work goes through the task
runner.

Alex: Good point, we should be doing this async. Propose a change.

### I4. Leaving the editor mid-upload deletes the draft

`useArticleDraft.ts:162` sweeps "untouched" drafts on unmount, and `isUntouched`
(`:43`) tests `article.images.length === 0`. Verified: nothing updates
`article.images` for inline uploads — `useImageUploadStatus.ts:25` never touches
draft state. MDXEditor awaits the upload before inserting the node, so during
the upload the body is empty, `isDirty()` is false, no confirm fires, and
`api.articles.delete` runs. Draft gone, upload orphaned, no message.

Alex: I don't really follow what the problem case is here. Is this only when first starting a draft, if you navigate away whilst starting you don't get it? or is this navigating away mid upload of an image on the draft results in the whole draft being deleted regardless of the state?


### I5. Text typed immediately after `/new` is discarded

`useArticleDraft.ts:113` issues `router.replace` to `/edit/<id>` and then,
without awaiting it, sets form state and `isLoading = false` — a fully
interactive editor on a page that is already navigating away. `/new` and
`/edit` are different routes, so the landing page remounts and refetches an
article with `title: ""`, `body: ""`. On a slow connection that is a 0.5–3 s
window in which typing is silently lost.

Alex: what do you suggest here?

### I6. Clicking "Listing settings" pushes unsaved edits live

`ArticleAuthoringPage.tsx:131` calls `draft.save()` before opening the tab. The
update endpoint is the same for published articles, so half-finished body text
goes live with no confirmation. The comment explains why the save is needed —
the summary is derived server-side — but not why it is safe on a published
article. It isn't.

Alex: Interesting point! I assume fixing this would mean having the idea of an unpublished
revision or similar. Quite a big change. We can discuss this but I think if it's as big
as i think it is we'll need to push that to follow ups.

### I7. The "an empty Follow is deleted" rule holds in only one place

`services/follows/django_impl/handler.py:64`. Reachable without any
concurrency: the owner deletes a channel, `FollowedChannel` cascades, and a user
whose last followed channel it was keeps a `Follow` with zero children
reporting `is_following = true` forever. Recovery is trapped, because `follow()`
only enrols channels when `created=True` (`:24`). This is the same divergence
migration `0004` knowingly leaves behind — but as a live code path, not a
historical artifact.

Alex: Great point. Suggest some fixes.

### I8. `users/0018` re-subscribes a cohort the follows sweep does not cover

A user with `notification_frequency="never"` and a surviving `FollowedChannel`
previously received no article email; they now get an hourly digest.
`REVIEW.md` argues correctly that `notification_frequency` carried no *article*
consent — but that argument is about the broadcast channels seeded by
`follows/0002`, and does not cover this cohort. Worth a deliberate decision
rather than a default, since it is unwindable only before the first send.

Alex: Notification frequency was only about discussions before. We're good here

### I9. CI never runs the tests this branch adds

`.github/workflows/ci.yml` runs `make lint` and `make build-app` for web-ui —
no vitest, no Playwright. Verified. 89 new vitest tests and two Playwright specs
do not execute on a PR, including `markdown-parity.test.tsx`, which is the only
guard against the editor's and the read page's markdown pipelines drifting
apart. One line.

Alex: Yes let's have the ci run the vitest tests.

### I10. CI does not enforce OpenAPI regeneration

`npm run generate-types` reads the *committed* JSON, so a stale spec passes
green. The contract is in sync here only because the author regenerated by hand.
Adding `make extract-openapi && git diff --exit-code` to the backend job closes
the repo's most-forgotten step permanently.

Alex: Add that step too to make sure this is done. But do it by adding a stage
that any service could add and using that in the for now hardcoded pipeline.
eg a "make extra-tests" that we run in both web-ui and django-backend and one can be
a no-op for now.

## Architecture and maintenance

The layering is respected. Routers orchestrate, services own the writes, and the
new article endpoints use the shared helpers rather than inventing their own
auth. `services/image` → `services/images` is complete — nothing points at the
old path. `CroppedImage` / `ImageCropper` are genuinely domain-free. The
comments explain *why*. This is better organised than the size of the diff
suggests.

Three things will cost later:

1. **`useArticleDraft` is doing too much** — 386 lines, a 21-member return, and
   it owns routing, eager draft creation, the unmount sweep, `beforeunload`,
   form state and persistence. I4 and I5 both fall directly out of routing
   living inside a state hook; the `leaving` ref exists only to paper over that.
   `ArticleFormState.body` is a trap field — always stale except immediately
   after `snapshotForm()`.

Alex: Write a proposal of what you recommend changing

2. **There is no `REPO.images`**, so four router call sites hand-roll
   `ProjectImage` filters (`articles.py:292`, `my_projects.py:253,282,321`).
   `article__isnull=True` — the "project endpoints must not touch article
   images" rule — is written out three times. This is the same shape as the
   five-places problem the branch's own design note diagnosed and half-fixed;
   the queryset exists (`project_gallery_images()`), the callers just don't all
   use it. I1 is what happens when one forgets.

Alex: Fix this and have things use REPO.images

3. **`derive_summary` has a second implementation.** Its docstring says it
   "lives only here so a second implementation cannot drift" — and then
   `services/notifications/django_impl/handler.py:123` does
   `_body_excerpt(article.body)`, a raw-markdown slice that ignores the authored
   summary. The bell shows `##` and `![](…)` where every other surface shows
   prose.

Alex: This sounds bad, can we propose a fix?

## Minor

- `ArticleRenderContent.tsx` is `"use client"` and pulls `rehype-prism-plus`'s
  default export, which is built on `refractor/all` — 297 grammars shipped to
  the browser where the editor offers 12. The rest of the app renders markdown
  in server components.
  Alex: What do you suggest?
- `sanitize-schema.ts:38` adds a bare `"className"` to `span`/`pre`/`code`,
  which in `hast-util-sanitize` means *any value*. Not script execution — the
  rest of the schema is sound and correctly refuses `style` — but a
  `full_edit` contributor can write `<span class="fixed inset-0 z-50 bg-white">`
  and cover the page. Prism needs a regex allow-list, not a bare pass.

  Alex: If a contributor did this would it alter the entire site, or just their own article?

- Raw API error strings reach authors: a backend blip during Save puts "Token
  refresh failed" in red next to the button (`useArticleDraft.ts:141,287,347`).
  `publish()` already narrows on `ApiRequestError` — that is the pattern.

  Alex: What do you suggest?

- `PATCH` / `publish` serialise `ArticleOut` off a queryset missing
  `images__variants` (`services/articles/django_impl/handler.py:353`) — ~13
  avoidable queries per *Save draft* at 12 figures.

Alex: What do you suggest?

- `node_modules/.vite/vitest/…/results.json` is committed (added in `41b79ccf`).
  The root has no `node_modules` ignore — only the directory-anchored
  `/node_modules` in `src/web-ui/.gitignore:4`. The file records two test files
  as failing; both pass now.

Alex: Oops, we should remove this from the set of git tracked things right?

- `REVIEW.md`, `FRONT_END_REVIEW.md` and `FOLLOW_UPS.md` are committed at the
  repo root. Working notes, not product. `REVIEW.md` is already deleted in the
  working copy; the other two aren't.

Alex: Remove FRONT_END_REVIEW but let's keep follow ups, it'll ironically be deleted in a follow up

- `CLAUDE.md` documents `make ci`, `scripts/ci/` and `infra/prod/app/`. None of
  the three exist in this repo. Verified.

Alex: insteresting - remove the old documentation

- `@mdxeditor/editor` brings 242 transitive packages, including an unused CRDT
  runtime (`yjs`/`lib0`), 21 CodeMirror language packs and a second markdown
  pipeline. All MIT, none with an advisory — but invisible from the four-line
  `package.json` diff.

Alex: what do you suggest?

- The guard test at `test_articles.py:902` enumerates `Article` / `Channel` /
  `FollowedChannel` but not `ProjectImage` — the model the file actually
  hand-queries.

Alex: what do you suggest?

## Verdict

The code is in better shape than a 22k-line branch by an agent has any right to
be, and the two review rounds the branch carries did real work — every blocker
they raised is genuinely closed, including the one they had to re-diagnose.

Nothing here blocks on correctness of the code itself. What blocks is the
release: B1 and B2 are both deploy-sequencing, both known and written down in
the openspec tasks, and both still unticked. Land the infra-repo cron change
first, and decide the column-drop question deliberately.

Of the code findings, I1–I3 and I4–I6 are worth fixing in this change. I8 is a
consent decision that has to be made before the first digest goes out, not
after. The rest can follow.
