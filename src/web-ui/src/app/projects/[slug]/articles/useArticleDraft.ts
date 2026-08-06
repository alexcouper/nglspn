"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { Article, Channel, Project, ProjectImage } from "@/lib/api";
import { ApiRequestError } from "@/lib/api/base";
import type { CropRect } from "@/components/CroppedImage";

// How the article's listing image was decided. Mirrors ListingImageMode in
// apps/articles/models.py.
export type ListingImageMode = "auto" | "chosen" | "none";

export interface ArticleFormState {
  title: string;
  body: string;
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

interface Options {
  project: Project;
  // Present → editing an existing article. Absent → the /new route, which
  // creates a draft immediately (see below) rather than waiting for a save.
  articleId?: string;
}

// True when nothing has been written to this draft. Used to sweep up the empty
// draft that opening /new creates when the author leaves without editing.
function isUntouched(article: Article, body: string): boolean {
  return (
    !article.title.trim() &&
    !body.trim() &&
    !article.listing_image_id &&
    article.images.length === 0
  );
}

// Form + persistence state for the article authoring page.
//
// Separated from the page component so the component is mostly layout/wiring.
// Owns: the eager draft creation on /new, initial load (channels + article),
// form snapshot (form fields plus the uncontrolled MDXEditor body held in a
// ref), and save/publish/delete.
export function useArticleDraft({ project, articleId }: Options) {
  const router = useRouter();
  const projectRef = project.slug ?? project.id;

  const [channels, setChannels] = useState<Channel[]>([]);
  const [article, setArticle] = useState<Article | null>(null);
  const [form, setForm] = useState<ArticleFormState | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Track the in-memory body separately from the article form to avoid
  // MDXEditor re-keying on every keystroke (it is uncontrolled internally).
  const bodyRef = useRef<string>("");
  // React StrictMode runs effects twice in development. Without this guard
  // opening /new would create two drafts per visit.
  const creatingRef = useRef(false);
  // Read by the unmount cleanup, which cannot see current state.
  const latestRef = useRef<{ article: Article | null; leaving: boolean }>({
    article: null,
    leaving: false,
  });

  const isEditing = !!articleId;

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const channelList = await api.channels.list(projectRef);
        if (cancelled) return;
        setChannels(channelList);

        // An upload cannot name an article that does not exist yet, so /new
        // creates an empty draft up front and swaps the URL to /edit/<id> —
        // the same swap that used to happen on first save, moved earlier.
        let loaded: Article;
        if (isEditing) {
          loaded = await api.articles.get(projectRef, articleId!);
        } else {
          if (creatingRef.current) return;
          creatingRef.current = true;
          loaded = await api.articles.create(projectRef, {
            channel_id: channelList[0]?.id ?? "",
            title: "",
            body: "",
          });
          if (cancelled) return;
          // /new and /edit are different routes, so the replace unmounts this
          // page. Without this the untouched-draft sweep below would delete
          // the draft we are navigating to.
          latestRef.current.leaving = true;
          router.replace(`/projects/${projectRef}/articles/edit/${loaded.id}`);
        }
        if (cancelled) return;

        setArticle(loaded);
        bodyRef.current = loaded.body;
        setForm({
          title: loaded.title,
          body: loaded.body,
          channel_id: loaded.channel.id,
          summary: loaded.summary,
          listing_image_id: loaded.listing_image_id,
          listing_crop: loaded.listing_crop,
          listing_image_mode: loaded.listing_image_mode as ListingImageMode,
        });
        setIsLoading(false);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load article");
        setIsLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [isEditing, articleId, projectRef, router]);

  // Kept in an effect, not written during render: the cleanup below is the
  // only reader, and it runs after the last commit.
  useEffect(() => {
    latestRef.current.article = article;
  }, [article]);

  // Best-effort sweep of the draft /new created when the author leaves without
  // writing anything. What survives it is a draft in the author's own list,
  // invisible to readers, with a delete button next to it.
  useEffect(() => {
    const state = latestRef.current;
    return () => {
      const current = state.article;
      if (state.leaving || !current) return;
      if (!isUntouched(current, bodyRef.current)) return;
      api.articles.delete(projectRef, current.id).catch(() => {});
    };
  }, [projectRef]);

  const handleBodyChange = useCallback((markdown: string) => {
    bodyRef.current = markdown;
  }, []);

  const updateForm = useCallback((patch: Partial<ArticleFormState>) => {
    setForm((prev) => (prev ? { ...prev, ...patch } : prev));
  }, []);

  // Merge the current form fields with the live MDXEditor body. Used by every
  // handler that hits the network so they never persist stale body text.
  const snapshotForm = useCallback((): ArticleFormState | null => {
    if (!form) return null;
    const current: ArticleFormState = { ...form, body: bodyRef.current };
    setForm(current);
    return current;
  }, [form]);

  // The wizard's outcome: an image and the rectangle the author drew on it.
  // Any choice commits the mode, so the next save does not re-derive the image
  // out from under a rectangle they just drew.
  const chooseListingImage = useCallback(
    (image: ProjectImage, crop: CropRect | null) => {
      setForm((prev) =>
        prev
          ? {
              ...prev,
              listing_image_id: image.id,
              listing_crop: crop,
              listing_image_mode: "chosen",
            }
          : prev,
      );
    },
    [],
  );

  const removeListingImage = useCallback(() => {
    setForm((prev) =>
      prev
        ? {
            ...prev,
            listing_image_id: null,
            listing_crop: null,
            listing_image_mode: "none",
          }
        : prev,
    );
  }, []);

  const persistDraft = useCallback(
    async (current: ArticleFormState): Promise<Article | null> => {
      if (!article) return null;
      try {
        const updated = await api.articles.update(projectRef, article.id, {
          title: current.title,
          body: current.body,
          channel_id: current.channel_id,
          summary: current.summary,
          listing_image_id: current.listing_image_id,
          listing_crop: current.listing_crop,
          listing_image_mode: current.listing_image_mode,
        });
        setArticle(updated);
        // `auto` is resolved server-side on every save, so the response is the
        // only place the resolved image id exists.
        setForm((prev) =>
          prev
            ? {
                ...prev,
                listing_image_id: updated.listing_image_id,
                listing_crop: updated.listing_crop,
                listing_image_mode:
                  updated.listing_image_mode as ListingImageMode,
              }
            : prev,
        );
        return updated;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to save article");
        return null;
      }
    },
    [article, projectRef],
  );

  const save = useCallback(async (): Promise<Article | null> => {
    const current = snapshotForm();
    if (!current) return null;
    setError("");
    setSuccessMessage("");
    setIsSaving(true);
    const saved = await persistDraft(current);
    setIsSaving(false);
    if (saved) {
      setSuccessMessage(saved.state === "published" ? "Saved" : "Draft saved");
      setTimeout(() => setSuccessMessage(""), 2500);
    }
    return saved;
  }, [snapshotForm, persistDraft]);

  const publish = useCallback(async () => {
    const current = snapshotForm();
    if (!current) return;
    setError("");
    setIsPublishing(true);
    const saved = await persistDraft(current);
    if (!saved) {
      setIsPublishing(false);
      return;
    }
    try {
      await api.articles.publish(projectRef, saved.id, { published_at: null });
      latestRef.current.leaving = true;
      router.push(`/projects/${projectRef}`);
    } catch (err) {
      if (err instanceof ApiRequestError && err.status === 422) {
        const detail =
          typeof err.body.detail === "string"
            ? err.body.detail
            : "Article is not ready to publish.";
        setError(detail);
      } else {
        setError(
          err instanceof Error ? err.message : "Failed to publish article",
        );
      }
      setIsPublishing(false);
    }
  }, [snapshotForm, persistDraft, projectRef, router]);

  const remove = useCallback(async () => {
    if (!article) return;
    setIsDeleting(true);
    try {
      await api.articles.delete(projectRef, article.id);
      latestRef.current.leaving = true;
      router.push(`/projects/${projectRef}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete article");
      setIsDeleting(false);
    }
  }, [article, projectRef, router]);

  return {
    channels,
    article,
    setArticle,
    form,
    // The article's own uploads — the wizard's selection list. Comes off the
    // image-article link, so it holds whatever was uploaded for this article
    // whether or not it is in the body.
    images: article?.images ?? [],
    // The image the form currently points at, not the last-saved one: the
    // panel must show what the wizard just picked, before any save.
    listingImage:
      article?.images.find((image) => image.id === form?.listing_image_id) ??
      (form?.listing_image_id &&
      form.listing_image_id === article?.listing_image_id
        ? article.listing_image
        : null),
    isLoading,
    error,
    setError,
    successMessage,
    isSaving,
    isPublishing,
    isDeleting,
    isPublished: article?.state === "published",
    handleBodyChange,
    updateForm,
    snapshotForm,
    chooseListingImage,
    removeListingImage,
    save,
    publish,
    remove,
  };
}
