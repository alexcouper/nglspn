const WORDS_PER_MINUTE = 200;

/** Whole minutes, never zero. */
export function readingMinutes(body: string): number {
  return Math.max(1, Math.round(countWords(stripMarkup(body)) / WORDS_PER_MINUTE));
}

// Code, gallery directives, images and tags are not prose; a link reads as its
// text.
function stripMarkup(body: string): string {
  return body
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/`[^`]*`/g, " ")
    .replace(/^:::.*$/gm, " ")
    .replace(/!\[[^\]]*\]\([^)]*\)/g, " ")
    .replace(/\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/<[^>]+>/g, " ");
}

function countWords(text: string): number {
  return text.split(/\s+/).filter((token) => /[\p{L}\p{N}]/u.test(token)).length;
}
