# 20. `@mdxeditor/editor`'s transitive weight

**Finding:** Minor (`00-SUMMARY.md` §Minor, detail `05-crosscutting-review.md:346–380`) — one direct dependency drags in an unused CRDT runtime, 21 CodeMirror language packs and a second markdown pipeline, invisible from a four-line `package.json` diff.
**Alex:** "what do you suggest?"
**Type:** answer, with one small fix proposal
**Effort:** S — the dependency needs nothing. The guard is a ~60-line script plus a `make` target.

---

## Short answer

Nothing about the dependency. It is properly code-split, none of it is on any
read path, and `yjs` never reaches the browser at all. The review's headline
number is also slightly wrong.

The one thing worth doing is a per-route client-JS budget, because the weight
that *does* matter on this branch is not the editor — it is 272 kB gzipped of
Prism grammars on the article **read** page (document 13), and a dependency-count
check would not have caught that either.

---

## What is actually happening

### The numbers, re-measured

`package-lock.json`, base `d2463b33` → head `7a20fb38`:

| | Base | Head |
|---|---:|---:|
| `packages` entries | 768 | 954 |

**+186 added, 0 removed.** On (path, version) pairs it is +187 / −1 — a single
version bump. The review's "gains 242 packages and removes 56" does not hold;
nothing was removed.

Where the 186 go:

| | Packages | New on this branch |
|---|---:|---:|
| `@mdxeditor/editor@4.0.1` transitive closure | 239 | 162 |
| `rehype-prism-plus@2.0.2` closure | 43 | 15 |
| `rehype-raw@7.0.0` closure | 35 | 10 |
| `rehype-sanitize@6.0.0` closure | 6 | 1 |

The "242" in the review is close to the editor's *closure* size (239, of which
77 were already installed), not to what the lock file added. Either number is
defensible; conflating them is not.

Installed tree: 524 package directories under `node_modules`;
`npm ls --omit=dev --all --parseable` → 417 nodes, `npm ls --all` → 837.

The specific items named all check out:

- **21** `@codemirror/lang-*` packs plus `@codemirror/language` and
  `@codemirror/language-data`, and 17 `@lezer/*` grammars.
- `yjs@13.6.31` (2.5 MB on disk) and `lib0@0.2.117` (4.9 MB on disk) — but they
  arrive via `@lexical/yjs`, which `@lexical/react` depends on. Not a direct
  MDXEditor dependency, and nothing in this repo imports it.
- `prismjs@1.30.0` via `@lexical/code` — a *third* Prism, alongside
  `refractor@5.0.0` under `rehype-prism-plus`.
- MDXEditor's own `mdast-util-*` / `micromark-extension-*` stack, i.e. the
  second markdown pipeline. `markdown-parity.test.tsx` exists precisely because
  of it.

### (a) Does any of it reach the client bundle?

Measured from the committed production build in `src/web-ui/.next` (`BUILD_ID
MRRsbxqEnbn36bmxI2pnj`). No build was run.

`/projects/[slug]/articles/edit/[articleId]`, eager client JS — the chunks the
route's `page_client-reference-manifest.js` names:

| | |
|---|---:|
| Chunks | 7 |
| Raw | 107,992 B |
| gzip -9 | ~32 kB |

The editor is **not** in that. It arrives via the route's
`react-loadable-manifest.json`:

| Chunk | Raw | gzip -9 | Contents |
|---|---:|---:|---|
| `fc690ba8452897fe.js` | 684,138 | 212,187 | lexical + codemirror + mdxeditor |
| `50f014a5eb2b747b.js` | 314,426 | 100,571 | codemirror |
| `f3f58be6abdf238a.js` | 64,232 | 17,359 | |
| `6e1a11e98fca3d84.js` | 36,049 | 12,376 | |
| `0648d5496d8ae5fe.js` | 30,987 | 9,954 | |
| `063294d249d1a66d.js` | 13,294 | 2,944 | lazy-loader stub |
| **JS total** | **1,143,126** | **355,391** | |
| CSS (`4f57170e6c14ac0c.css` + `35eb7c41c317b8c8.css`) | 47,994 | | Radix colours + article markdown |

**`yjs` is not in there.** It is in `static/chunks/48daf08bc604476f.js`
(71,199 B / 25,123 gz), reachable only through `063294d249d1a66d.js`, whose
references take the form

```js
s.v(a => Promise.all(["static/chunks/93f176f2feb4ad3e.js","static/chunks/48daf08bc604476f.js"].map(a => s.l(a))).then(() => a(54976)))
```

— a runtime lazy load, fetched only if that module id is requested.
`ArticleEditor.tsx:66–128` registers no collaboration plugin, so it never is.

The 21 CodeMirror language packs sit behind the same stub — that is
`@codemirror/language-data`'s on-demand loader (e.g. `0d52f74e3343fff4.js`,
87,934 B). They are emitted, not shipped.

### (b) Is it code-split away from the read path?

Yes, already, and deliberately:

```tsx
// ArticleAuthoringPage.tsx:16–19
const ArticleEditor = dynamic(
  () => import("./ArticleEditor").then((m) => m.ArticleEditor),
  { ssr: false, loading: () => <div className="skeleton h-[60vh] w-full" /> },
);
```

For scale, client JS per route in this build:

| Route | Raw | gzip -9 |
|---|---:|---:|
| `articles/[articleSlug]` (read) | 1,017,818 | ~340 kB |
| `projects/[slug]` | 249,978 | ~75 kB |
| `articles/edit/[articleId]` eager | 107,992 | ~32 kB |
| `articles/edit/[articleId]` editor, on demand | 1,143,126 | ~355 kB |

So the editor costs a contributor ~355 kB gzipped, once, at the moment they
deliberately open an editor, behind a skeleton. That is unremarkable for a
WYSIWYG surface. Meanwhile the *read* page — public, the most-visited article
route — is 340 kB gzipped, 272 kB of which is Prism grammar tables. The
dependency the review flagged is the well-behaved one.

### (c) What guard is worth adding

The honest observation: neither a package count nor a `package.json` diff would
have surfaced the Prism problem, because it came from a 3-line dependency
(`rehype-prism-plus`) whose weight is entirely in *which entry point you
import*. A dependency-count check optimises for the thing that turned out to be
fine.

What would have caught it is a size budget on the built output.

## Proposed change

Add `src/web-ui/scripts/check-bundle-budgets.mjs`, run from a new `extra-tests`
target — the same seam Alex asked for in I10, so both land together:

```make
# src/web-ui/Makefile
extra-tests:
	node scripts/check-bundle-budgets.mjs
```

```make
# src/django-backend/Makefile — no-op for now
extra-tests:
	@echo "no extra tests for django-backend"
```

and in `.github/workflows/ci.yml`, after `make build-app`:

```yaml
      - run: make extra-tests
```

The script reads what is already on disk after `make build-app` — no bundle
analyser dependency:

- for each `.next/server/app/**/page_client-reference-manifest.js`, collect
  `static/chunks/*.js` and sum `gzipSync(file, {level: 9}).length`;
- add the sibling `page/react-loadable-manifest.json` chunks as a separate
  `<route> (lazy)` entry;
- compare against a committed `bundle-budgets.json`;
- fail on any route over budget, and print a table so the number is visible in
  the log whether or not it fails.

Starting budgets, from the figures above with ~10% headroom:

```json
{
  "projects/[slug]/articles/[articleSlug]": 380000,
  "projects/[slug]/articles/edit/[articleId]": 40000,
  "projects/[slug]/articles/edit/[articleId] (lazy)": 400000,
  "projects/[slug]": 85000,
  "*": 200000
}
```

The `"*"` default is what makes it a guard rather than a snapshot: a new route
that ships 200 kB gzipped fails without anyone having predicted it. When
document 13 lands, drop the article-read budget to ~160,000 and the regression
is locked in.

### What I would not add

`npm ls --omit=dev --depth=0` diffing in CI. It only sees direct dependencies —
the four-line `package.json` diff is exactly what it would have printed, and it
would have said nothing useful. `npm ls --omit=dev --all --parseable | wc -l`
committed and diffed would have flagged 417 vs 231, but a package count does not
distinguish 162 lazily-loaded packages from one 272 kB eager chunk, so it
generates noise and trains people to bump the number. Skip it.

`npm audit` in CI is separately reasonable — the review confirmed no advisories
today — but it answers a different question and belongs in its own decision.

## Tests

The script is the test. Add one unit test for its parser
(`scripts/check-bundle-budgets.test.mjs`) covering: a manifest with no chunks, a
route over budget, a route matched only by `"*"`, and a chunk listed in two
routes counted once per route. That last case matters — shared chunks are
double-counted across routes by design, since each route does download them.

Verify by hand once: run `make build-app && make extra-tests` and check the
printed article-read figure is ~340 kB, matching the table above.

## Risks and what this does not cover

- Budgets rot. Someone will bump a number instead of investigating. The mitigation
  is that the bump appears as a line in a reviewed diff, which is more than
  exists today.
- The script depends on Next's internal manifest layout
  (`page_client-reference-manifest.js`, `react-loadable-manifest.json`). A Next
  major could move them. Fail loudly if a manifest is missing rather than
  reporting zero — a silent pass is worse than no check.
- gzip -9 of individual chunks is not what the CDN serves (brotli, and HTTP/2
  compresses across the stream). It is a stable *relative* measure, not a
  prediction of bytes on the wire. Do not quote these figures as user-facing
  performance numbers.
- Nothing here reduces `node_modules` size, install time or supply-share
  surface. 162 new packages remain 162 new packages to trust and to `npm ci`.
  If that is the actual worry, it is a different conversation — and the answer
  is not a CI check, it is a decision about whether a WYSIWYG markdown editor is
  worth its supply chain. On this branch it is: the product needs an editor,
  the alternative is building one, and MDXEditor is doing a real job behind a
  lazy boundary.
