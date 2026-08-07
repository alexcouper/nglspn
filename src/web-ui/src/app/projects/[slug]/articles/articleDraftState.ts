import type { Article, ListingImageMode } from "@/lib/api";
import type { CropRect } from "@/components/CroppedImage";

// The article authoring page's state, as pure data. No React, no network: the
// hooks below this file own the wiring, these functions own the rules.

export interface ArticleFormFields {
  title: string;
  channel_id: string;
  // The authored standfirst. "" is meaningful: it clears the override and
  // returns the card to the summary derived server-side from the body.
  summary: string;
  listing_image_id: string | null;
  // The author's 16:9 framing of the listing image. Null renders as 16:9
  // centred, which is what `auto` always gets.
  listing_crop: CropRect | null;
  listing_image_mode: ListingImageMode;
}

// The fields plus the body. The body is not part of the form: MDXEditor holds
// it uncontrolled in a ref, so it only exists as a value at snapshot time.
// Making it a separate type means a caller cannot hand a bare `ArticleFormFields`
// to something that saves — the missing `body` is a compile error rather than a
// silently stale write.
export type ArticleSavePayload = ArticleFormFields & { body: string };

export function fieldsFromArticle(article: Article): ArticleFormFields {
  return {
    title: article.title,
    channel_id: article.channel.id,
    summary: article.summary,
    listing_image_id: article.listing_image_id,
    listing_crop: article.listing_crop,
    listing_image_mode: article.listing_image_mode,
  };
}

// Whether anything would be lost by leaving now. The body is the reason this
// has to exist at all: it lives in the editor's ref until a save, so nothing
// that only reads the article can tell it has moved on from what the server
// holds.
export function hasUnsavedChanges(
  article: Article,
  fields: ArticleFormFields,
  body: string,
): boolean {
  return (
    body !== article.body ||
    fields.title !== article.title ||
    fields.summary !== article.summary ||
    fields.channel_id !== article.channel.id ||
    fields.listing_image_id !== article.listing_image_id ||
    fields.listing_image_mode !== article.listing_image_mode ||
    JSON.stringify(fields.listing_crop) !== JSON.stringify(article.listing_crop)
  );
}

export interface LeaveState {
  article: Article;
  fields: ArticleFormFields | null;
  body: string;
}

// True when nothing has been written to this draft. Used to sweep up the empty
// draft that opening /new creates when the author leaves without editing.
//
// Reads the live fields rather than the last-saved article for everything the
// author can edit without a save: typing only a headline and leaving used to
// delete the draft and the headline with it.
export function shouldDiscardDraft(state: LeaveState): boolean {
  return (
    !(state.fields?.title ?? state.article.title).trim() &&
    !state.body.trim() &&
    !(state.fields?.listing_image_id ?? state.article.listing_image_id) &&
    state.article.images.length === 0
  );
}
