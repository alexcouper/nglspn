# 13. Prism ships 333 grammars to read an article

**Finding:** Minor (`00-SUMMARY.md` §Minor, detail `04-frontend-review.md:11–25`) — `ArticleRenderContent.tsx` is `"use client"` and imports `rehype-prism-plus`'s default export, which is built on `refractor/all`.
**Alex:** "What do you suggest?"
**Type:** fix proposal
**Effort:** S for the recommended option — one import swap, one new 40-line module, one shared language list, one test. M if you also want the render moved server-side.

## What is actually happening

### The import pulls in two grammar sets, not one

`node_modules/rehype-prism-plus/package.json` declares four entry points:

| Export | Registers |
|---|---|
| `.` (default) | `refractor` **and** `refractor/all` |
| `./common` | `refractor` only (36 grammars) |
| `./all` | `refractor/all` only (297 grammars) |
| `./generator` | nothing — takes a refractor instance you build |

The `.` entry is a barrel: `dist/index.es.js` opens with

```js
import{refractor as i}from"refractor";import{refractor as o}from"refractor/all";
```

because `index.d.ts` re-exports `rehypePrismGenerator`, `rehypePrismCommon` *and* the default `all` plugin. So
`src/web-ui/src/app/projects/[slug]/articles/[articleSlug]/ArticleRenderContent.tsx:7` costs
297 + 36 = **333 grammar registrations**, not 297.

### Measured, from `node_modules`

| Set | Files | Bytes of source |
|---|---:|---:|
| `refractor/lang/*.js` (all) | 297 | 935,047 |
| refractor common (`lib/common.js`) | 36 | 152,757 |
| The 12 the editor can emit | 12 | 58,172 |

### Measured, from the committed build output

`src/web-ui/.next` holds a production Turbopack build of this branch (`BUILD_ID
MRRsbxqEnbn36bmxI2pnj`, 6 Aug 18:09). No build was run for this document.

`static/chunks/8cf557b2c8ae44cd.js` — **791,119 bytes raw, 272,367 bytes gzip -9**.
It contains 297 `displayName` and 297 `aliases` assignments; `abap`, `wolfram`,
`brainfuck`, `cobol`, `fortran`, `zig`, `solidity` and `smalltalk` are all in
there. Grammar tables occupy roughly bytes 1,345–83,600 (the common block, ending
in the `clike`/`c`/`cpp`/`arduino` displayName run) and 90,243–578,000 (the `all`
block, `abap` → `wgsl`) — about **570 KB of the 776 KB script body, 73%**.

It is referenced from exactly one manifest:
`server/app/projects/[slug]/articles/[articleSlug]/page_client-reference-manifest.js`.

Client JS per route, summed from each route's client-reference manifest:

| Route | Chunks | Raw | gzip -9 |
|---|---:|---:|---:|
| `projects/[slug]/articles/[articleSlug]` | 10 | 1,017,818 | ~340 kB |
| `projects/[slug]` | 9 | 249,978 | ~75 kB |
| `projects/[slug]/articles/edit/[articleId]` (eager) | 7 | 107,992 | ~32 kB |

The article **read** page ships four times the client JS of the project page, and
78% of it is the Prism chunk. Reading an article is the heaviest thing this app
does in the browser — heavier than opening the editor (the editor is lazy; see
document 20).

And because the component is `"use client"`, react-markdown + refractor run
**twice** on a cold load: once during SSR to produce the HTML, once again during
hydration.

### What the editor can actually produce

`ArticleEditor.tsx:80–93` declares the code-block languages inline:

```
"" ts js tsx jsx python bash css html json md sql
```

11 real languages. Verified against a hand-registered refractor core with the 12
grammars `markup css clike javascript jsx typescript tsx python bash json markdown sql`:
all 11 keys resolve (`ts`/`js`/`md`/`html` via aliases) and highlight.

Note `jsx` and `tsx` are **not** in refractor's common set
(`grep -c jsx node_modules/refractor/lib/common.js` → 0).

## Proposed change

### Option 1 — `rehype-prism-plus/common` (one line)

```diff
-import rehypePrismPlus from "rehype-prism-plus";
+import rehypePrismPlus from "rehype-prism-plus/common";
```

Drops the `refractor/all` block only; the 36-grammar common block stays. Chunk
goes from ~791 KB to roughly 300 KB raw.

Cost: TSX and JSX blocks stop being highlighted. With `ignoreMissing: true`
(line 115) that failure is silent — the author picks "TSX" in the toolbar, the
editor colours it, the published page does not. Worse than the bug it fixes.

### Option 2 — hand-registered subset matching the editor (recommended)

Two new files, plus edits to two existing ones.

**New** `src/app/projects/[slug]/articles/code-languages.ts` — the single
declaration of what a code block may be. No refractor import, so it stays out of
the editor chunk:

```ts
// The languages a code block may be written in. The editor's dropdown and the
// read page's syntax highlighter are both derived from this map, so the two
// cannot drift: a language the author can pick is a language the reader sees
// highlighted.
//
// The keys are the fence info strings MDXEditor writes (```ts, ```md …) and
// must be refractor-resolvable names or aliases; article-code-highlight.ts
// registers the grammars, and code-languages.test.ts asserts the two agree.
export const ARTICLE_CODE_LANGUAGES: Record<string, string> = {
  "": "Plain text",
  ts: "TypeScript",
  js: "JavaScript",
  tsx: "TSX",
  jsx: "JSX",
  python: "Python",
  bash: "Shell",
  css: "CSS",
  html: "HTML",
  json: "JSON",
  md: "Markdown",
  sql: "SQL",
};
```

**New** `src/app/projects/[slug]/articles/[articleSlug]/article-code-highlight.ts`:

```ts
// rehype-prism-plus's default export registers refractor/all AND refractor's
// common set — 333 grammars, ~570 KB of minified regex tables, in a chunk the
// browser fetches to read one article. The generator entry takes a refractor
// instance instead, so we register only what code-languages.ts lets an author
// write.
//
// Registration order matters: refractor does not resolve dependencies. clike
// underpins javascript, javascript underpins typescript and jsx, jsx and
// typescript underpin tsx, markup underpins markdown.
import { refractor } from "refractor/core";
import markup from "refractor/lang/markup";
import css from "refractor/lang/css";
import clike from "refractor/lang/clike";
import javascript from "refractor/lang/javascript";
import jsx from "refractor/lang/jsx";
import typescript from "refractor/lang/typescript";
import tsx from "refractor/lang/tsx";
import python from "refractor/lang/python";
import bash from "refractor/lang/bash";
import json from "refractor/lang/json";
import markdown from "refractor/lang/markdown";
import sql from "refractor/lang/sql";
// The `/generator` entry, not the barrel: the barrel is what imports
// refractor/all.
import rehypePrismGenerator from "rehype-prism-plus/generator";

for (const syntax of [
  markup, css, clike, javascript, jsx, typescript, tsx,
  python, bash, json, markdown, sql,
]) {
  refractor.register(syntax);
}

export const rehypeArticlePrism = rehypePrismGenerator(refractor);
export { refractor as articleRefractor };
```

**Edit** `ArticleRenderContent.tsx`:

```diff
-import rehypePrismPlus from "rehype-prism-plus";
+import { rehypeArticlePrism } from "./article-code-highlight";
@@
-              [rehypePrismPlus, { ignoreMissing: true }],
+              [rehypeArticlePrism, { ignoreMissing: true }],
```

**Edit** `ArticleEditor.tsx:79–95`:

```diff
+import { ARTICLE_CODE_LANGUAGES } from "./code-languages";
@@
           codeMirrorPlugin({
-            codeBlockLanguages: {
-              "": "Plain text",
-              ts: "TypeScript",
-              js: "JavaScript",
-              tsx: "TSX",
-              jsx: "JSX",
-              python: "Python",
-              bash: "Shell",
-              css: "CSS",
-              html: "HTML",
-              json: "JSON",
-              md: "Markdown",
-              sql: "SQL",
-            },
+            codeBlockLanguages: ARTICLE_CODE_LANGUAGES,
             codeMirrorExtensions: articleCodeMirrorExtensions,
           }),
```

Expected result: 58,172 bytes of grammar source instead of 1,087,804. The
observed minify ratio for these files in this build is ~0.52 (935 KB → ~488 KB,
153 KB → ~82 KB), so the grammar payload drops from ~570 KB minified to ~31 KB.
Chunk `8cf557b2c8ae44cd.js` should land around 250 KB raw / ~85 kB gz —
roughly **185 kB gzipped off every article page load**.

### Option 3 — render the markdown in the server component

`ArticleRenderContent` cannot stop being `"use client"`. It calls `useAuth`
(:24), `useNotifications` (:28) and `useEffect` (:37) to POST the read receipt.
That is real client state.

But the markdown render does not have to live inside it. `page.tsx:55` is a
server component, and this repo already renders react-markdown in server
components — `src/app/about/why/page.tsx:1`, `src/app/about/prizes/page.tsx:1`,
`src/app/privacy/page.tsx:2`. Render there and pass the tree down:

```diff
   return (
     <main className="min-h-screen bg-muted pt-14">
-      <ArticleRenderContent project={project} article={article} />
+      <ArticleRenderContent project={project} article={article}>
+        <ReactMarkdown …>{article.body}</ReactMarkdown>
+      </ArticleRenderContent>
     </main>
   );
```

The `components` overrides stay inline arrow functions — they run during the
server render and produce plain host elements, which serialise across the RSC
boundary fine.

This removes refractor, react-markdown, rehype-raw, rehype-sanitize and
remark-gfm from the client bundle entirely — the whole 791 KB chunk plus its
rehype/remark tail, ~340 kB gz down to ~70 kB.

The cost is not zero and is worth stating plainly: today the RSC payload carries
`article.body` as a markdown string, and the JS chunk that renders it is
immutably cached and shared across every article. Option 3 swaps that for a
serialised element tree per article — typically 2–4x the markdown's size, worse
for code-heavy articles where every token becomes an element, and not shared
between articles. A reader who opens ten articles pays ten inflated payloads
instead of one cached chunk. Option 2 keeps the caching and gets most of the
win.

## Tests

Add to `src/app/projects/[slug]/articles/` a `code-languages.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { ARTICLE_CODE_LANGUAGES } from "./code-languages";
import { articleRefractor } from "./[articleSlug]/article-code-highlight";

describe("code block languages", () => {
  it("registers a grammar for every language the editor offers", () => {
    const unregistered = Object.keys(ARTICLE_CODE_LANGUAGES)
      .filter((key) => key !== "")
      .filter((key) => !articleRefractor.registered(key));
    expect(unregistered).toEqual([]);
  });
});
```

That is the drift guard: adding "Go" to the dropdown without registering the
grammar fails, instead of silently producing unhighlighted code.

`markdown-parity.test.tsx` imports `rehypePrismPlus` at line 4 and uses it at
line 36 — switch it to `rehypeArticlePrism` so the test exercises the pipeline
the page actually runs. Add one case there asserting a ```` ```tsx ```` fence
produces `<span class="token keyword">`, which is what Option 1 would have
regressed.

Neither test runs on CI today (finding I9).

## Risks and what this does not cover

- A code fence whose info string is outside `ARTICLE_CODE_LANGUAGES` (pasted
  markdown, an import) renders unhighlighted rather than raising —
  `ignoreMissing: true` at `ArticleRenderContent.tsx:115` already swallows it.
  That is the current behaviour for the 297th grammar too; the set of
  unsupported languages just gets larger. If you care, drop `ignoreMissing` and
  let the parity test catch it.
- The size figures for Option 2 are projections from a measured minify ratio,
  not from a build. Verify with a `make build-app` and re-measure
  `8cf557b2c8ae44cd.js` before claiming the number anywhere.
- `refractor/core` and `refractor/lang/*` are exported (`"./*": "./lang/*.js"`),
  so the deep imports are supported API, not reaching inside the package.
- Sanitisation is unaffected in isolation, but the two findings interact: the
  smaller grammar set also shrinks the token-class allow-list document 14
  proposes. Do this one first.
