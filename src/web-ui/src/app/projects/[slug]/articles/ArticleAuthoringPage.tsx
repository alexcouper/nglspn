"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useMemo, useState } from "react";
import { ArrowPathIcon, TrashIcon } from "@heroicons/react/24/outline";
import { useAuth } from "@/contexts/auth";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { useImageUpload } from "@/hooks/useImageUpload";
import { api } from "@/lib/api";
import type { Project, ProjectImage } from "@/lib/api";
import { ImageCropDialog } from "@/components/ImageCropDialog";
import type { CropRect } from "@/components/CroppedImage";
import { pickVariant } from "@/lib/utils";
import { PublishDialog } from "./PublishDialog";
import { ArticleCardPreviewDialog } from "./ArticleCardPreviewDialog";
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
  const [showCardPreview, setShowCardPreview] = useState(false);
  const [isOpeningPreview, setIsOpeningPreview] = useState(false);
  // A hero that has been uploaded but not yet framed. It is deliberately not in
  // the draft form: cancelling the crop dialog must leave the article as it was.
  const [pendingHero, setPendingHero] = useState<ProjectImage | null>(null);
  const [isAdjustingFraming, setIsAdjustingFraming] = useState(false);

  const canEdit = useMemo(() => {
    if (!user) return false;
    return project.contributors.some(
      (c) => c.user.id === user.id && c.full_edit,
    );
  }, [project.contributors, user]);

  const { uploadFile: uploadHeroFile, isUploading: isHeroUploading } =
    useImageUpload({
      projectId: project.id,
      source: "article",
      // Frame it before it becomes the hero. An image with no recorded
      // dimensions cannot be cropped, so it skips the dialog and lands
      // uncropped — the 16:9 centre fallback, which is what it would get anyway.
      onUploadComplete: (image) => {
        if (image.width && image.height) {
          setPendingHero(image);
        } else {
          draft.handleHeroUpload(image, null);
        }
      },
      onError: (err) => draft.setError(err.message),
    });

  // The image the crop dialog is working on: a fresh upload, or the current
  // hero when the author asked to re-frame it.
  const croppingImage = pendingHero ?? (isAdjustingFraming ? draft.heroImage : null);

  const handleCropConfirm = (crop: CropRect) => {
    if (pendingHero) {
      draft.handleHeroUpload(pendingHero, crop);
      setPendingHero(null);
    } else {
      draft.setHeroCrop(crop);
    }
    setIsAdjustingFraming(false);
  };

  const handleCropCancel = () => {
    // A cancelled first upload never becomes the hero, so the file it left
    // behind is deleted. Best-effort: article images are excluded from the
    // project gallery, so a failure leaves an invisible orphan rather than a
    // visible one.
    if (pendingHero) {
      api.myProjects.deleteImage(project.id, pendingHero.id).catch(() => {});
      setPendingHero(null);
    }
    setIsAdjustingFraming(false);
  };

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

  // The derived summary lives only in the backend, so the preview has to render
  // a saved article — otherwise it would show a stale excerpt for unsaved body
  // text. Save first; if that fails, draft.error already says why.
  const handlePreviewClick = async () => {
    setIsOpeningPreview(true);
    await draft.save();
    setIsOpeningPreview(false);
    setShowCardPreview(true);
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
            {draft.article && (
              <button
                onClick={handlePreviewClick}
                disabled={
                  draft.isSaving ||
                  draft.isPublishing ||
                  isOpeningPreview ||
                  draft.needsHeroImage
                }
                className="text-sm py-2 px-4 rounded-lg border border-border text-foreground hover:bg-muted transition-colors"
              >
                {isOpeningPreview ? (
                  <ArrowPathIcon className="w-4 h-4 animate-spin" />
                ) : (
                  "Preview card"
                )}
              </button>
            )}
            <button
              onClick={draft.save}
              disabled={
                draft.isSaving || draft.isPublishing || draft.needsHeroImage
              }
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
          crop={draft.form.hero_crop}
          articleId={draft.article?.id ?? "new"}
          isUploading={isHeroUploading}
          onUpload={uploadHeroFile}
          onAdjustFraming={() => setIsAdjustingFraming(true)}
          onClear={draft.clearHero}
        />

        {draft.needsHeroImage && (
          <p className="text-sm text-amber-800" role="alert">
            Published articles need a hero image — add one before saving.
          </p>
        )}

        <ArticleEditor
          projectId={project.id}
          initialMarkdown={draft.form.body}
          onChange={draft.handleBodyChange}
        />
      </div>

      {showPublishDialog && (
        <PublishDialog
          onClose={() => setShowPublishDialog(false)}
          onConfirm={() => {
            setShowPublishDialog(false);
            draft.publish();
          }}
          isPublishing={draft.isPublishing}
        />
      )}

      {croppingImage && croppingImage.width && croppingImage.height && (
        <ImageCropDialog
          isOpen
          src={pickVariant(croppingImage.variants, "large") ?? croppingImage.url}
          naturalWidth={croppingImage.width}
          naturalHeight={croppingImage.height}
          initial={pendingHero ? null : draft.form.hero_crop}
          title="Frame the hero image"
          onConfirm={handleCropConfirm}
          onCancel={handleCropCancel}
        />
      )}

      {showCardPreview && draft.article && (
        <ArticleCardPreviewDialog
          article={draft.article}
          projectSlug={project.slug ?? project.id}
          onClose={() => setShowCardPreview(false)}
          onSaved={draft.setArticle}
        />
      )}
    </>
  );
}
