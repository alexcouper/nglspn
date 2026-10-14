// Articles are markdown, so the word count has to ignore the syntax. The
// numbers only have to be good enough to set an expectation — "6 min read"
// is a promise about scale, not a measurement — so this errs towards
// undercounting rather than towards clever.
const WORDS_PER_MINUTE = 200;

/** Whole minutes, never zero: a one-line article still takes a moment. */
export function readingMinutes(body: string): number {
  return Math.max(1, Math.round(countWords(stripMarkup(body)) / WORDS_PER_MINUTE));
}

function stripMarkup(body: string): string {
  return (
    body
      // Code is scanned rather than read, and a long listing would otherwise
      // dominate the estimate for an article that is mostly prose.
      .replace(/```[\s\S]*?```/g, " ")
      .replace(/`[^`]*`/g, " ")
      // Gallery directives carry urls and alt text, not prose.
      .replace(/^:::.*$/gm, " ")
      .replace(/!\[[^\]]*\]\([^)]*\)/g, " ")
      // A link reads as its text; the url is never read aloud.
      .replace(/\[([^\]]*)\]\([^)]*\)/g, "$1")
      .replace(/<[^>]+>/g, " ")
  );
}

function countWords(text: string): number {
  // A token counts only if it contains something readable, which drops the
  // `##`, `---` and `>` that survive stripMarkup.
  return text.split(/\s+/).filter((token) => /[\p{L}\p{N}]/u.test(token)).length;
}
