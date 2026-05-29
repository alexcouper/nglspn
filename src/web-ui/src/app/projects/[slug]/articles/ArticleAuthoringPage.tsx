"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowPathIcon, TrashIcon } from "@heroicons/react/24/outline";
import { useAuth } from "@/contexts/auth";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { useImageUpload } from "@/hooks/useImageUpload";
import { api } from "@/lib/api";
import type { Article, Channel, Project, ProjectImage } from "@/lib/api";
import { ApiRequestError } from "@/lib/api/base";
import { PublishDialog } from "./PublishDialog";
import { HeroImageUploader } from "./HeroImageUploader";
import { ChannelDropdown } from "./ChannelDropdown";

const ArticleEditor = dynamic(
  () => import("./ArticleEditor").then((m) => m.ArticleEditor),
  { ssr: false, loading: () => <div className="skeleton h-[60vh] w-full" /> },
);

interface Props {
  project: Project;
  mode: "new" | "edit";
  articleId?: string;
}

interface FormState {
  title: string;
  body: string;
  channel_id: string;
  hero_image_id: string | null;
}

export function ArticleAuthoringPage({ project, mode, articleId }: Props) {
  const router = useRouter();
  const { user } = useAuth();
  const { isReady, isLoading: authLoading } = useRequireAuth();

  const [channels, setChannels] = useState<Channel[]>([]);
  const [article, setArticle] = useState<Article | null>(null);
  const [form, setForm] = useState<FormState | null>(null);
  const [heroImage, setHeroImage] = useState<ProjectImage | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [showPublishDialog, setShowPublishDialog] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  // Track the in-memory body separately from the article form to avoid
  // MDXEditor re-keying on every keystroke (it is uncontrolled internally).
  const bodyRef = useRef<string>("");

  const isPublished = article?.state === "published";

  const canEdit = useMemo(() => {
    if (!user) return false;
    return project.contributors.some(
      (c) => c.user.id === user.id && c.full_edit,
    );
  }, [project.contributors, user]);

  useEffect(() => {
    if (!isReady) return;
    let cancelled = false;

    async function load() {
      try {
        const channelList = await api.channels.list(project.slug ?? project.id);
        if (cancelled) return;
        setChannels(channelList);

        if (mode === "edit" && articleId) {
          const loaded = await api.articles.get(
            project.slug ?? project.id,
            articleId,
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
  }, [isReady, mode, articleId, project.slug, project.id, project.images]);

  const { uploadFile: uploadHeroFile, isUploading: isHeroUploading } =
    useImageUpload({
      projectId: project.id,
      onUploadComplete: (image) => {
        setHeroImage(image);
        setForm((prev) =>
          prev ? { ...prev, hero_image_id: image.id } : prev,
        );
      },
      onError: (err) => setError(err.message),
    });

  const handleBodyChange = useCallback((markdown: string) => {
    bodyRef.current = markdown;
  }, []);

  const updateForm = useCallback((patch: Partial<FormState>) => {
    setForm((prev) => (prev ? { ...prev, ...patch } : prev));
  }, []);

  const persistDraft = useCallback(
    async (current: FormState): Promise<Article | null> => {
      try {
        if (mode === "new" || !article) {
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
    [article, mode, project.id, project.slug, router],
  );

  const handleSave = useCallback(async () => {
    if (!form) return;
    setError("");
    setSuccessMessage("");
    setIsSaving(true);
    const current: FormState = { ...form, body: bodyRef.current };
    setForm(current);
    const saved = await persistDraft(current);
    setIsSaving(false);
    if (saved) {
      setSuccessMessage(saved.state === "published" ? "Saved" : "Draft saved");
      setTimeout(() => setSuccessMessage(""), 2500);
    }
  }, [form, persistDraft]);

  const handleOpenPublish = useCallback(() => {
    if (!form) return;
    const current: FormState = { ...form, body: bodyRef.current };
    setForm(current);
    setShowPublishDialog(true);
  }, [form]);

  const handlePublish = useCallback(
    async (publishedAt: string | null) => {
      if (!form) return;
      setError("");
      setIsPublishing(true);
      const current: FormState = { ...form, body: bodyRef.current };
      const saved = await persistDraft(current);
      if (!saved) {
        setIsPublishing(false);
        return;
      }
      try {
        await api.articles.publish(project.slug ?? project.id, saved.id, {
          published_at: publishedAt,
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
    [form, persistDraft, project.id, project.slug, router],
  );

  const handleDelete = useCallback(async () => {
    if (!article) return;
    if (!window.confirm("Delete this article? This cannot be undone.")) return;
    setIsDeleting(true);
    try {
      await api.articles.delete(project.slug ?? project.id, article.id);
      router.push(`/projects/${project.slug ?? project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete article");
      setIsDeleting(false);
    }
  }, [article, project.id, project.slug, router]);

  if (authLoading || isLoading) {
    return (
      <div className="py-8 px-4 sm:px-6">
        <div className="max-w-4xl mx-auto bg-white rounded-xl border border-border p-8">
          <div className="skeleton h-6 w-1/3 mb-4" />
          <div className="skeleton h-48 w-full mb-4 rounded-lg" />
          <div className="skeleton h-4 w-2/3 mb-2" />
        </div>
      </div>
    );
  }

  if (!canEdit) {
    return (
      <div className="max-w-2xl mx-auto py-12 px-4 text-center">
        <h1 className="text-lg font-semibold text-foreground">
          Not allowed
        </h1>
        <p className="text-sm text-muted-foreground mt-2">
          You need full edit access on this project to author articles.
        </p>
        <div className="mt-6">
          <Link
            href={`/projects/${project.slug ?? project.id}`}
            className="text-sm text-accent hover:text-accent-hover"
          >
            Back to project
          </Link>
        </div>
      </div>
    );
  }

  if (!form) return null;

  return (
    <>
      <div className="sticky top-14 z-30 bg-white border-b border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 flex items-center justify-between py-2">
          <div className="text-sm text-muted-foreground">
            <Link
              href={`/my-projects/${project.id}#articles`}
              className="hover:text-foreground"
            >
              {project.title}
            </Link>
            <span className="mx-2">/</span>
            <span className="text-foreground font-medium">
              {mode === "new" ? "New article" : "Edit article"}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {successMessage && (
              <span className="text-emerald-600 text-sm">{successMessage}</span>
            )}
            {error && (
              <span className="text-red-600 text-sm" role="alert">
                {error}
              </span>
            )}
            <button
              onClick={handleSave}
              disabled={isSaving || isPublishing}
              className="btn-primary text-sm py-2 px-4"
            >
              {isSaving ? (
                <ArrowPathIcon className="w-4 h-4 animate-spin" />
              ) : isPublished ? (
                "Save"
              ) : (
                "Save draft"
              )}
            </button>
            {!isPublished && (
              <button
                onClick={handleOpenPublish}
                disabled={isSaving || isPublishing}
                className="btn-primary text-sm py-2 px-4"
              >
                {isPublishing ? (
                  <ArrowPathIcon className="w-4 h-4 animate-spin" />
                ) : (
                  "Publish"
                )}
              </button>
            )}
            {article && (
              <button
                onClick={handleDelete}
                disabled={isDeleting}
                title="Delete article"
                className="p-2 rounded-lg text-muted-foreground border border-border hover:bg-red-50 hover:text-red-600 hover:border-red-200 transition-colors"
              >
                <TrashIcon className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-[1fr_auto] gap-3 sm:items-center">
          <input
            type="text"
            value={form.title}
            onChange={(e) => updateForm({ title: e.target.value })}
            placeholder="Article title"
            className="w-full rounded-lg border border-border bg-white px-3.5 py-2.5 text-lg font-semibold text-foreground placeholder:text-[#94a3b8] focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/12 transition-[border-color,box-shadow]"
          />
          <ChannelDropdown
            channels={channels}
            value={form.channel_id}
            onChange={(value) => updateForm({ channel_id: value })}
          />
        </div>

        <HeroImageUploader
          heroImage={heroImage}
          isUploading={isHeroUploading}
          onUpload={uploadHeroFile}
          onClear={() => {
            setHeroImage(null);
            updateForm({ hero_image_id: null });
          }}
        />

        <ArticleEditor
          projectId={project.id}
          initialMarkdown={form.body}
          onChange={handleBodyChange}
        />
      </div>

      {showPublishDialog && (
        <PublishDialog
          onClose={() => setShowPublishDialog(false)}
          onConfirm={(publishedAt) => {
            setShowPublishDialog(false);
            handlePublish(publishedAt);
          }}
          isPublishing={isPublishing}
        />
      )}
    </>
  );
}
