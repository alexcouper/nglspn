"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { type CSSProperties, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { ArrowPathIcon, EyeIcon, PencilIcon, TrashIcon } from "@heroicons/react/24/outline";
import { useAuth } from "@/contexts/auth";
import type { Article, Project } from "@/lib/api";
import { ArticleAuthoringSkeleton } from "./ArticleAuthoringSkeleton";
import { PublishDialog } from "./PublishDialog";
import { ChannelDropdown } from "./ChannelDropdown";
import { CoverSlot } from "./CoverSlot";
import { ListingImageDialog } from "./ListingImageDialog";
import { ArticlePreview } from "./ArticlePreview";
import { authorContainer, projectContainer } from "./container";
import { useArticleDraft } from "./useArticleDraft";
import { useStickyChromeOffset } from "./useStickyChromeOffset";
import { pickVariant } from "@/lib/utils";

const SUMMARY_MAX = 300;

// The import stays inline: next/dynamic's compile-time transform has to see the
// literal `import()` to register the chunk in the loadable manifest. Hoisting
// it behind a named function still code-splits, but drops it off the manifest —
// which is what the per-route lazy bundle budget measures, so the budget would
// silently start guarding nothing.
const ArticleEditor = dynamic(
  () => import("./ArticleEditor").then((m) => m.ArticleEditor),
  { ssr: false, loading: () => <div className="skeleton h-[60vh] w-full" /> },
);

// Editing, or looking at what the reader will get. Switching to the preview
// saves first: the derived summary and the rendered body are the server's.
type View = "edit" | "preview";

const VIEWS: View[] = ["edit", "preview"];

interface Props {
  // Null for an author-owned article: no channel dropdown, and the breadcrumb
  // leads to the author's profile rather than to my-projects.
  project: Project | null;
  // Always an existing article: the Write article button creates the draft
  // and routes here, so there is no "unsaved article" state to represent. The
  // route loaded it to find the project, so it arrives whole.
  initialArticle: Article;
}

export function ArticleAuthoringPage({ project, initialArticle }: Props) {
  // `useRequireAuth` lives in ArticleAuthoringRoute, which will not render this
  // until a signed-in caller has an article. `authLoading` still matters here
  // though: `canEdit` below reads `user`, and a null user mid-load would render
  // "Not allowed" at someone who is allowed.
  const { user, isLoading: authLoading } = useAuth();
  const articleId = initialArticle.id;
  const t = useTranslations("articles.authoring");
  const tc = useTranslations("common.actions");
  // Spelled out rather than t(`view.${key}`): a template-literal key is not
  // checked against the messages, so adding a view would render its own key
  // path. `tsc` now fails on a missing message and on a missing view alike.
  const viewLabels: Record<View, string> = {
    edit: t("view.edit"),
    preview: t("view.preview"),
  };

  // Where the author came from and goes back to: the project page, or their
  // own profile for an author-owned article.
  const containerHref = project
    ? `/projects/${project.slug ?? project.id}`
    : `/users/${initialArticle.author?.id ?? ""}`;
  const backToContainer = project ? t("backToProject") : t("backToProfile");

  const draft = useArticleDraft({ project, articleId, initialArticle });
  // The editor's own toolbar is sticky as well, and has to come to rest below
  // the action bar rather than behind it. See article-markdown.css.
  const { ref: actionBarRef, offset: chromeOffset } = useStickyChromeOffset();
  const [showPublishDialog, setShowPublishDialog] = useState(false);
  const [showCoverDialog, setShowCoverDialog] = useState(false);
  const [view, setView] = useState<View>("edit");
  const [isSwitchingView, setIsSwitchingView] = useState(false);

  // Same rule the backend applies: a `full_edit` contributor on the project,
  // or the author of an author-owned article.
  const canEdit = useMemo(() => {
    if (!user) return false;
    if (!project) return initialArticle.author?.id === user.id;
    return project.contributors.some(
      (c) => c.user.id === user.id && c.full_edit,
    );
  }, [project, initialArticle.author, user]);

  if (authLoading || draft.isLoading) {
    return <ArticleAuthoringSkeleton />;
  }

  if (!canEdit) {
    return (
      <div className="max-w-2xl mx-auto py-12 px-4 text-center">
        <h1 className="text-lg font-semibold text-foreground">{t("notAllowed.title")}</h1>
        <p className="text-sm text-muted-foreground mt-2">
          {project ? t("notAllowed.body") : t("notAllowed.bodyOwn")}
        </p>
        <div className="mt-6">
          <Link
            href={containerHref}
            className="text-sm text-accent hover:text-accent-hover"
          >
            {backToContainer}
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
          {t("openFailed.title")}
        </h1>
        <p className="text-sm text-muted-foreground mt-2" role="alert">
          {draft.error || t("openFailed.fallback")}
        </p>
        <div className="mt-6">
          <Link
            href={containerHref}
            className="text-sm text-accent hover:text-accent-hover"
          >
            {backToContainer}
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
  const mode = draft.isPublished ? t("modeEditArticle") : t("modeEditDraft");

  const handleDeleteClick = async () => {
    if (!window.confirm(t("confirmDelete"))) return;
    await draft.remove();
  };

  // The preview renders the saved article — the derived summary only exists
  // server-side, and the body lives in the editor until a save — so switching
  // to it saves first. On failure the view stays put, and draft.error already
  // says why.
  const handleViewClick = async (next: View) => {
    if (next === view) return;
    if (next === "edit") {
      setView(next);
      return;
    }
    setIsSwitchingView(true);
    const saved = await draft.save();
    setIsSwitchingView(false);
    if (saved) setView("preview");
  };

  const container = project
    ? projectContainer(project)
    : article.author
      ? authorContainer(article.author)
      : null;

  return (
    <>
      <div
        ref={actionBarRef}
        className="sticky top-14 z-30 bg-white border-b border-border"
      >
        <div className="max-w-4xl mx-auto px-4 sm:px-6 flex items-center justify-between py-2">
          <div className="text-sm text-muted-foreground">
            {project ? (
              <Link
                href={`/my-projects/${project.id}#articles`}
                className="hover:text-foreground"
              >
                {project.title}
              </Link>
            ) : (
              <Link href={containerHref} className="hover:text-foreground">
                {t("yourProfile")}
              </Link>
            )}
            <span className="mx-2">/</span>
            <span className="text-foreground font-medium">{mode}</span>
          </div>
          <div
            role="group"
            aria-label={t("view.label")}
            className="inline-flex rounded-lg border border-border bg-muted p-0.5"
          >
            {VIEWS.map((key) => (
              <button
                key={key}
                type="button"
                aria-pressed={view === key}
                disabled={isSwitchingView}
                onClick={() => handleViewClick(key)}
                className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1 text-sm transition-colors ${
                  view === key
                    ? "bg-white font-medium text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {key === "edit" ? (
                  <PencilIcon className="w-4 h-4" />
                ) : isSwitchingView ? (
                  <ArrowPathIcon className="w-4 h-4 animate-spin" />
                ) : (
                  <EyeIcon className="w-4 h-4" />
                )}
                {viewLabels[key]}
              </button>
            ))}
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
                tc("save")
              ) : (
                t("saveDraft")
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
                  tc("publish")
                )}
              </button>
            )}
            <button
              onClick={handleDeleteClick}
              disabled={draft.isDeleting}
              title={t("deleteArticle")}
              className="p-2 rounded-lg text-muted-foreground border border-border hover:bg-red-50 hover:text-red-600 hover:border-red-200 transition-colors"
            >
              <TrashIcon className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Mounted, not unmounted, when previewing: MDXEditor holds the body
          uncontrolled, and remounting it on every switch would lose the cursor
          and re-run its plugin setup. */}
      <div
        className={`max-w-4xl mx-auto px-4 sm:px-6 py-6 space-y-4 ${
          view === "edit" ? "" : "hidden"
        }`}
        style={
          { "--article-chrome-offset": `${chromeOffset}px` } as CSSProperties
        }
      >
        <div className="grid grid-cols-1 sm:grid-cols-[1fr_auto] gap-3 sm:items-center">
          <input
            type="text"
            value={form.title}
            onChange={(e) => draft.updateForm({ title: e.target.value })}
            placeholder={t("titlePlaceholder")}
            className="w-full rounded-lg border border-border bg-white px-3.5 py-2.5 text-lg font-semibold text-foreground placeholder:text-[#94a3b8] focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/12 transition-[border-color,box-shadow]"
          />
          {project && (
            <ChannelDropdown
              channels={draft.channels}
              value={form.channel_id}
              onChange={(value) => draft.updateForm({ channel_id: value })}
            />
          )}
        </div>

        {/* The standfirst sits under the title on the page, in the email and
            on cards, so it is edited under the title here too. */}
        <div>
          <label htmlFor="article-summary" className="sr-only">
            {t("summary.label")}
          </label>
          <textarea
            id="article-summary"
            value={form.summary}
            placeholder={article.summary_display || t("summary.placeholder")}
            maxLength={SUMMARY_MAX}
            rows={2}
            onChange={(e) => draft.updateForm({ summary: e.target.value })}
            className="w-full rounded-lg border border-border bg-white px-3.5 py-2 text-base text-muted-foreground placeholder:text-[#94a3b8] focus:outline-none focus:border-accent focus:ring-[3px] focus:ring-accent/12 transition-[border-color,box-shadow]"
          />
          <div className="mt-1 flex items-center justify-between text-xs text-muted-foreground">
            <span>{t("summary.hint")}</span>
            <span>
              {t("summary.count", { count: form.summary.length, max: SUMMARY_MAX })}
            </span>
          </div>
        </div>

        <CoverSlot
          imageUrl={
            draft.cover
              ? (pickVariant(draft.cover.variants, "medium") ?? draft.cover.url)
              : null
          }
          crop={form.listing_crop}
          onPick={() => setShowCoverDialog(true)}
          onRemove={draft.removeCover}
        />
        <ArticleEditor
          articleId={article.id}
          initialMarkdown={article.body}
          onChange={draft.handleBodyChange}
        />
      </div>

      {view === "preview" && container && (
        <div className="py-6">
          <ArticlePreview article={article} container={container} />
        </div>
      )}

      {showPublishDialog && (
        <PublishDialog
          destination={project ? "project" : "profile"}
          onClose={() => setShowPublishDialog(false)}
          onConfirm={() => {
            setShowPublishDialog(false);
            draft.publish();
          }}
          isPublishing={draft.isPublishing}
        />
      )}

      {showCoverDialog && (
        <ListingImageDialog
          articleId={article.id}
          images={draft.images}
          currentImageId={form.listing_image_id}
          currentCrop={form.listing_crop}
          onConfirm={(image, crop) => {
            draft.chooseCover(image, crop);
            setShowCoverDialog(false);
          }}
          onRemove={() => {
            draft.removeCover();
            setShowCoverDialog(false);
          }}
          onClose={() => setShowCoverDialog(false)}
        />
      )}
    </>
  );
}
