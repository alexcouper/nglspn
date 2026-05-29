/*
 * CodeMirror dark theme for the MDXEditor code-block surface. Designed to
 * match the read-view Prism palette in `article-markdown.css` so authors
 * see the same colours they (and readers) will see on the rendered page.
 *
 * Palette is one-dark-ish on slate-900. Token mapping uses Lezer's tag
 * system rather than language-specific tokens, so colours generalise across
 * the languages we expose in `codeBlockLanguages` (ts / js / python / bash /
 * css / html / json / md / sql).
 */

import { HighlightStyle, syntaxHighlighting } from "@codemirror/language";
import { EditorView } from "@codemirror/view";
import { tags as t } from "@lezer/highlight";

const COLOURS = {
  bg: "rgb(15 23 42)", // slate-900
  fg: "rgb(241 245 249)", // slate-100
  selection: "rgb(51 65 85)", // slate-700
  cursor: "rgb(241 245 249)",
  gutter: "rgb(15 23 42)",
  gutterFg: "rgb(100 116 139)", // slate-500
  comment: "rgb(148 163 184)", // slate-400
  punctuation: "rgb(203 213 225)", // slate-300
  literal: "rgb(248 113 113)", // red-400 — numbers, booleans, tags
  string: "rgb(134 239 172)", // green-300
  operator: "rgb(165 180 252)", // indigo-300
  keyword: "rgb(196 181 253)", // violet-300
  fnOrClass: "rgb(253 224 71)", // yellow-300
  regex: "rgb(252 165 165)", // red-300
} as const;

const editorTheme = EditorView.theme(
  {
    "&": {
      backgroundColor: COLOURS.bg,
      color: COLOURS.fg,
    },
    ".cm-content": {
      caretColor: COLOURS.cursor,
      fontFamily:
        'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
      fontSize: "0.875rem",
      lineHeight: "1.6",
      padding: "0.5rem 0",
    },
    ".cm-scroller": { fontFamily: "inherit" },
    ".cm-gutters": {
      backgroundColor: COLOURS.gutter,
      color: COLOURS.gutterFg,
      border: "none",
    },
    ".cm-activeLine": { backgroundColor: "rgba(255,255,255,0.04)" },
    ".cm-activeLineGutter": { backgroundColor: "transparent" },
    ".cm-selectionBackground, ::selection": {
      backgroundColor: COLOURS.selection,
    },
    "&.cm-focused .cm-selectionBackground": {
      backgroundColor: COLOURS.selection,
    },
    ".cm-cursor": { borderLeftColor: COLOURS.cursor },
  },
  { dark: true },
);

const highlightStyle = HighlightStyle.define([
  { tag: t.comment, color: COLOURS.comment, fontStyle: "italic" },
  { tag: t.lineComment, color: COLOURS.comment, fontStyle: "italic" },
  { tag: t.blockComment, color: COLOURS.comment, fontStyle: "italic" },
  { tag: t.docComment, color: COLOURS.comment, fontStyle: "italic" },

  { tag: t.punctuation, color: COLOURS.punctuation },
  { tag: t.bracket, color: COLOURS.punctuation },
  { tag: t.brace, color: COLOURS.punctuation },
  { tag: t.paren, color: COLOURS.punctuation },
  { tag: t.separator, color: COLOURS.punctuation },

  { tag: t.number, color: COLOURS.literal },
  { tag: t.bool, color: COLOURS.literal },
  { tag: t.tagName, color: COLOURS.literal },
  { tag: t.atom, color: COLOURS.literal },
  { tag: t.propertyName, color: COLOURS.literal },

  { tag: t.string, color: COLOURS.string },
  { tag: t.special(t.string), color: COLOURS.string },
  { tag: t.character, color: COLOURS.string },

  { tag: t.operator, color: COLOURS.operator },
  { tag: t.compareOperator, color: COLOURS.operator },
  { tag: t.logicOperator, color: COLOURS.operator },
  { tag: t.arithmeticOperator, color: COLOURS.operator },
  { tag: t.url, color: COLOURS.operator },

  { tag: t.keyword, color: COLOURS.keyword },
  { tag: t.controlKeyword, color: COLOURS.keyword },
  { tag: t.moduleKeyword, color: COLOURS.keyword },
  { tag: t.definitionKeyword, color: COLOURS.keyword },
  { tag: t.self, color: COLOURS.keyword },
  { tag: t.null, color: COLOURS.keyword },
  { tag: t.operatorKeyword, color: COLOURS.keyword },

  { tag: t.function(t.variableName), color: COLOURS.fnOrClass },
  { tag: t.function(t.propertyName), color: COLOURS.fnOrClass },
  { tag: t.className, color: COLOURS.fnOrClass },
  { tag: t.definition(t.function(t.variableName)), color: COLOURS.fnOrClass },

  { tag: t.regexp, color: COLOURS.regex },
  { tag: t.variableName, color: COLOURS.fg },
  { tag: t.attributeName, color: COLOURS.literal },
  { tag: t.heading, color: COLOURS.keyword, fontWeight: "bold" },
  { tag: t.link, color: COLOURS.operator, textDecoration: "underline" },
]);

export const articleCodeMirrorExtensions = [
  editorTheme,
  syntaxHighlighting(highlightStyle),
];
