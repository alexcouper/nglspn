"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useMemo, useState } from "react";
import { ArrowPathIcon, TrashIcon } from "@heroicons/react/24/outline";
import { useAuth } from "@/contexts/auth";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { useImageUpload } from "@/hooks/useImageUpload";
import type { Project } from "@/lib/api";
import { PublishDialog } from "./PublishDialog";
import { HeroImageUploader } from "./HeroImageUploader";
import { ChannelDropdown } from "./ChannelDropdown";
import { useArticleDraft } from "./useArticleDraft";

const ArticleEditor = dynamic(
  () => import("./ArticleEditor").then((m) => m.ArticleEditor),
  { ssr: false, loading: () => <div className="skeleton h-[60vh] w-full" /> },
);

interface Props {
  project: Project;
  // Present → editing an existing article; absent → creating a new one.
  articleId?: string;
}

export function ArticleAuthoringPage({ project, articleId }: Props) {
  const { user } = useAuth();
  const { isReady, isLoading: authLoading } = useRequireAuth();

  const draft = useArticleDraft({ project, articleId });
  const [showPublishDialog, setShowPublishDialog] = useState(false);

  const canEdit = useMemo(() => {
    if (!user) return false;
    return project.contributors.some(
      (c) => c.user.id === user.id && c.full_edit,
    );
  }, [project.contributors, user]);

  const { uploadFile: uploadHeroFile, isUploading: isHeroUploading } =
    useImageUpload({
      projectId: project.id,
      onUploadComplete: draft.handleHeroUpload,
      onError: (err) => draft.setError(err.message),
    });

  const isEditing = !!articleId;
  const mode = isEditing ? "Edit article" : "New article";

  if (!isReady || authLoading || draft.isLoading) {
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

  if (!draft.form) return null;

  const handleDeleteClick = async () => {
    if (!window.confirm("Delete this article? This cannot be undone.")) return;
    await draft.remove();
  };

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
            <span className="text-foreground font-medium">{mode}</span>
          </div>
          <div className="flex items-center gap-2">
            {draft.successMessage && (
              <span className="text-emerald-600 text-sm">
                {draft.successMessage}
              </span>
            )}
            {draft.error && (
              <span className="text-red-600 text-sm" role="alert">
                {draft.error}
              </span>
            )}
            <button
              onClick={draft.save}
              disabled={draft.isSaving || draft.isPublishing}
              className="btn-primary text-sm py-2 px-4"
            >
              {draft.isSaving ? (
                <ArrowPathIcon className="w-4 h-4 animate-spin" />
              ) : draft.isPublished ? (
                "Save"
              ) : (
                "Save draft"
              )}
            </button>
            {!draft.isPublished && (
              <button
                onClick={() => {
                  draft.snapshotForm();
                  setShowPublishDialog(true);
                }}
                disabled={draft.isSaving || draft.isPublishing}
                className="btn-primary text-sm py-2 px-4"
              >
                {draft.isPublishing ? (
                  <ArrowPathIcon className="w-4 h-4 animate-spin" />
                ) : (
                  "Publish"
                )}
              </button>
            )}
            {draft.article && (
              <button
                onClick={handleDeleteClick}
                disabled={draft.isDeleting}
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
            value={draft.form.title}
            onChange={(e) => draft.updateForm({ title: e.target.value })}
            placeholder="Article title"
            className="w-full rounded-lg border border-border bg-white px-3.5 py-2.5 text-lg font-semibold text-foreground placeholder:text-[#94a3b8] focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/12 transition-[border-color,box-shadow]"
          />
          <ChannelDropdown
            channels={draft.channels}
            value={draft.form.channel_id}
            onChange={(value) => draft.updateForm({ channel_id: value })}
          />
        </div>

        <HeroImageUploader
          heroImage={draft.heroImage}
          isUploading={isHeroUploading}
          onUpload={uploadHeroFile}
          onClear={draft.clearHero}
        />

        <ArticleEditor
          projectId={project.id}
          initialMarkdown={draft.form.body}
          onChange={draft.handleBodyChange}
        />
      </div>

      {showPublishDialog && (
        <PublishDialog
          onClose={() => setShowPublishDialog(false)}
          onConfirm={(publishedAt) => {
            setShowPublishDialog(false);
            draft.publish(publishedAt);
          }}
          isPublishing={draft.isPublishing}
        />
      )}
    </>
  );
}
