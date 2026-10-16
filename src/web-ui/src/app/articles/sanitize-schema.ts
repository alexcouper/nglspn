import { defaultSchema } from "rehype-sanitize";
import type { Schema } from "hast-util-sanitize";
import { GALLERY_CLASS } from "./gallery-mdast";

// rehype-prism-plus writes `language-<name>` onto <pre> and <code> from the
// fence info string, and refractor uses the same shape as a token alias
// (`<span class="token language-css">`).
const LANGUAGE_CLASS = /^language-[\w+#-]+$/;

// Structural classes rehype-prism-plus adds itself (dist/generator.es.js):
// `code-highlight` on the <code>, the rest on the per-line <span>s.
const PRISM_CODE_CLASS = "code-highlight";
const PRISM_LINE_CLASSES = [
  "code-line",
  "line-number",
  "highlight-line",
  "deleted",
  "inserted",
] as const;

// refractor emits `token` plus the token type plus any grammar aliases
// (refractor/lib/core.js: `classes: ['token', value.type]`). This list is the
// closure of token names and aliases over the grammars behind the code-block
// languages ArticleEditor.tsx offers, plus the few extra names
// `article-markdown.css` colours (`char`, `symbol`, `deleted`, `inserted`) so
// a pasted fence in some other language still comes out coloured. Token types
// unique to those other grammars are dropped — no rule styles them, so that is
// invisible.
//
// markdown-parity.test.tsx renders a fence in every editor language with and
// without sanitisation and fails if any emitted class goes missing, so a
// refractor upgrade cannot silently break colouring.
//
// It has to be an enumeration. A shape-based pattern such as
// /^[a-z][a-z0-9-]*$/ would also match `fixed`, `inset-0`, `z-50` and
// `bg-white`, which is exactly what must not get through.
const PRISM_TOKEN_CLASSES = [
  "token",
  "alternation", "anchor", "annotation", "arrow", "assign-left", "at",
  "atrule", "attr-equals", "attr-name", "attr-value", "attribute",
  "backreference", "bash", "blockquote", "bold", "boolean", "builtin",
  "case-sensitivity", "cdata", "char", "char-class", "char-class-negation",
  "char-class-punctuation", "char-set", "class", "class-name", "code",
  "code-block", "code-language", "code-snippet", "color", "combinator",
  "comment", "console", "constant", "content", "control-flow",
  "conversion-option", "css", "datetime", "decorator", "directive",
  "doc-comment", "doctype", "doctype-tag", "dom", "embedded-code", "entity",
  "environment", "escape", "example", "exports", "file-descriptor",
  "for-or-select", "format-spec", "front-matter", "front-matter-block",
  "function", "function-name", "function-variable", "generic",
  "generic-function", "graphql", "group", "group-name", "hashbang",
  "hexcode", "hr", "html", "id", "identifier", "important", "imports",
  "included-cdata", "internal-subset", "interpolation",
  "interpolation-punctuation", "italic", "javascript", "key", "keyword",
  "known-class-name", "list", "literal-property", "markdown",
  "maybe-class-name", "method", "method-variable", "module", "n-th", "name",
  "named-entity", "namespace", "nil", "null", "number", "operator",
  "optional-parameter", "parameter", "prolog", "property", "property-access",
  "pseudo-class", "pseudo-element", "punctuation", "quantifier", "range",
  "range-punctuation", "regex", "regex-delimiter", "regex-flags",
  "regex-source", "rule", "scalar", "script", "script-punctuation",
  "selector", "selector-function-argument", "shebang", "special-attr",
  "special-escape", "spread", "sql", "strike", "string",
  "string-interpolation", "string-property", "style", "svg", "symbol",
  "table", "table-data", "table-data-rows", "table-header",
  "table-header-row", "table-line", "tag", "template-punctuation",
  "template-string", "title", "triple-quoted-string", "unit", "url",
  "url-reference", "value", "variable", "yaml",
] as const;

// Allowlist for raw HTML inside article bodies. Articles can be authored by
// any `full_edit` contributor, so the surface is wider than admin-authored
// broadcasts — keep this conservative.
//
// What we add on top of defaultSchema (GitHub-style):
//   - `figure` / `figcaption` in tagNames so authors can caption images
//   - `align` attribute on `div` (the legacy centering pattern used in
//     broadcast emails — broadly browser-supported despite being deprecated)
//   - `width` / `height` on `img` so MDXEditor's emitted `<img width="..."
//     height="..." />` round-trips
//   - the syntax-highlighter's own classes on `pre`, `code` and `span`, so
//     rehype-prism-plus output (e.g. `<span class="token keyword">`) and the
//     `language-xxx` class on fenced blocks survive sanitisation
//
// We deliberately do NOT allow the `style` attribute. Style values are
// effectively unbounded text and would let authors slip in `background:
// url(javascript:…)` etc. If a future construct needs CSS-driven sizing,
// fold it into the `.markdown-article` styles rather than loosening this
// allowlist.
export const articleSanitizeSchema: Schema = {
  ...defaultSchema,
  tagNames: [
    ...(defaultSchema.tagNames ?? []),
    "figure",
    "figcaption",
  ],
  attributes: {
    ...(defaultSchema.attributes ?? {}),
    // `gallery` is the marker `remark-gallery` puts on the wrapper it builds
    // from a `:::gallery` block, so `ArticleRenderContent` can swap in the
    // carousel component. Only that one literal name gets through, and the
    // rules behind it live in `article-markdown.css` — an author writing the
    // class by hand gets the same wrapper, not a lever on page layout.
    div: [
      ...(defaultSchema.attributes?.div ?? []),
      "align",
      ["className", GALLERY_CLASS],
    ],
    img: [
      ...(defaultSchema.attributes?.img ?? []),
      "width",
      "height",
    ],
    // Not a bare "className": hast-util-sanitize reads that as "any value",
    // and Tailwind's utilities are global on every page, so a `full_edit`
    // contributor could write <span class="fixed inset-0 z-50 bg-white"> and
    // blank the viewport — nav included — for anyone opening the article.
    // Only the classes the highlighter emits get through. Each class in the
    // attribute is checked independently (hast-util-sanitize's
    // `propertyValueMany`), so the rest of the list is dropped, not the
    // element.
    pre: [["className", LANGUAGE_CLASS]],
    code: [["className", LANGUAGE_CLASS, PRISM_CODE_CLASS]],
    span: [
      [
        "className",
        LANGUAGE_CLASS,
        ...PRISM_LINE_CLASSES,
        ...PRISM_TOKEN_CLASSES,
      ],
    ],
  },
};

// Exposed so a test can assert the list never grows a class that positions or
// sizes anything.
export const articleAllowedSpanClasses: ReadonlySet<string> = new Set([
  ...PRISM_LINE_CLASSES,
  ...PRISM_TOKEN_CLASSES,
]);

// Same, for the one class an author can put on a block-level element.
export const articleAllowedDivClasses: ReadonlySet<string> = new Set([
  GALLERY_CLASS,
]);
