"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { Article, Project, ProjectImage } from "@/lib/api";
import type { CropRect } from "@/components/CroppedImage";
import {
  type ArticleFormFields,
  shouldDiscardDraft,
} from "./articleDraftState";
import { useArticleForm } from "./useArticleForm";
import { useArticleImages } from "./useArticleImages";
import { useArticleLoad } from "./useArticleLoad";
import { useArticleMutations } from "./useArticleMutations";
import { useLeaveGuard } from "./useLeaveGuard";

interface Options {
  project: Project;
  // Present → editing an existing article. Absent → the /new route, which
  // creates a draft immediately (see `useArticleLoad`) rather than waiting for
  // a save.
  articleId?: string;
}

// Everything the article authoring page needs, assembled from one unit per
// concern: form state, images, the initial load, persistence and the leave
// guard. This is the only thing the page imports — the units below it are an
// implementation detail, so they can be re-cut without touching consumers.
//
// What is left here is what genuinely spans them: the shared error message, the
// article's routing decisions, and the sweep that reads the last committed
// state at unmount.
export function useArticleDraft({ project, articleId }: Options) {
  const router = useRouter();
  const projectRef = project.slug ?? project.id;

  // One message, whatever produced it: the page has a single place to show it.
  const [error, setError] = useState("");

  const {
    fields,
    getBody,
    reset,
    updateFields,
    handleBodyChange,
    snapshot,
    applySaved,
    isDirty: fieldsAreDirty,
  } = useArticleForm();

  // Read by the unmount cleanup, which cannot see current state.
  const latestRef = useRef<{
    article: Article | null;
    fields: ArticleFormFields | null;
    leaving: boolean;
  }>({
    article: null,
    fields: null,
    leaving: false,
  });

  const handleCreated = useCallback(
    (created: Article) => {
      // /new and /edit are different routes, so the replace unmounts this page.
      // Without this the untouched-draft sweep below would delete the draft we
      // are navigating to.
      latestRef.current.leaving = true;
      router.replace(`/projects/${projectRef}/articles/edit/${created.id}`);
    },
    [projectRef, router],
  );

  const { channels, article, setArticle, isLoading } = useArticleLoad({
    projectRef,
    articleId,
    onLoaded: reset,
    onCreated: handleCreated,
    onError: setError,
  });

  const { images, listingImage, adoptImage } = useArticleImages(
    article,
    setArticle,
    fields?.listing_image_id ?? null,
  );

  const handlePersisted = useCallback(
    (updated: Article) => {
      setArticle(updated);
      applySaved(updated);
    },
    [setArticle, applySaved],
  );

  const {
    save: persist,
    publish: persistAndPublish,
    remove: deleteArticle,
    isSaving,
    isPublishing,
    isDeleting,
    successMessage,
  } = useArticleMutations({
    projectRef,
    article,
    onPersisted: handlePersisted,
    onError: setError,
  });

  // Kept in an effect, not written during render: the cleanup below is the
  // only reader, and it runs after the last commit.
  useEffect(() => {
    latestRef.current.article = article;
    latestRef.current.fields = fields;
  }, [article, fields]);

  // Best-effort sweep of the draft /new created when the author leaves without
  // writing anything. What survives it is a draft in the author's own list,
  // invisible to readers, with a delete button next to it.
  useEffect(() => {
    const state = latestRef.current;
    return () => {
      const current = state.article;
      if (state.leaving || !current) return;
      if (
        !shouldDiscardDraft({
          article: current,
          fields: state.fields,
          body: getBody(),
        })
      )
        return;
      api.articles.delete(projectRef, current.id).catch(() => {});
    };
  }, [projectRef, getBody]);

  const isDirty = useCallback(
    () => fieldsAreDirty(article),
    [fieldsAreDirty, article],
  );
  const confirmLeave = useLeaveGuard(isDirty);

  // The wizard's outcome: an image and the rectangle the author drew on it.
  // Any choice commits the mode, so the next save does not re-derive the image
  // out from under a rectangle they just drew.
  const chooseListingImage = useCallback(
    (image: ProjectImage, crop: CropRect | null) => {
      adoptImage(image);
      updateFields({
        listing_image_id: image.id,
        listing_crop: crop,
        listing_image_mode: "chosen",
      });
    },
    [adoptImage, updateFields],
  );

  const removeListingImage = useCallback(() => {
    updateFields({
      listing_image_id: null,
      listing_crop: null,
      listing_image_mode: "none",
    });
  }, [updateFields]);

  const save = useCallback(async (): Promise<Article | null> => {
    const payload = snapshot();
    if (!payload) return null;
    return persist(payload);
  }, [snapshot, persist]);

  // The two mutations that end the session: the page they were performed on is
  // gone, so the hook takes itself off the screen. `leaving` suppresses the
  // sweep for the unmount that follows.
  const publish = useCallback(async () => {
    const payload = snapshot();
    if (!payload) return;
    const published = await persistAndPublish(payload);
    if (!published) return;
    latestRef.current.leaving = true;
    router.push(`/projects/${projectRef}`);
  }, [snapshot, persistAndPublish, projectRef, router]);

  const remove = useCallback(async () => {
    const deleted = await deleteArticle();
    if (!deleted) return;
    latestRef.current.leaving = true;
    router.push(`/projects/${projectRef}`);
  }, [deleteArticle, projectRef, router]);

  return {
    channels,
    article,
    form: fields,
    images,
    listingImage,
    isLoading,
    error,
    setError,
    successMessage,
    isSaving,
    isPublishing,
    isDeleting,
    isPublished: article?.state === "published",
    handleBodyChange,
    updateForm: updateFields,
    snapshotForm: snapshot,
    isDirty,
    confirmLeave,
    chooseListingImage,
    removeListingImage,
    save,
    publish,
    remove,
  };
}
