"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useMemo, useState } from "react";
import { ArrowPathIcon, TrashIcon } from "@heroicons/react/24/outline";
import { useAuth } from "@/contexts/auth";
import type { Project } from "@/lib/api";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { PublishDialog } from "./PublishDialog";
import { ChannelDropdown } from "./ChannelDropdown";
import { ListingImageDialog } from "./ListingImageDialog";
import { ListingSettingsPanel } from "./ListingSettingsPanel";
import { useArticleDraft } from "./useArticleDraft";

const ArticleEditor = dynamic(
  () => import("./ArticleEditor").then((m) => m.ArticleEditor),
  { ssr: false, loading: () => <div className="skeleton h-[60vh] w-full" /> },
);

type Tab = "content" | "listing";

const TABS: { key: Tab; label: string }[] = [
  { key: "content", label: "Content" },
  { key: "listing", label: "Listing settings" },
];

interface Props {
  project: Project;
  // Present → editing an existing article; absent → the /new route, which
  // creates a draft on mount and swaps the URL to /edit/<id>.
  articleId?: string;
}

export function ArticleAuthoringPage({ project, articleId }: Props) {
  const { user } = useAuth();
  const { isReady, isLoading: authLoading } = useRequireAuth();

  // One reference to the project for everything under the article editor.
  // Article images are addressed by the article that owns them, so the editor
  // no longer needs the project's UUID alongside this.
  const projectRef = project.slug ?? project.id;

  const draft = useArticleDraft({ project, articleId });
  const [showPublishDialog, setShowPublishDialog] = useState(false);
  const [showImageWizard, setShowImageWizard] = useState(false);
  const [tab, setTab] = useState<Tab>("content");
  const [isSwitchingTab, setIsSwitchingTab] = useState(false);

  const canEdit = useMemo(() => {
    if (!user) return false;
    return project.contributors.some(
      (c) => c.user.id === user.id && c.full_edit,
    );
  }, [project.contributors, user]);

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
        <h1 className="text-lg font-semibold text-foreground">Not allowed</h1>
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

  if (!draft.form || !draft.article) return null;

  const article = draft.article;
  const form = draft.form;

  const handleDeleteClick = async () => {
    if (!window.confirm("Delete this article? This cannot be undone.")) return;
    await draft.remove();
  };

  // The previewed summary is derived server-side from the saved body, so the
  // listing tab has to render a saved article — otherwise it would show a stale
  // excerpt for text the author has just typed. On failure the tab does not
  // open, and draft.error already says why.
  const handleTabClick = async (next: Tab) => {
    if (next === tab) return;
    if (next !== "listing") {
      setTab(next);
      return;
    }
    setIsSwitchingTab(true);
    const saved = await draft.save();
    setIsSwitchingTab(false);
    if (saved) setTab("listing");
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
            <button
              onClick={handleDeleteClick}
              disabled={draft.isDeleting}
              title="Delete article"
              className="p-2 rounded-lg text-muted-foreground border border-border hover:bg-red-50 hover:text-red-600 hover:border-red-200 transition-colors"
            >
              <TrashIcon className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 space-y-4">
        {/* Above the tabs: the title is article identity and it is what the
            card preview renders, so tuning a headline for the card should not
            mean changing tabs. */}
        <div className="grid grid-cols-1 sm:grid-cols-[1fr_auto] gap-3 sm:items-center">
          <input
            type="text"
            value={form.title}
            onChange={(e) => draft.updateForm({ title: e.target.value })}
            placeholder="Article title"
            className="w-full rounded-lg border border-border bg-white px-3.5 py-2.5 text-lg font-semibold text-foreground placeholder:text-[#94a3b8] focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/12 transition-[border-color,box-shadow]"
          />
          <ChannelDropdown
            channels={draft.channels}
            value={form.channel_id}
            onChange={(value) => draft.updateForm({ channel_id: value })}
          />
        </div>

        <div role="tablist" aria-label="Article editor" className="flex gap-1">
          {TABS.map(({ key, label }) => (
            <button
              key={key}
              role="tab"
              aria-selected={tab === key}
              disabled={isSwitchingTab}
              onClick={() => handleTabClick(key)}
              className={`flex items-center gap-1.5 border-b-2 px-3 py-2 text-sm transition-colors ${
                tab === key
                  ? "border-accent font-medium text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {label}
              {key === "listing" && isSwitchingTab && (
                <ArrowPathIcon className="w-3.5 h-3.5 animate-spin" />
              )}
            </button>
          ))}
        </div>

        {/* Mounted, not unmounted, when hidden: MDXEditor holds the body
            uncontrolled, and remounting it on every tab switch would lose the
            cursor and re-run its plugin setup. */}
        <div className={tab === "content" ? undefined : "hidden"}>
          <ArticleEditor
            projectRef={projectRef}
            articleId={article.id}
            initialMarkdown={form.body}
            onChange={draft.handleBodyChange}
          />
        </div>

        {tab === "listing" && (
          <ListingSettingsPanel
            article={article}
            summary={form.summary}
            listingImage={draft.listingImage}
            crop={form.listing_crop}
            mode={form.listing_image_mode}
            onSummaryChange={(value) => draft.updateForm({ summary: value })}
            onChangeImage={() => setShowImageWizard(true)}
            onRemoveImage={draft.removeListingImage}
          />
        )}
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

      {showImageWizard && (
        <ListingImageDialog
          projectRef={projectRef}
          articleId={article.id}
          images={draft.images}
          currentImageId={form.listing_image_id}
          currentCrop={form.listing_crop}
          onConfirm={(image, crop) => {
            draft.chooseListingImage(image, crop);
            setShowImageWizard(false);
          }}
          onRemove={() => {
            draft.removeListingImage();
            setShowImageWizard(false);
          }}
          onClose={() => setShowImageWizard(false)}
        />
      )}
    </>
  );
}
