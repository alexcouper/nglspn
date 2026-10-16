"use client";

import { useCallback, useRef, useState } from "react";
import type { Article } from "@/lib/api";
import {
  type ArticleFormFields,
  type ArticleSavePayload,
  fieldsFromArticle,
  hasUnsavedChanges,
} from "./articleDraftState";

// The editable state of the article: the form fields plus the body. No network,
// no router, and no article of its own — the caller passes the last-saved copy
// in when it wants a comparison.
export function useArticleForm() {
  const [fields, setFields] = useState<ArticleFormFields | null>(null);
  // The in-memory body is tracked separately from the fields so MDXEditor does
  // not re-key on every keystroke (it is uncontrolled internally).
  const bodyRef = useRef<string>("");

  // Adopt a freshly loaded article wholesale. Only the load path calls this;
  // a save uses `applySaved`, which must not clobber unsaved edits.
  const reset = useCallback((article: Article) => {
    bodyRef.current = article.body;
    setFields(fieldsFromArticle(article));
  }, []);

  const updateFields = useCallback((patch: Partial<ArticleFormFields>) => {
    setFields((prev) => (prev ? { ...prev, ...patch } : prev));
  }, []);

  const handleBodyChange = useCallback((markdown: string) => {
    bodyRef.current = markdown;
  }, []);

  // The live body, for callers that need it outside a render — the unmount
  // sweep reads it from a cleanup, after the last commit.
  const getBody = useCallback(() => bodyRef.current, []);

  // The only producer of an `ArticleSavePayload`: it merges the fields with the
  // live editor body, so nothing that hits the network can persist a stale one.
  const snapshot = useCallback((): ArticleSavePayload | null => {
    if (!fields) return null;
    return { ...fields, body: bodyRef.current };
  }, [fields]);

  // `auto` is resolved server-side on every save, so the response is the only
  // place the resolved listing image exists.
  const applySaved = useCallback((saved: Article) => {
    setFields((prev) =>
      prev
        ? {
            ...prev,
            listing_image_id: saved.listing_image_id,
            listing_crop: saved.listing_crop,
            listing_image_mode: saved.listing_image_mode,
          }
        : prev,
    );
  }, []);

  const isDirty = useCallback(
    (article: Article | null): boolean => {
      if (!article || !fields) return false;
      return hasUnsavedChanges(article, fields, bodyRef.current);
    },
    [fields],
  );

  return {
    fields,
    getBody,
    reset,
    updateFields,
    handleBodyChange,
    snapshot,
    applySaved,
    isDirty,
  };
}
