"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { type CSSProperties, useMemo, useState } from "react";
import { ArrowPathIcon, TrashIcon } from "@heroicons/react/24/outline";
import { useAuth } from "@/contexts/auth";
import type { Project } from "@/lib/api";
import { ArticleAuthoringSkeleton } from "./ArticleAuthoringSkeleton";
import { PublishDialog } from "./PublishDialog";
import { ChannelDropdown } from "./ChannelDropdown";
import { ListingImageDialog } from "./ListingImageDialog";
import { ListingSettingsPanel } from "./ListingSettingsPanel";
import { useArticleDraft } from "./useArticleDraft";
import { useStickyChromeOffset } from "./useStickyChromeOffset";

// The import stays inline: next/dynamic's compile-time transform has to see the
// literal `import()` to register the chunk in the loadable manifest. Hoisting
// it behind a named function still code-splits, but drops it off the manifest —
// which is what the per-route lazy bundle budget measures, so the budget would
// silently start guarding nothing.
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
  // Always an existing article: the New article button creates the draft and
  // routes here, so there is no "unsaved article" state to represent.
  articleId: string;
}

export function ArticleAuthoringPage({ project, articleId }: Props) {
  // `useRequireAuth` lives in ArticleAuthoringRoute, which will not render this
  // until a signed-in caller has a project. `authLoading` still matters here
  // though: `canEdit` below reads `user`, and a null user mid-load would render
  // "Not allowed" at someone who is allowed.
  const { user, isLoading: authLoading } = useAuth();

  // One reference to the project for everything under the article editor.
  // Article images are addressed by the article that owns them, so the editor
  // no longer needs the project's UUID alongside this.
  const projectRef = project.slug ?? project.id;

  const draft = useArticleDraft({ project, articleId });
  // The editor's own toolbar is sticky as well, and has to come to rest below
  // the action bar rather than behind it. See article-markdown.css.
  const { ref: actionBarRef, offset: chromeOffset } = useStickyChromeOffset();
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

  if (authLoading || draft.isLoading) {
    return <ArticleAuthoringSkeleton />;
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

  // Nothing loaded. A deleted draft (404), a contributor who has lost full_edit
  // between page loads (403) and a dropped connection all land here, and none
  // of the affordances below exist yet — so this has to carry draft.error
  // itself rather than leave the author on a blank page.
  if (!draft.form || !draft.article) {
    return (
      <div className="max-w-2xl mx-auto py-12 px-4 text-center">
        <h1 className="text-lg font-semibold text-foreground">
          Couldn&apos;t open this article
        </h1>
        <p className="text-sm text-muted-foreground mt-2" role="alert">
          {draft.error || "The article is no longer available."}
        </p>
        <div className="mt-6">
          <Link
            href={`/projects/${projectRef}`}
            className="text-sm text-accent hover:text-accent-hover"
          >
            Back to project
          </Link>
        </div>
      </div>
    );
  }

  const article = draft.article;
  const form = draft.form;
  // The /new route is gone, so the old "New article" / "Edit article" split has
  // nothing left to say. What still distinguishes two of these pages is whether
  // readers can see the thing yet.
  const mode = draft.isPublished ? "Edit article" : "Edit draft";

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
      <div
        ref={actionBarRef}
        className="sticky top-14 z-30 bg-white border-b border-border"
      >
        <div className="max-w-4xl mx-auto px-4 sm:px-6 flex items-center justify-between py-2">
          <div className="text-sm text-muted-foreground">
            <Link
              href={`/my-projects/${project.id}#articles`}
              className="hover:text-foreground"
              onClick={(e) => {
                // The body is only in memory until a save, so leaving by the
                // breadcrumb is as lossy as closing the tab.
                if (!draft.confirmLeave()) e.preventDefault();
              }}
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

      <div
        className="max-w-4xl mx-auto px-4 sm:px-6 py-6 space-y-4"
        style={
          { "--article-chrome-offset": `${chromeOffset}px` } as CSSProperties
        }
      >
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
            initialMarkdown={article.body}
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
