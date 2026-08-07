# 14. Bare `className` on `span`/`pre` — how far does it reach

**Finding:** Minor (`00-SUMMARY.md` §Minor, detail `04-frontend-review.md:209–216`) — `sanitize-schema.ts:38–40` adds a bare `"className"` to `pre`/`code`/`span`, which in `hast-util-sanitize` means any value.
**Alex:** "If a contributor did this would it alter the entire site, or just their own article?"
**Type:** answer, with a fix proposal attached
**Effort:** S — one file, ~15 lines, plus one test. Do document 13 first; it shrinks the allow-list this needs.

---

## Verdict

**The whole page on which that one article renders, site nav included — but only
that page, only for people who open that article's URL. Not the rest of the site,
not other users' articles, and nothing persists once the reader navigates away.**

It is a defacement of one URL, not a site-wide takeover, and not script
execution. It is also not theoretical: every CSS class needed is present in the
compiled stylesheet on every page.

---

## What is actually happening

### 1. The `code` entry is a no-op; only `pre` and `span` are opened

`node_modules/hast-util-sanitize/lib/schema.js` already ships

```js
code: [['className', /^language-./]],
```

and `findDefinition` (`lib/index.js`) returns the **first** entry whose name
matches the key. `sanitize-schema.ts:39` appends a bare `"className"` *after*
that, so the restricted entry still wins. `code` was never opened.

Confirmed by running the real schema through `hast-util-sanitize@5.0.2`:

| Input | Output under the current schema |
|---|---|
| `<span class="fixed inset-0 z-50 bg-white">gotcha</span>` | **unchanged** |
| `<pre class="fixed inset-0 z-50 bg-white">p</pre>` | **unchanged** |
| `<code class="fixed inset-0 language-js code-highlight">c</code>` | `<code class="language-js">c</code>` |
| `<div class="fixed inset-0">d</div>` | `<div>d</div>` |
| `<span style="position:fixed">s</span>` | `<span>s</span>` |

Two incidental facts fall out of that: `style` is correctly refused, and
`code-highlight` — which `rehype-prism-plus` puts on the `<code>` element — is
being stripped today. Harmless, because no rule in `article-markdown.css` uses
it, but it means the comment at `sanitize-schema.ts:15` is describing something
that does not happen.

`<style>`, `<link>` and `<iframe>` are not in `defaultSchema.tagNames` (53 tags,
checked). So there is no route to a persistent or cross-page stylesheet, and no
route to script.

### 2. Tailwind is global and the dangerous utilities are genuinely emitted

This is the crux, and the answer is not the comfortable one.

`src/app/globals.css:1` is `@import "tailwindcss";`, and
`src/app/layout.tsx:12` imports `globals.css` into the **root** layout. The
compiled result in this branch's build is
`.next/static/chunks/2f1c981e95e58389.css`, 75,273 bytes, present on every route.

Tailwind 4 only emits what it finds by scanning source — so the question is
whether other components already use the classes an attacker would want. They
do. Every one of these is in that stylesheet:

`.fixed` `.absolute` `.sticky` `.inset-0` `.top-0` `.left-0` `.z-50`
`.bg-white` `.w-full` `.h-full` `.block` `.inline-block` `.p-8` `.rounded-xl`
`.text-center` `.underline` `.text-red-600` `.opacity-0` `.pointer-events-none`

They exist because real components use them —
`src/components/Navigation.tsx:107` (`fixed inset-0 … z-50`),
`src/app/projects/[slug]/ProjectDetailContent.tsx:255`,
`src/app/my-projects/[id]/PublishDialog.tsx:20`,
`src/components/ImageUpload/ImageGallery.tsx:174`. The JIT is not a mitigation
here.

Only `z-10`, `z-20`, `z-30`, `z-50` are generated; there is no arbitrary
`z-[…]` anywhere in `src/`. `z-50` is enough — see below.

### 3. Nothing bounds the overlay

The article body's ancestor chain is:

```
body.antialiased.min-h-screen.flex.flex-col      (layout.tsx:64)
 └ div.flex-1.flex.flex-col                       (layout.tsx:73)
    └ main.min-h-screen.bg-muted.pt-14            (page.tsx:77)
       └ article.sm:py-8.sm:px-6                  (ArticleRenderContent.tsx:45)
          └ div.max-w-3xl.mx-auto.bg-white…       (:68)
             └ div.markdown.markdown-article.mt-8 (:104)
```

None of those sets `transform`, `filter`, `perspective`, `contain`,
`backdrop-filter` or `will-change`, so none establishes a containing block for
`position: fixed`. `article-markdown.css` carries no transform either; its only
`overflow` is `overflow-x: auto` on `.markdown-article pre` (:87), and overflow
does not clip fixed-position descendants.

`position: fixed` also blockifies the inline `<span>`, so `inset-0` gives a
full-viewport box without needing a `display` utility.

### 4. It covers the nav

`Navigation.tsx:42` is `<nav className="fixed top-0 left-0 right-0 z-50 …">`, a
direct child of `<body>`. The injected span is also positioned with `z-50` and
also participates in the root stacking context (no intervening ancestor creates
one). Equal `z-index` in the same stacking context is broken by tree order, and
the article body comes after `<nav>`. The span wins.

So `<span class="fixed inset-0 z-50 bg-white">` blanks the entire viewport
including the nav bar, and `pointer-events-none` is *not* set, so it also eats
every click. Add `bg-white` plus text and it is a convincing fake page.

### 5. It reaches nowhere else

`articleSanitizeSchema` is imported in exactly two places:
`ArticleRenderContent.tsx:11` and `markdown-parity.test.tsx:8`. Nothing else in
the app renders `article.body` as HTML. Checked each surface the review named:

| Surface | What it renders | Safe because |
|---|---|---|
| Notification bell | `group.latest_body_excerpt` at `NotificationGroupItem.tsx:49` | React text child — escaped. It is a raw markdown slice (`services/notifications/django_impl/handler.py:47`), never parsed as HTML. |
| Digest email | `body_excerpt` from `services/email/django_impl/handler.py:121` | `derive_summary()` flattens the markdown; the Django template autoescapes. |
| Article cards | `article.summary` / `summary_display` (`ArticleCard.tsx`, `ArticleCardPreview.tsx:36`) | Plain text, never the body. |
| Page metadata | `page.tsx:34` | `summary` / `summary_display`, deliberately not the body — the comment says so. |
| Editor preview | MDXEditor's own Lexical render | Separate pipeline, does not use this schema. |

### 6. Who can do it, and what they cannot do

`require_full_edit` → `user_can_edit` (`services/project/django_impl/query.py:186`)
means a `ProjectContributor` row with `full_edit=True` on that project. So: a
contributor defacing a project they already have write access to. They cannot
touch another project's articles, and the CSP (`next.config.ts`) blocks
`img-src` outside the CDN and sets `frame-ancestors 'none'`, so the fake page
cannot pull remote imagery or be framed.

What it *is* good for: a plausible full-screen "session expired, log in again"
panel on a URL you can send someone. Phishing, not XSS.

---

## Proposed change

### Option 1 — explicit allow-list plus a drift test (recommended)

Replace the three bare entries. `hast-util-sanitize` supports RegExp values in a
property definition (`lib/index.js`, `propertyValuePrimitive`: `if (allowed &&
typeof allowed === 'object' && 'flags' in allowed)`) and filters each class name
in the list independently.

The class names `rehype-prism-plus` and refractor actually emit are:

- on `<pre>`: `language-<lang>` (generator.es.js, `parent.properties.className`)
- on `<code>`: `language-<lang>`, `code-highlight`
- on line `<span>`s: `code-line`, and conditionally `line-number`,
  `highlight-line`, `deleted`, `inserted`
- on token `<span>`s: `token`, the token type, and any aliases
  (`refractor/lib/core.js:264`: `classes: ['token', value.type]`)

Enumerated from the 12 grammars document 13 registers, the token types and
aliases are 97 names, all matching `/^[a-z][a-z0-9-]*$/`:

```
annotation assign-left at atrule attr-equals attr-name attr-value bash
blockquote bold boolean builtin cdata class-name code code-block code-language
code-snippet comment constant content conversion-option css decorator doctype
doctype-tag entity environment file-descriptor for-or-select format-spec
front-matter front-matter-block function function-name function-variable
generic generic-function hashbang hr identifier important included-cdata
internal-subset interpolation interpolation-punctuation italic keyword
language-css language-javascript language-regex language-yaml list
literal-property name named-entity namespace null number operator parameter
prolog property punctuation regex regex-delimiter regex-flags regex-source rule
script script-punctuation selector selector-function-argument shebang
special-attr spread strike string string-interpolation string-property style
table table-data table-data-rows table-header table-header-row table-line tag
template-punctuation template-string title triple-quoted-string url
url-reference value variable yaml
```

Cross-checked against the compiled Tailwind stylesheet: exactly two of the 97
also exist as Tailwind utilities — `.italic` and `.table`. Neither positions or
sizes anything.

Note that a generic pattern like `/^[a-z][a-z0-9-]*$/` would **not** work:
`fixed`, `absolute`, `inset-0`, `z-50` and `bg-white` all match it. Enumeration
is the only honest option.

```diff
 export const articleSanitizeSchema: Schema = {
   ...defaultSchema,
   tagNames: [
     ...(defaultSchema.tagNames ?? []),
     "figure",
     "figcaption",
   ],
   attributes: {
     ...(defaultSchema.attributes ?? {}),
     div: [...(defaultSchema.attributes?.div ?? []), "align"],
     img: [
       ...(defaultSchema.attributes?.img ?? []),
       "width",
       "height",
     ],
-    pre: [...(defaultSchema.attributes?.pre ?? []), "className"],
-    code: [...(defaultSchema.attributes?.code ?? []), "className"],
-    span: [...(defaultSchema.attributes?.span ?? []), "className"],
+    // Not a bare "className": hast-util-sanitize reads that as "any value",
+    // and Tailwind's utilities are global on every page, so a full_edit
+    // contributor could write <span class="fixed inset-0 z-50 bg-white"> and
+    // blank the viewport, nav included, for anyone opening the article.
+    // Only the classes the highlighter emits get through.
+    pre: [["className", LANGUAGE_CLASS]],
+    code: [["className", LANGUAGE_CLASS, "code-highlight"]],
+    span: [["className", ...PRISM_STRUCTURE_CLASSES, TOKEN_CLASS]],
   },
 };
```

with, above it:

```ts
// rehype-prism-plus writes `language-<name>` onto <pre> and <code> from the
// fence info string.
const LANGUAGE_CLASS = /^language-[\w+#-]+$/;

// Structural classes rehype-prism-plus puts on the per-line spans
// (dist/generator.es.js).
const PRISM_STRUCTURE_CLASSES = [
  "code-line",
  "line-number",
  "highlight-line",
  "deleted",
  "inserted",
] as const;

// refractor emits `token` plus the token type plus any grammar aliases
// (refractor/lib/core.js: classes: ['token', value.type]). This is the closure
// of type names and aliases over the grammars registered in
// article-code-highlight.ts — code-highlight.test.ts fails if a grammar starts
// emitting something outside it, so the list cannot silently go stale.
const TOKEN_CLASS =
  /^(?:token|annotation|assign-left|at|atrule|…|yaml)$/;
```

Verified against `hast-util-sanitize@5.0.2`: the attack input reduces to
`<span class="">gotcha</span>` / `<pre class="">p</pre>`, while real Prism output

```html
<pre class="language-js"><code class="language-js code-highlight"><span class="code-line"><span class="token keyword">const</span> <span class="token class-name">X</span></span></code></pre>
```

passes through byte-identical (and now keeps `code-highlight`, which the current
schema drops).

### Option 2 — namespace the token classes

A rehype step between prism and sanitize that rewrites every emitted class to a
`tk-` prefix, then `span: [["className", /^tk-[a-z0-9-]+$/]]` and a rewrite of
the 13 selectors in `article-markdown.css:104–158`. Drift-proof by construction,
no list to maintain. Not recommended: more moving parts, a custom plugin to
maintain, and CSS churn, to avoid a list that a test already guards.

## Tests

In `markdown-parity.test.tsx`, next to the existing raw-HTML cases:

```ts
describe("article sanitisation", () => {
  it("strips layout classes a contributor could use to cover the page", () => {
    const html = renderArticle('<span class="fixed inset-0 z-50 bg-white">x</span>');
    expect(html).not.toContain("fixed");
    expect(html).not.toContain("inset-0");
    expect(html).not.toContain("z-50");
  });

  it("keeps the classes the syntax highlighter emits", () => {
    const html = renderArticle("```ts\nconst x = 1;\n```\n");
    expect(html).toContain('class="language-ts"');
    expect(html).toContain('class="code-line"');
    expect(html).toContain("token keyword");
  });
});
```

Plus the drift guard, so a grammar change cannot silently break colouring —
walk the registered grammars for token type names and aliases and assert each
is accepted by `TOKEN_CLASS`. That is the same walk used to produce the 97-name
list; ~25 lines in a test file, run once.

Neither runs on CI today (finding I9).

## Risks and what this does not cover

- The 97 names are the closure over the **12** grammars document 13 proposes. If
  you keep `refractor/all`, the closure is over 297 grammars and is far larger —
  and includes names much likelier to collide with Tailwind. Land document 13
  first, or the list is unmaintainable.
- `deleted` and `inserted` only appear for `diff` fences, which the editor
  cannot produce (`ArticleEditor.tsx:80–93` has no diff entry). Harmless to
  allow; pasted markdown can still contain a diff fence.
- This does not narrow `div`'s `align` or `img`'s `width`/`height` — both are
  bounded value spaces and neither can position anything.
- It does not address the *other* half of the surface: `rehypeRaw` still admits
  53 tag names of raw HTML. That is a deliberate product decision (authors want
  `<figure>`), and `style` is correctly refused, so the remaining reach is
  layout via structure rather than layout via CSS — much weaker.
- Nothing here is a security incident today. It needs a `full_edit` contributor
  on a project, i.e. someone the project owner already trusts with the content.
