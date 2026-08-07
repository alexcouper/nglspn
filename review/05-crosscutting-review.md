# Cross-cutting review — `d2463b33..7a20fb38` (49 commits, 208 files)

Scope: API contract sync, migrations, security/privacy, repo hygiene, CI/build.
Everything below was verified by running the command, not by reading alone,
except where explicitly stated. Working tree was restored to its starting state
(verified: regenerated `backend-openapi.json` byte-identical, tracked vitest
artifact unchanged).

## 1. API contract sync

**Verdict: in sync. No finding.**

Regenerated and diffed:

```
$ cd src/django-backend && make extract-openapi
uv run python scripts/extract_openapi.py
$ git diff --stat -- src/web-ui/backend-openapi.json
(no output — zero diff)
```

The committed `src/web-ui/backend-openapi.json` is byte-identical to what the
current routers/schemas produce. Spot-checked that the new surface is present:

```
/api/projects/{slug}/articles                                        get, post
/api/projects/{slug}/articles/by-slug/{article_slug}                 get
/api/projects/{slug}/articles/{article_id}                           delete, get, patch
/api/projects/{slug}/articles/{article_id}/images/upload-url         post
/api/projects/{slug}/articles/{article_id}/images/{image_id}         delete
/api/projects/{slug}/articles/{article_id}/images/{image_id}/complete post
/api/projects/{slug}/articles/{article_id}/publish                   post
/api/projects/{slug}/channels                                        get, post
/api/projects/{slug}/channels/{channel_id}                           delete, patch
/api/projects/{slug}/channels/{channel_id}/reassign                  post
/api/projects/{slug}/follow/channels/{channel_id}                    delete, post
```

Also verified the spec carries no reference to the columns this branch drops
(`notification_frequency`, `email_enabled`, `in_app_enabled`) — grep over
`backend-openapi.json` and `src/web-ui/src` returns nothing. `UserResponse` now
carries `discussion_email_frequency` / `article_email_frequency` and the spec
agrees.

`src/web-ui/src/lib/api-types.ts` is gitignored (`src/web-ui/.gitignore:46`) and
present on disk. Correct, as noted.

**Related gap, not a contract bug:** nothing in CI enforces this. `.github/workflows/ci.yml:31`
runs `npm run generate-types`, which reads the *committed* JSON. A stale spec
would produce stale types and still pass. The only reason this branch is clean
is that the author regenerated it by hand. See §5.

## 2. Migrations

`makemigrations --check` is clean:

```
$ cd src/django-backend && uv run python manage.py makemigrations --check --dry-run
No changes detected
```

Every model change has a migration. Graph ordering is correct: the two
cross-app edges (`articles/0005` → `projects/0044`, `projects/0045` →
`articles/0005`) are declared and non-circular.

### 2.1 The follows three-step preserves what it claims to, and loses what it says it loses

Verified the migration's own claims against the source it depends on:

- `apps/follows/migrations/0001_initial.py:113` pins `db_table = "follow_channel_preferences"`,
  so `0003`'s `RenameModel` really is state-only. No SQL, no data risk.
- `apps/follows/migrations/0002_seed_channels_and_house_follows.py:77,85,91`
  writes `in_app_enabled=True` unconditionally, and `:76,84` writes
  `email_enabled` from the legacy opt-in booleans. This confirms the sweep's
  reasoning in `0004_sweep_both_off_rows.py:14-32`: keying on
  `email_enabled OR in_app_enabled` would have matched nothing.

Old-boolean combinations after `0004` + `0005`:

| `email_enabled` | `in_app_enabled` | outcome | correct? |
|---|---|---|---|
| T | T | row kept → following | yes |
| T | F | row kept → following | yes (in-app was never a user choice on seeded rows) |
| F | T | row **deleted** → unfollowed | deliberate, documented loss |
| F | F | row deleted → unfollowed | yes |

The `F/T` case is a real preference the collapse cannot represent. It is
documented at `apps/follows/migrations/0004_sweep_both_off_rows.py:24-27` and
in `REVIEW.md` blocker 1, and errs toward silence. Accepted, not a finding.

The one artefact worth carrying forward: `0004` deliberately leaves `Follow`
rows behind when it empties them
(`apps/follows/migrations/0004_sweep_both_off_rows.py:29-38`), so an emptied
`Follow` reports `is_following = true` while delivering nothing. The API's
`unfollow_channel` does the opposite. That is a legacy-only inconsistent state
the code never produces. Documented; low blast radius.

### 2.2 `projects/0044` → `0045` is coherent, and only because both ship together

`0044` adds `ProjectImage.source` (`CharField`, default `"project"`), `0045`
removes it one day later and adds the `article` FK. Both are new in this diff,
so `source` never reaches production carrying data — no loss. It is pure churn
in the migration history (`REVIEW.md` finding 10, marked "Won't do"). Not a
correctness problem. Flagging only because the same pair *would* lose data if
this branch had been deployed at `0044`.

### 2.3 Deploy-order hazard: two column drops with no drain window — **Important**

`src/django-backend/entrypoint.sh:8` runs `manage.py migrate` in the container
entrypoint of the *new* image, before the server starts. There is no separate
migrate step and no `pre-deploy` hook. During a rolling revision swap, the new
container migrates while old containers still serve traffic.

Both of these then break the old containers immediately:

- `apps/follows/migrations/0005_drop_legacy_booleans.py` drops
  `email_enabled` / `in_app_enabled`.
- `apps/users/migrations/0019_drop_notification_frequency.py` drops
  `notification_frequency`.

Django emits explicit column lists in `SELECT`, so any old-code query against
`follow_channel_preferences` or `users` raises `UndefinedColumn` until the old
revision drains. The docstrings on both migrations assert "every reader is gone
by the time this migration ships" — true of the *new* code, not of the old code
still running. This is a real, if brief, window of 500s on login, the follow
popover, and the profile page.

Both `openspec/changes/simplify-follow-and-cadence/tasks.md:121` and
`openspec/changes/add-article-authoring/tasks.md:164` name this exact risk and
are **unticked**. Either accept the blip explicitly, or split `0005`/`0019` into
a follow-up deploy.

### 2.4 `users/0018` does not carry any cadence into `article_email_frequency`

`apps/users/migrations/0018_user_article_email_frequency_and_more.py:5-9` copies
`notification_frequency` into `discussion_email_frequency` only.
`article_email_frequency` lands at its `"hourly"` default for every existing
user, i.e. every user is opted in to a new email stream.

This was reviewed and deliberately chosen — `REVIEW.md` blocker 1 argues
correctly that `notification_frequency` was labelled "how often you receive
discussion notifications" and carries no consent about articles, and that the
real opt-out lived in `FollowedChannel.email_enabled`, handled by
`follows/0004`. The reasoning holds. Recording it here so the deliberate
default is visible to whoever signs off on the deploy, not as a defect.

`reverse_copy` at `:12-15` resets `discussion_email_frequency` to `"hourly"`
rather than restoring prior values — reverse is lossy, but the source column is
untouched at that point, so a forward re-run recovers. Adequately documented.

### 2.5 No new unique constraints or slug backfills

`articles/0002-0005` add no constraints. The `articles_project_slug_uniq`
partial unique constraint is pre-existing (`articles/0001_initial.py:104-108`).
Nothing to backfill or dedupe. No finding.

## 3. Security & privacy

### 3.1 IP trust — no new code, existing code is not forgeable

Grepped the diff: this branch adds **no** new `HTTP_X_FORWARDED_FOR` /
`REMOTE_ADDR` reader. Nothing to flag.

For completeness, the two existing readers, neither touched here:

- `src/django-backend/project_showcase/middleware.py:22-35` — counts back from
  the right by `NUM_TRUSTED_PROXIES`. Correct.
- `src/django-backend/api/rate_limit.py:21-25` — takes `split(",")[-1]`, the
  rightmost entry, but ignores `NUM_TRUSTED_PROXIES`
  (`project_showcase/settings.py:42`, default `1`). At `NUM_TRUSTED_PROXIES=1`
  the two agree and the value is not forgeable. It silently diverges if the
  setting is ever raised above 1. Pre-existing, out of scope for this diff,
  worth a follow-up ticket.

### 3.2 kennitala — not exposed

`kennitala` appears in this diff only in `apps/users/admin.py` (list display and
`search_fields`) and in a test assertion. `api/schemas/user.py` has it on
`UserCreate` (inbound only); neither `UserResponse` nor `PublicUserProfile`
carries it, and it does not appear anywhere in `backend-openapi.json`. No
finding.

### 3.3 Secrets and domain

- No hardcoded secrets in the diff. Regex sweep over added `src/` lines for
  `SECRET|PASSWORD|API_KEY|ACCESS_KEY|token = "…"` returns nothing outside
  `os.getenv` / `settings.` / `process.env`.
- `naglasupan.com` appears nowhere in `src/` or `infra/`. No finding.
- `src/web-ui/next.config.ts` (CSP) is **unchanged** by this branch. Its
  `connect-src` already interpolates `cspApiUrl` / `cspCdnUrl` at line 26. The
  new image upload path PUTs to `https://s3.fr-par.scw.cloud`, which is already
  in the allowlist. No new CSP need, nothing baked that wasn't already.

### 3.4 New upload endpoints — authorisation is correct, size limit is advisory

Authorisation on all three new endpoints
(`src/django-backend/api/routers/articles.py:295`, `:338`, `:372`) goes through
`_get_editable_article` (`:281-287`), which is
`require_full_edit(slug, user_id)` followed by `_get_article_in_project`. Image
lookups then go through `_get_article_image_or_404` (`:289-292`), which filters
`ProjectImage` by `article=article`. A user cannot upload to, complete, or
delete an image on a project or article they lack `full_edit` on, and cannot
address another article's image. Verified by reading; no IDOR.

Validation:

- Content type: allowlisted at
  `src/django-backend/services/images/handler_interface.py:18-25`, enforced at
  `services/images/django_impl/handler.py:130-131`, and the type is signed into
  the presigned PUT (`services/storage.py:53-56`), so S3 rejects a mismatched
  header. Adequate.
- Path traversal: `services/storage.py:36-41` strips everything except
  alphanumerics, `.`, `-`, `_`, and the key is prefixed
  `projects/{project_id}/{uuid}/`. `..` survives the filter as a literal but
  cannot escape an S3 key namespace (no path resolution). No finding.
- **Size: client-declared and never enforced.** `_validate`
  (`services/images/django_impl/handler.py:132-133`) checks the `file_size` the
  browser *says* it will upload against `MAX_FILE_SIZE = 10MB`. The presigned
  URL is generated with `Params` = Bucket/Key/ContentType/ACL only
  (`services/storage.py:48-58`) — **no `content-length-range` condition** — so
  an authenticated user can declare 1 KB and PUT an arbitrarily large object.
  `complete_upload` then only checks `object_exists`
  (`services/images/django_impl/handler.py:82-83`), never the stored size.
  This weakness is pre-existing in `generate_presigned_upload_url`, but the
  branch widens the surface: 30 images per article
  (`services/images/handler_interface.py:16`) against an **uncapped** number of
  articles per project (`services/articles/django_impl/handler.py:69-92` has no
  cap and the route has no rate limit), versus the previous 10-per-project
  gallery ceiling. Bounded storage abuse becomes unbounded.

### 3.5 Email template injection — none

`templates/email/article_digest.mjml` and `.txt` interpolate `article_title`,
`project_title`, `channel_name`, `body_excerpt` and `article_image_url` with
plain `{{ }}`. Django autoescape is on — no `|safe`, no `{% autoescape off %}`
anywhere in the email templates, and `mark_safe` is only used in
`apps/projects/admin.py` on literal strings. `body_excerpt` is additionally
flattened through `services/articles/summary.py`, which strips HTML tags
(`_HTML_TAG_RE`, `:22`) before truncation. No finding.

### 3.6 Raw HTML in article bodies — correctly ordered and locked down

Worth recording since `rehype-raw` is a new dependency and is an XSS primitive
on its own. `src/web-ui/src/app/projects/[slug]/articles/[articleSlug]/ArticleRenderContent.tsx:107-110`
runs `rehypeRaw` → `rehypePrismPlus` → `rehypeSanitize` **last**, which is the
only safe order. `sanitize-schema.ts` extends `defaultSchema` with `figure`,
`figcaption`, `align` on `div`, `width`/`height` on `img`, and `className` on
`pre`/`code`/`span`, and explicitly refuses `style`. Conservative and correctly
reasoned. No finding.

## 4. Repo hygiene

### 4.1 Committed `node_modules` artifact — confirmed, and it records failing tests

`node_modules/.vite/vitest/da39a3ee5e6b4b0d3255bfef95601890afd80709/results.json`
was added in commit `41b79ccf` ("Article hero images, summary, and newsy
listing"). It is tracked (`git ls-files node_modules` returns it, and only it).

Root cause: the only `node_modules` ignore rule is `src/web-ui/.gitignore:4`
(`/node_modules`), which is anchored to that directory. The **root**
`.gitignore` has no `node_modules` entry at all, so a vitest run started from
the repo root created and committed `./node_modules/`. The directory now
contains nothing but this one file.

The file's content is worth reading:

```json
{"version":"3.2.7","results":[
  [":src/web-ui/src/components/article-card.test.tsx",{"duration":0,"failed":true}],
  [":src/web-ui/src/app/projects/[slug]/articles/article-card-preview.test.tsx",{"duration":0,"failed":true}]]}
```

A committed cache recording two failed test files. Both pass now (§5), so it is
stale as well as wrong to commit. Delete the file and add `node_modules/` to the
root `.gitignore`.

### 4.2 Scratch review docs at the repo root — **not new, but growing**

`REVIEW.md` (356 lines at `7a20fb38`), `FRONT_END_REVIEW.md` (301) and
`FOLLOW_UPS.md` (163) are added at the repo root. They are working documents:
`REVIEW.md` opens with a per-finding status table naming jj change IDs
(`xzpr 33b4`, `nnkr b401`, `wvvx`, …), which is session state, not project
documentation.

This is a recurring pattern, not a one-off — history shows `BEFORE_RELEASE.md`
was dropped in `beaa3915` when `REVIEW.md` replaced it, and `QUESTIONS.md` (226
lines) and `docs.md` (77) are already sitting at the root from prior rounds.
Per `CLAUDE.md`'s file-location table and the repo's documentation taxonomy, a
review's durable output belongs in `openspec/changes/*/feedback.md` (which
`add-article-authoring` already has) or under `docs/`; the transient status
table belongs nowhere in the tree.

Note also that `FOLLOW_UPS.md` records real open work (7 items) — if the root
docs are deleted at merge, those need a home first.

Two live inconsistencies inside `REVIEW.md` as committed:

- Finding 12 ("Article uploads have no cap") is listed **Open** at
  `REVIEW.md:29` and `:282`, but the cap shipped in `99d24cf2`
  (`MAX_IMAGES_PER_ARTICLE = 30`,
  `src/django-backend/services/images/handler_interface.py:16`). Stale.
- The header claims `npx vitest run — 126 passed`; the actual count is now 153
  (§5). Stale.

### 4.3 openspec — archived change is consistent, the two active ones are not complete

| directory | state | tasks |
|---|---|---|
| `openspec/changes/archive/2026-08-06-rework-article-listing-image/` | archived | 63/63 done, 0 open |
| `openspec/changes/add-article-authoring/` | active | 83 done, **11 open** |
| `openspec/changes/simplify-follow-and-cadence/` | active | 59 done, **9 open** |

The archived change is internally consistent and matches what shipped: the
hero→listing rename, `listing_image_mode`, and the crop are all in the code and
migrations. Correctly archived.

The two active changes are correctly left unarchived — the open tasks are real,
not bookkeeping. The consequential ones:

- `simplify-follow-and-cadence/tasks.md:51` (7.7) — **the infra repo's CronJobs
  still `INSERT` the old task paths.** `send_hourly_notifications` /
  `send_daily_notifications` are deleted in this branch
  (`src/django-backend/api/tasks/notifications.py`), replaced by five new task
  functions plus the `enqueue_digest` management command
  (`apps/notifications/management/commands/enqueue_digest.py`) that exists
  precisely to decouple cron from Python symbol names. That seam is good work,
  but until the CronJobs in `naglasupan-hq` are switched to invoke it, **all
  digest email stops on deploy** — silently, because the raw INSERT succeeds
  whatever string it carries and only the worker discovers the dead path. The
  task is marked "Must ship with or before the backend deploy". Still open;
  `REVIEW.md` finding 2 also marks it Open.
- `add-article-authoring/tasks.md:38-39` (5.4, 5.5) — mixed discussion+article
  digest deferred; a recipient with both pending gets two emails. Documented
  as partial, acceptable.
- `add-article-authoring/tasks.md:163-165` and
  `simplify-follow-and-cadence/tasks.md:120-121` — the prod-snapshot dry runs
  of the sweep, and the "resolver and column drop ship together" confirmation.
  See §2.3.
- `simplify-follow-and-cadence/tasks.md:19` (3.2) — the sweep regression test
  was not written and cannot be without a migration-state harness
  (`django-test-migrations`). Honestly unticked rather than quietly dropped.

`docs/superpowers/specs/2026-08-05-article-hero-images-design.md` is correctly
headed `Status: superseded (2026-08-06)`. No stale-doc finding there.

### 4.4 Dependencies — one direct addition, 242 transitive packages

`src/web-ui/package.json` gains four direct deps: `@mdxeditor/editor@^4.0.1`,
`rehype-prism-plus@^2.0.2`, `rehype-raw@^7.0.0`, `rehype-sanitize@^6.0.0`.
`package-lock.json` gains **242** packages and removes 56.

All new packages are MIT. `npm audit --omit=dev` reports 33 vulnerabilities
(1 critical, 20 high) but **none of them trace to a package added here** — the
high/critical set is `protobufjs` (via `@opentelemetry/*`), `sharp` and `next`,
`postcss`, `js-yaml`, `@grpc/grpc-js`, all pre-existing. Versions pulled in are
current: `prismjs@1.30.0`, `lexical@0.35.0`, `parse5@8.0.1`.

The concern is bulk, not vulnerability. `@mdxeditor/editor` drags in:

- the whole **Lexical** editor framework (~25 `@lexical/*` packages),
- **all** of CodeMirror's language packs — `@codemirror/lang-{angular,cpp,css,go,html,java,javascript,jinja,json,less,liquid,markdown,php,python,rust,sass,sql,vue,wast,xml,yaml}` plus the matching `@lezer/*` grammars,
- **`yjs` + `lib0`** — a CRDT collaborative-editing runtime this product does
  not use,
- the full MDX micromark/mdast extension set (`micromark-extension-mdx*`,
  `mdast-util-mdx`) for MDX syntax articles do not support,
- `react-hook-form`, `downshift`, `classnames`, a second Radix surface, and
  `prismjs`/`refractor` alongside the already-present `rehype-prism-plus`.

Duplicated functionality with what is already in the tree: the repo already had
`react-markdown` + `remark` + `remark-gfm` + `remark-html`; it now also carries
MDXEditor's independent markdown pipeline. Two markdown stacks that must be kept
in agreement — which is exactly why
`src/app/projects/[slug]/articles/markdown-parity.test.tsx` had to be written.
That test is the right mitigation, but the underlying duplication is a
maintenance cost worth stating out loud, and it is not visible from the
four-line `package.json` diff.

Actual usage of the new editor is five files
(`ArticleEditor.tsx`, `ArticleImageDialog.tsx`, `InsertImageButton.tsx`,
`buildAltTextSavePayload.ts`, plus the stylesheet import). Whether 242 packages
is the right price for a markdown editor with an image button is a product call,
not a review finding — but it should be a conscious one.

## 5. CI / build

All four commands were run to completion. Literal output:

**`cd src/django-backend && make lint`** — pass

```
uv run ruff check .
All checks passed!
uv run ruff format --check .
353 files already formatted
```

**`cd src/django-backend && make test`** — pass

```
================ 1111 passed, 744 warnings in 280.76s (0:04:40) ================
```

(744 warnings are pre-existing `factory_boy` `_after_postgeneration`
deprecations across `CompetitionFactory` / `BroadcastEmailFactory`, not
introduced here.)

**`cd src/web-ui && npm run lint`** — pass (`eslint && tsc --noEmit`)

```
> web-ui@0.1.0 lint
> eslint && tsc --noEmit

The prop value with an expression type of TSNonNullExpression could not be resolved. Please file an issue ( https://github.com/jsx-eslint/jsx-ast-utils/issues/new ) to get this fixed immediately.
```

Exit 0. The message is a `jsx-ast-utils` limitation warning, not a lint error.

**`cd src/web-ui && npm run test`** — pass (run because CI does not; see below)

```
 RUN  v3.2.4 /Users/alex/Work/codalens/nglspn/nglspn-hq/src/web-ui

 ✓ src/app/projects/[slug]/articles/use-article-draft.test.tsx (19 tests) 152ms
 ✓ src/components/image-cropper.test.tsx (13 tests) 205ms
 ✓ src/app/projects/[slug]/articles/image-insert.test.tsx (13 tests) 100ms
 ✓ src/app/projects/[slug]/articles/article-card-preview.test.tsx (14 tests) 215ms
 ✓ src/components/article-card.test.tsx (14 tests) 229ms
 ✓ src/app/projects/[slug]/articles/listing-image-dialog.test.tsx (12 tests) 286ms
 ✓ src/lib/api/base.test.ts (11 tests) 27ms
 ✓ src/hooks/use-channel-toggle.test.tsx (6 tests) 77ms
 ✓ src/contexts/auth.test.tsx (1 test) 66ms
 ✓ src/app/competitions/[id]/MyRanking.test.tsx (32 tests) 675ms
 ✓ src/app/projects/[slug]/articles/markdown-parity.test.tsx (18 tests) 53ms

 Test Files  11 passed (11)
      Tests  153 passed (153)
   Duration  2.71s
```

### 5.1 CI does not run the frontend tests this branch adds — **Important**

`.github/workflows/ci.yml` `web-ui` job runs `npm ci`, `npm run generate-types`,
`make lint`, `make build-app`. It does **not** run `make test` (vitest) or
`make e2e` (playwright), both of which exist as targets in
`src/web-ui/Makefile:44,47,50`.

This branch adds ~1,700 lines of frontend test — six new vitest suites (89 of the
153 tests) plus two Playwright specs (`e2e/article-images.spec.ts`,
`e2e/article-listing-image.spec.ts`) and their fixtures. None of it runs on a
pull request. A regression in the crop maths, the draft autosave, the alt-text
payload builder, or — most importantly — the **markdown parity between the
editor's pipeline and the read page's** would land green.

Add `- run: make test` to the `web-ui` job. That is one line and it is the
difference between the test investment in this branch being a safety net and
being documentation.

### 5.2 Nothing enforces OpenAPI sync in CI — **Important**

Follows from §1. `npm run generate-types` reads the committed JSON, so a stale
spec produces stale types and passes. The check that would catch it is a single
step in the `django-backend` job:

```yaml
- run: make extract-openapi && git diff --exit-code -- ../web-ui/backend-openapi.json
```

Given `CLAUDE.md` calls the regeneration step out explicitly as something that
MUST be done, and it is the repo's most-forgotten step, it should be enforced by
the machine rather than by the instruction file. It happened to be done
correctly here.

### 5.3 `make ci` does not exist — **Minor**

`CLAUDE.md` documents "Full CI Check: from project root `make ci`" and lists
`scripts/ci/` in the file-locations table. There is no root `Makefile` and no
`scripts/ci/` directory (`scripts/` contains `app-common.mk`, `build.sh`,
`find-free-port.sh`, `set_categories.py`).

This is pre-existing doc drift, but it becomes load-bearing here:
`openspec/changes/add-article-authoring/tasks.md:154` (16.1) is the verification
task "Run `make ci` from project root" and is unticked — it cannot be ticked,
because the command does not exist. Either add the target or fix `CLAUDE.md` and
the task.

## Verdict on cross-cutting concerns

### Blocker

None. The API contract is in sync, migrations are complete and ordered, no PII
leak, no new IP-trust bug, no hardcoded secrets, no template injection, and all
four CI commands pass.

### Important

1. **Digest email stops on deploy unless the infra repo ships first.**
   `openspec/changes/simplify-follow-and-cadence/tasks.md:51`. The old task
   symbols `send_hourly_notifications` / `send_daily_notifications` are deleted
   from `src/django-backend/api/tasks/notifications.py`; the CronJobs in
   `naglasupan-hq` still `INSERT` those paths into the task table, which
   succeeds silently and fails only in the worker. `enqueue_digest` is the
   correct fix and exists — it just is not wired up on the cron side. Ship
   order: infra CronJobs at or before this backend deploy.

2. **Two column drops with no drain window.**
   `apps/follows/migrations/0005_drop_legacy_booleans.py` and
   `apps/users/migrations/0019_drop_notification_frequency.py` run from
   `entrypoint.sh:8` in the new container while old containers still serve.
   Old code selects the dropped columns explicitly and will 500 until the old
   revision drains. Either accept the blip in writing or defer both drops to a
   follow-up deploy. Both openspec task lists flag this and both are unticked.

3. **CI does not run the frontend tests this branch adds.**
   `.github/workflows/ci.yml` runs lint + build only; 89 new vitest tests and
   two Playwright specs never execute on a PR. One-line fix (`- run: make test`).

4. **CI does not enforce OpenAPI regeneration.** The repo's most-forgotten step
   is checked only by convention. One-line fix
   (`make extract-openapi && git diff --exit-code`).

5. **Upload size limit is client-declared and unenforced.**
   `services/images/django_impl/handler.py:132-133` validates the browser's
   claimed `file_size`; the presigned PUT carries no `content-length-range`
   (`services/storage.py:48-58`) and `complete_upload` never checks the stored
   object. Pre-existing, but the branch replaces a 10-image-per-project ceiling
   with 30-per-article × uncapped articles, so the abuse ceiling goes from
   bounded to unbounded.

### Minor

6. **Committed `node_modules` artifact.**
   `node_modules/.vite/vitest/da39a3ee5e6b4b0d3255bfef95601890afd80709/results.json`,
   added in `41b79ccf`. Root `.gitignore` has no `node_modules` entry — the only
   rule is the directory-anchored `/node_modules` in `src/web-ui/.gitignore:4`.
   The file records two test files as failing; both pass. Delete it, add
   `node_modules/` to the root ignore.

7. **Three scratch review docs at the repo root.** `REVIEW.md`,
   `FRONT_END_REVIEW.md`, `FOLLOW_UPS.md` (820 lines total), joining the
   existing `QUESTIONS.md` and `docs.md`. `REVIEW.md`'s status table names jj
   change IDs — session state, not documentation — and is already stale in two
   places (finding 12 listed Open though the cap shipped in `99d24cf2`; test
   count 126 vs actual 153). Decide before merge; `FOLLOW_UPS.md`'s seven open
   items need a durable home if the files go.

8. **242 new transitive packages for one markdown editor.** All MIT, none
   carrying an advisory, but the tree now contains an unused CRDT runtime
   (`yjs`/`lib0`), 21 CodeMirror language packs, the MDX syntax extensions, and
   a second markdown pipeline alongside the existing `react-markdown`/`remark`
   stack. `markdown-parity.test.tsx` is the right mitigation for the last of
   these — see finding 3, since CI does not run it.

9. **Article deletion orphans S3 objects.**
   `services/articles/django_impl/handler.py:169-172` does a plain
   `Article.objects.filter(pk=...).delete()`. `ProjectImage.article` is
   `CASCADE` (`apps/projects/migrations/0045_...`) and `ImageVariant.image` is
   `CASCADE` (`apps/projects/models.py:313-317`), so the rows vanish, but
   `HANDLERS.images.delete_image` — the only thing that removes the originals
   and variants from storage — is never called, and there is no `post_delete`
   receiver for `ProjectImage` (`apps/projects/signals.py` has one, for
   `ProjectContributor`). Same shape as project deletion, so pre-existing, but
   article deletion is a new and far more frequent operation.

10. **`make ci` and `scripts/ci/` do not exist** but are documented in
    `CLAUDE.md` and are the subject of unticked verification task
    `add-article-authoring/tasks.md:154`.

11. **`api/rate_limit.py:21-25` ignores `NUM_TRUSTED_PROXIES`.** Not touched by
    this branch and not currently forgeable at the default of 1, but it diverges
    from `project_showcase/middleware.py:22-35` and becomes a forgeable-IP bug
    the moment a second proxy is added. Follow-up ticket.

12. **`projects/0044` → `0045` column churn.** `source` is added and removed
    within the same branch; no data is at risk because both ship together.
    Already triaged as "Won't do" in `REVIEW.md` finding 10. Noted for the
    record only.
