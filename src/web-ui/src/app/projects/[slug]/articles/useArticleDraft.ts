"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type {
  Article,
  Channel,
  Project,
  ProjectImage,
} from "@/lib/api";
import { ApiRequestError } from "@/lib/api/base";

export interface ArticleFormState {
  title: string;
  body: string;
  channel_id: string;
  hero_image_id: string | null;
}

interface Options {
  project: Project;
  // Present → editing an existing article; absent → creating a new one.
  articleId?: string;
}

// Form + persistence state for the article authoring page.
//
// Separated from the page component so the component is mostly layout/wiring.
// Owns: initial load (channels + article), form snapshot (form fields plus
// the uncontrolled MDXEditor body held in a ref), save/publish/delete, and
// the post-create URL swap from /new to /edit/{id}.
export function useArticleDraft({ project, articleId }: Options) {
  const router = useRouter();

  const [channels, setChannels] = useState<Channel[]>([]);
  const [article, setArticle] = useState<Article | null>(null);
  const [form, setForm] = useState<ArticleFormState | null>(null);
  const [heroImage, setHeroImage] = useState<ProjectImage | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Track the in-memory body separately from the article form to avoid
  // MDXEditor re-keying on every keystroke (it is uncontrolled internally).
  const bodyRef = useRef<string>("");

  const isEditing = !!articleId;

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const channelList = await api.channels.list(project.slug ?? project.id);
        if (cancelled) return;
        setChannels(channelList);

        if (isEditing) {
          const loaded = await api.articles.get(
            project.slug ?? project.id,
            articleId!,
          );
          if (cancelled) return;
          setArticle(loaded);
          bodyRef.current = loaded.body;
          setForm({
            title: loaded.title,
            body: loaded.body,
            channel_id: loaded.channel.id,
            hero_image_id: loaded.hero_image_id,
          });
          if (loaded.hero_image_id) {
            const match = project.images.find(
              (img) => img.id === loaded.hero_image_id,
            );
            setHeroImage(match ?? null);
          }
        } else {
          bodyRef.current = "";
          setForm({
            title: "",
            body: "",
            channel_id: channelList[0]?.id ?? "",
            hero_image_id: null,
          });
        }
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
  }, [isEditing, articleId, project.slug, project.id, project.images]);

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

  const handleHeroUpload = useCallback((image: ProjectImage) => {
    setHeroImage(image);
    setForm((prev) =>
      prev ? { ...prev, hero_image_id: image.id } : prev,
    );
  }, []);

  const clearHero = useCallback(() => {
    setHeroImage(null);
    setForm((prev) => (prev ? { ...prev, hero_image_id: null } : prev));
  }, []);

  const persistDraft = useCallback(
    async (current: ArticleFormState): Promise<Article | null> => {
      try {
        if (!article) {
          const created = await api.articles.create(
            project.slug ?? project.id,
            {
              channel_id: current.channel_id,
              title: current.title,
              body: current.body,
              hero_image_id: current.hero_image_id ?? null,
            },
          );
          setArticle(created);
          // Switch URL to /edit so subsequent saves PATCH instead of POST.
          router.replace(
            `/projects/${project.slug ?? project.id}/articles/edit/${created.id}`,
          );
          return created;
        }
        const updated = await api.articles.update(
          project.slug ?? project.id,
          article.id,
          {
            title: current.title,
            body: current.body,
            channel_id: current.channel_id,
            hero_image_id: current.hero_image_id ?? null,
          },
        );
        setArticle(updated);
        return updated;
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to save article",
        );
        return null;
      }
    },
    [article, project.id, project.slug, router],
  );

  const save = useCallback(async () => {
    const current = snapshotForm();
    if (!current) return;
    setError("");
    setSuccessMessage("");
    setIsSaving(true);
    const saved = await persistDraft(current);
    setIsSaving(false);
    if (saved) {
      setSuccessMessage(saved.state === "published" ? "Saved" : "Draft saved");
      setTimeout(() => setSuccessMessage(""), 2500);
    }
  }, [snapshotForm, persistDraft]);

  const publish = useCallback(
    async () => {
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
        await api.articles.publish(project.slug ?? project.id, saved.id, {
          published_at: null,
        });
        router.push(`/projects/${project.slug ?? project.id}`);
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
    },
    [snapshotForm, persistDraft, project.id, project.slug, router],
  );

  const remove = useCallback(async () => {
    if (!article) return;
    setIsDeleting(true);
    try {
      await api.articles.delete(project.slug ?? project.id, article.id);
      router.push(`/projects/${project.slug ?? project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete article");
      setIsDeleting(false);
    }
  }, [article, project.id, project.slug, router]);

  return {
    channels,
    article,
    form,
    heroImage,
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
    handleHeroUpload,
    clearHero,
    save,
    publish,
    remove,
  };
}
