"use client";

import { useCallback, useState } from "react";
import { api } from "@/lib/api";
import type { Article } from "@/lib/api";
import { describeApiError } from "@/lib/api/errors";
import type { ArticleSavePayload } from "./articleDraftState";

interface Options {
  projectRef: string;
  article: Article | null;
  // The server's copy after a successful write, for whoever holds the article
  // and the form.
  onPersisted: (updated: Article) => void;
  // Already author-facing: this unit knows which write failed, so it picks the
  // fallback sentence. The composite only decides where it shows.
  onError: (message: string) => void;
}

// Save, publish and delete. Reports outcomes; it does not navigate — what a
// successful publish or delete means for the URL is the page's decision.
export function useArticleMutations({
  projectRef,
  article,
  onPersisted,
  onError,
}: Options) {
  const [successMessage, setSuccessMessage] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const persistDraft = useCallback(
    async (payload: ArticleSavePayload): Promise<Article | null> => {
      if (!article) return null;
      try {
        const updated = await api.articles.update(projectRef, article.id, {
          title: payload.title,
          body: payload.body,
          channel_id: payload.channel_id,
          summary: payload.summary,
          listing_image_id: payload.listing_image_id,
          listing_crop: payload.listing_crop,
          listing_image_mode: payload.listing_image_mode,
        });
        onPersisted(updated);
        return updated;
      } catch (err) {
        onError(describeApiError(err, "Couldn't save this article."));
        return null;
      }
    },
    [article, projectRef, onPersisted, onError],
  );

  const save = useCallback(
    async (payload: ArticleSavePayload): Promise<Article | null> => {
      onError("");
      setSuccessMessage("");
      setIsSaving(true);
      const saved = await persistDraft(payload);
      setIsSaving(false);
      if (saved) {
        setSuccessMessage(
          saved.state === "published" ? "Saved" : "Draft saved",
        );
        setTimeout(() => setSuccessMessage(""), 2500);
      }
      return saved;
    },
    [persistDraft, onError],
  );

  // Resolves to the saved article once it is published, or null if either the
  // save or the publish failed. `isPublishing` deliberately stays set on
  // success: the page navigates away, and dropping it first would flash the
  // button back to "Publish".
  const publish = useCallback(
    async (payload: ArticleSavePayload): Promise<Article | null> => {
      onError("");
      setIsPublishing(true);
      const saved = await persistDraft(payload);
      if (!saved) {
        setIsPublishing(false);
        return null;
      }
      try {
        await api.articles.publish(projectRef, saved.id, {
          published_at: null,
        });
        return saved;
      } catch (err) {
        // The old 422-only branch was a special case of this: describeApiError
        // passes the backend's `detail` through for any 4xx, which is where the
        // "not ready to publish" reasons come from.
        onError(describeApiError(err, "Article is not ready to publish."));
        setIsPublishing(false);
        return null;
      }
    },
    [persistDraft, projectRef, onError],
  );

  const remove = useCallback(async (): Promise<boolean> => {
    if (!article) return false;
    setIsDeleting(true);
    try {
      await api.articles.delete(projectRef, article.id);
      return true;
    } catch (err) {
      onError(describeApiError(err, "Couldn't delete this article."));
      setIsDeleting(false);
      return false;
    }
  }, [article, projectRef, onError]);

  return {
    save,
    publish,
    remove,
    isSaving,
    isPublishing,
    isDeleting,
    successMessage,
  };
}
