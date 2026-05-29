import { defaultSchema } from "rehype-sanitize";
import type { Schema } from "hast-util-sanitize";

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
//   - `className` on `pre`, `code`, `span` so the rehype-prism-plus
//     syntax-highlighter output (e.g. `<span class="token keyword">`) and
//     the `language-xxx` class on fenced blocks survive sanitisation
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
    div: [...(defaultSchema.attributes?.div ?? []), "align"],
    img: [
      ...(defaultSchema.attributes?.img ?? []),
      "width",
      "height",
    ],
    pre: [...(defaultSchema.attributes?.pre ?? []), "className"],
    code: [...(defaultSchema.attributes?.code ?? []), "className"],
    span: [...(defaultSchema.attributes?.span ?? []), "className"],
  },
};
