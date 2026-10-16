"use client";

import { useCallback, useEffect, useState, use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowPathIcon, PencilIcon, PlusIcon } from "@heroicons/react/24/outline";
import { useTranslations } from "next-intl";
import { useAuth } from "@/contexts/auth";
import {
  api,
  ApiRequestError,
  type OwnArticle,
  type UserArticle,
  type UserProfile,
  type UserProject,
} from "@/lib/api";
import { describeApiError } from "@/lib/api/errors";
import { articleBadge, sortDraftsFirst } from "@/lib/article-listing";
import { formatDate, getAuthorName } from "@/lib/utils";
import { Avatar } from "@/components/Avatar";
import { ArticleCard } from "@/components/ArticleCard";
import { ArticleListingImage } from "@/components/ArticleListingImage";
import { FollowButton } from "@/components/FollowButton";
import { ProfileAbout } from "@/components/ProfileAbout";
import { ProjectTile } from "@/components/ProjectTile";

interface PageProps {
  params: Promise<{ id: string }>;
}

// The month a person joined, as shown in the profile header's "Joined …" line.
export function joinedMonth(createdAt: string): string {
  return new Date(createdAt).toLocaleDateString("en-GB", {
    month: "long",
    year: "numeric",
  });
}

type ProfileState =
  | { kind: "loading" }
  | { kind: "not-found" }
  | { kind: "error"; message: string }
  | { kind: "loaded"; profile: UserProfile };

// A list that failed is shown as failed, never as empty: "No projects yet."
// on a 5xx would be a claim about the person that nobody made.
type ListState<T> =
  | { kind: "loading" }
  | { kind: "failed" }
  | { kind: "loaded"; items: T[] };

const LOADING = { kind: "loading" } as const;
const FAILED = { kind: "failed" } as const;

function loaded<T>(items: T[]): ListState<T> {
  return { kind: "loaded", items };
}

export default function PublicUserProfilePage({ params }: PageProps) {
  const { id } = use(params);
  // Keyed so a navigation from one profile to another remounts with fresh
  // state, rather than resetting three pieces of state inside the effect.
  return <ProfileView key={id} id={id} />;
}

export function ProfileView({ id }: { id: string }) {
  const t = useTranslations("profile.public");
  const router = useRouter();
  const { user } = useAuth();
  const [state, setState] = useState<ProfileState>({ kind: "loading" });
  const [projects, setProjects] = useState<ListState<UserProject>>(LOADING);
  const [articles, setArticles] = useState<ListState<UserArticle>>(LOADING);
  // The owner's own list, with drafts and what is held for review. Fetched in
  // place of the public one on the viewer's own page.
  const [ownArticles, setOwnArticles] = useState<ListState<OwnArticle>>(LOADING);
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState("");

  const isOwn = user?.id === id;

  // The profile first, the lists once it exists: a 404 here is the whole
  // answer, and the two list requests would only 404 again.
  useEffect(() => {
    let cancelled = false;

    api.users
      .getPublicProfile(id)
      .then((profile) => {
        if (cancelled) return;
        setState({ kind: "loaded", profile });
        api.users
          .listProjects(id)
          .then((data) => !cancelled && setProjects(loaded(data)))
          .catch(() => !cancelled && setProjects(FAILED));
        if (isOwn) {
          api.articles
            .listOwn()
            .then((data) => !cancelled && setOwnArticles(loaded(sortDraftsFirst(data))))
            .catch(() => !cancelled && setOwnArticles(FAILED));
        } else {
          api.users
            .listArticles(id)
            .then((data) => !cancelled && setArticles(loaded(data)))
            .catch(() => !cancelled && setArticles(FAILED));
        }
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiRequestError && err.status === 404) {
          setState({ kind: "not-found" });
        } else {
          setState({
            kind: "error",
            message: err instanceof Error ? err.message : t("errors.loadFailed"),
          });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [id, isOwn, t]);

  // The draft is created here rather than on a /new route, for the same reason
  // as on my-projects: images upload against an article id, so the article has
  // to exist before the editor opens.
  const handleWriteArticle = useCallback(async () => {
    if (isCreating) return;
    setIsCreating(true);
    setCreateError("");
    try {
      const created = await api.articles.createOwn();
      router.push(`/articles/edit/${created.id}`);
    } catch (err) {
      setCreateError(describeApiError(err, t("errors.createFailed")));
      setIsCreating(false);
    }
  }, [isCreating, router, t]);

  if (state.kind !== "loaded") {
    return (
      <main className="min-h-screen bg-muted pt-14">
        <section className="bg-white border-b border-border py-8 px-4 sm:px-6">
          <div className="max-w-6xl mx-auto">
            {state.kind === "loading" ? (
              <div className="flex items-center gap-5">
                <div className="skeleton h-20 w-20 rounded-full" />
                <div className="space-y-2">
                  <div className="skeleton h-7 w-48" />
                  <div className="skeleton h-4 w-64" />
                </div>
              </div>
            ) : (
              <h1 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight">
                {state.kind === "not-found" ? t("notFoundTitle") : t("errorTitle")}
              </h1>
            )}
          </div>
        </section>
        {state.kind === "error" && (
          <section className="py-8 px-4 sm:px-6">
            <div className="max-w-6xl mx-auto bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {state.message}
            </div>
          </section>
        )}
        {state.kind === "not-found" && (
          <section className="py-8 px-4 sm:px-6">
            <p className="max-w-6xl mx-auto text-sm text-muted-foreground">
              {t("notFoundHint")}
            </p>
          </section>
        )}
      </main>
    );
  }

  const { profile } = state;
  const name = getAuthorName(profile);
  const listedArticles: ListState<UserArticle | OwnArticle> = isOwn ? ownArticles : articles;
  // Mirrors CreatorCredit's "Created by" / "Tipped off by" from the project's
  // side. Spelled out rather than t(`roles.${role}`): the role comes from the
  // backend's enum and a template-literal key is not checked against the
  // messages, so a new role would render its own key path onto the tile.
  const roleLabels: Record<UserProject["role"], string> = {
    owner: t("roles.owner"),
    tipster: t("roles.tipster"),
  };
  const meta = [t("joined", { month: joinedMonth(profile.created_at) })];
  if (projects.kind === "loaded") meta.push(t("projectCount", { count: projects.items.length }));
  if (listedArticles.kind === "loaded") {
    meta.push(t("articleCount", { count: listedArticles.items.length }));
  }

  return (
    <main className="min-h-screen bg-muted pt-14">
      <section className="bg-white border-b border-border py-8 sm:py-10 px-4 sm:px-6">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 sm:gap-6">
          <div className="flex items-center gap-4 sm:gap-6 min-w-0">
            <Avatar
              src={profile.avatar_url}
              firstName={profile.first_name}
              lastName={profile.last_name}
              size={80}
            />
            <div className="min-w-0">
              <h1 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight truncate">
                {name}
              </h1>
              <p className="text-sm text-muted-foreground mt-1" data-testid="profile-meta">
                {meta.join(" · ")}
              </p>
            </div>
          </div>
          {isOwn ? (
            <div className="flex flex-col sm:flex-row gap-2">
              <button
                type="button"
                onClick={handleWriteArticle}
                disabled={isCreating}
                className="btn-primary w-full sm:w-auto inline-flex items-center justify-center gap-1.5 disabled:opacity-60"
              >
                {isCreating ? (
                  <ArrowPathIcon className="w-4 h-4 animate-spin" />
                ) : (
                  <PlusIcon className="w-4 h-4" />
                )}
                {t("writeArticle")}
              </button>
              <Link href="/profile" className="btn-secondary w-full sm:w-auto">
                <PencilIcon className="w-4 h-4" />
                {t("editProfile")}
              </Link>
            </div>
          ) : (
            <FollowButton
              target={{ kind: "user", id: profile.id }}
              initialFollowed={profile.is_followed}
              whenAnonymous="login"
            />
          )}
        </div>
      </section>

      <section className="py-8 px-4 sm:px-6">
        <div className="max-w-6xl mx-auto grid gap-6 lg:gap-8 lg:grid-cols-[320px_minmax(0,1fr)] items-start">
          <aside className="bg-white rounded-xl border border-border p-5 sm:p-6">
            <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">
              {t("about")}
            </h2>
            <ProfileAbout info={profile.info} />
          </aside>

          <div className="space-y-10 min-w-0">
            <section aria-labelledby="profile-projects">
              <SectionHeading
                id="profile-projects"
                title={t("projects")}
                count={projects.kind === "loaded" ? projects.items.length : undefined}
              />
              {projects.kind === "loading" ? (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div className="skeleton aspect-[4/3] rounded-xl" />
                  <div className="skeleton aspect-[4/3] rounded-xl" />
                  <div className="skeleton aspect-[4/3] rounded-xl hidden md:block" />
                </div>
              ) : projects.kind === "failed" ? (
                <ListError what="projects" message={t("errors.projectsFailed")} />
              ) : projects.items.length === 0 ? (
                <p className="text-sm text-muted-foreground">{t("noProjects")}</p>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4 items-start">
                  {projects.items.map((project) => (
                    <ProjectTile
                      key={project.id}
                      id={project.id}
                      href={`/projects/${project.slug ?? project.id}`}
                      imageUrl={project.main_image_thumb_url}
                      title={project.title}
                      tagline={project.tagline}
                      categoryName={project.category_name}
                      roleLabel={roleLabels[project.role]}
                    />
                  ))}
                </div>
              )}
            </section>

            <section aria-labelledby="profile-articles" id="profile-articles-section">
              <SectionHeading
                id="profile-articles"
                title={t("articles")}
                count={listedArticles.kind === "loaded" ? listedArticles.items.length : undefined}
              />
              {createError && (
                <p className="text-sm text-red-600 mb-3" role="alert">
                  {createError}
                </p>
              )}
              {listedArticles.kind === "loading" ? (
                <div className="space-y-3">
                  <div className="skeleton h-[124px] rounded-lg" />
                  <div className="skeleton h-[124px] rounded-lg" />
                </div>
              ) : listedArticles.kind === "failed" ? (
                <ListError what="articles" message={t("errors.articlesFailed")} />
              ) : listedArticles.items.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  {isOwn ? t("noArticlesOwn") : t("noArticles")}
                </p>
              ) : isOwn ? (
                <OwnArticleList articles={(listedArticles as ListState<OwnArticle> & { kind: "loaded" }).items} />
              ) : (
                <div className="space-y-3">
                  {listedArticles.items.map((article) => (
                    <ArticleCard
                      key={article.id}
                      article={article}
                      flag={article.project ? article.project.title : name}
                      showChannel={!!article.project}
                      href={publicArticleHref(article, profile.id)}
                      variant="row"
                    />
                  ))}
                </div>
              )}
            </section>
          </div>
        </div>
      </section>
    </main>
  );
}

// `what` names the list for the test id; `message` is the sentence shown.
function ListError({ what, message }: { what: string; message: string }) {
  return (
    <p
      className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm"
      role="alert"
      data-testid={`profile-${what}-error`}
    >
      {message}
    </p>
  );
}

function SectionHeading({ id, title, count }: { id: string; title: string; count?: number }) {
  return (
    <div className="flex items-baseline gap-2.5 mb-4">
      <h2 id={id} className="text-lg font-semibold text-foreground tracking-tight">
        {title}
      </h2>
      {count !== undefined && <span className="text-sm text-muted-foreground">{count}</span>}
    </div>
  );
}


// A visible article's public address: under its project, or under the author
// for one published under their own name.
function publicArticleHref(article: UserArticle, authorId: string): string | undefined {
  if (!article.slug) return undefined;
  if (article.project) {
    return article.project.slug
      ? `/projects/${article.project.slug}/articles/${article.slug}`
      : undefined;
  }
  return `/users/${authorId}/articles/${article.slug}`;
}

// The owner's list: every article they wrote, in every state, with the same
// badges the my-projects article tab shows, each row opening the editor.
function OwnArticleList({ articles }: { articles: OwnArticle[] }) {
  const t = useTranslations("profile.public");
  // Spelled out rather than t(`badge.${key}`): a template-literal key is not
  // checked against the messages.
  const badgeLabels = {
    draft: t("badge.draft"),
    published: t("badge.published"),
    pendingReview: t("badge.pendingReview"),
    notShown: t("badge.notShown"),
  } as const;

  return (
    <ul className="space-y-2" data-testid="own-articles">
      {articles.map((article) => {
        const badge = articleBadge(article);
        return (
          <li
            key={article.id}
            className="rounded-lg border border-border bg-white hover:border-accent/50 transition-colors"
          >
            <Link
              href={`/articles/edit/${article.id}`}
              className="flex items-center gap-3 px-4 py-3"
            >
              <ArticleListingImage
                src={article.listing_image_url}
                alt=""
                crop={article.listing_crop}
                className="w-20 flex-shrink-0 rounded"
              />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-base font-medium text-foreground truncate">
                    {article.title || t("untitledDraft")}
                  </span>
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full border text-xs font-medium ${badge.tone}`}
                    data-testid="article-badge"
                  >
                    {badgeLabels[badge.key]}
                  </span>
                </div>
                <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-muted-foreground">
                  <span className="font-semibold uppercase tracking-wide text-accent">
                    {article.project ? article.project.title : t("ownName")}
                  </span>
                  {article.published_at && (
                    <time dateTime={article.published_at}>
                      {formatDate(article.published_at, {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                      })}
                    </time>
                  )}
                </div>
              </div>
              <span className="text-sm text-accent">{t("edit")}</span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
