"use client";

import { type Dispatch, type SetStateAction, useCallback } from "react";
import type { Article, ProjectImage } from "@/lib/api";

// The article's own images: the selection list the listing wizard offers, and
// the image the form currently points at.
//
// The article itself is owned by `useArticleLoad`; this takes its setter rather
// than holding a second copy.
export function useArticleImages(
  article: Article | null,
  setArticle: Dispatch<SetStateAction<Article | null>>,
  listingImageId: string | null,
) {
  // The wizard can hand back an image it uploaded itself, which the loaded
  // article knows nothing about. Both `images` and `listingImage` are derived
  // from `article.images`, so without adopting it here the panel would show
  // "No image" next to "Your choice." until the next save wrote the server's
  // copy back.
  const adoptImage = useCallback(
    (image: ProjectImage) => {
      setArticle((prev) =>
        prev && !prev.images.some((existing) => existing.id === image.id)
          ? { ...prev, images: [...prev.images, image] }
          : prev,
      );
    },
    [setArticle],
  );

  return {
    // Comes off the image-article link, so it holds whatever was uploaded for
    // this article whether or not it is in the body.
    images: article?.images ?? [],
    // What the form points at, not the last-saved image: the panel must show
    // what the wizard just picked, before any save.
    listingImage:
      article?.images.find((image) => image.id === listingImageId) ??
      (listingImageId && listingImageId === article?.listing_image_id
        ? article.listing_image
        : null),
    adoptImage,
  };
}
