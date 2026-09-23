"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import { PencilIcon } from "@heroicons/react/24/outline";
import { useAuth } from "@/contexts/auth";
import {
  api,
  ApiRequestError,
  type PublicUserProfile,
  type UserArticle,
  type UserProject,
} from "@/lib/api";
import { getAuthorName } from "@/lib/utils";
import { Avatar } from "@/components/Avatar";
import { ArticleCard } from "@/components/ArticleCard";
import { ProfileAbout } from "@/components/ProfileAbout";
import { ProjectTile } from "@/components/ProjectTile";

interface PageProps {
  params: Promise<{ id: string }>;
}

// What a project's contributor role reads as on the person's own page. Mirrors
// CreatorCredit's "Created by" / "Tipped off by" from the project's side.
export const ROLE_LABELS: Record<UserProject["role"], string> = {
  owner: "Owner",
  tipster: "Tipped off",
};

export function joinedLine(createdAt: string): string {
  return `Joined ${new Date(createdAt).toLocaleDateString("en-GB", {
    month: "long",
    year: "numeric",
  })}`;
}

function plural(count: number, noun: string): string {
  return `${count} ${noun}${count === 1 ? "" : "s"}`;
}

type ProfileState =
  | { kind: "loading" }
  | { kind: "not-found" }
  | { kind: "error"; message: string }
  | { kind: "loaded"; profile: PublicUserProfile };

export default function PublicUserProfilePage({ params }: PageProps) {
  const { id } = use(params);
  // Keyed so a navigation from one profile to another remounts with fresh
  // state, rather than resetting three pieces of state inside the effect.
  return <ProfileView key={id} id={id} />;
}

export function ProfileView({ id }: { id: string }) {
  const { user } = useAuth();
  const [state, setState] = useState<ProfileState>({ kind: "loading" });
  const [projects, setProjects] = useState<UserProject[] | null>(null);
  const [articles, setArticles] = useState<UserArticle[] | null>(null);

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
          .then((data) => !cancelled && setProjects(data))
          .catch(() => !cancelled && setProjects([]));
        api.users
          .listArticles(id)
          .then((data) => !cancelled && setArticles(data))
          .catch(() => !cancelled && setArticles([]));
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiRequestError && err.status === 404) {
          setState({ kind: "not-found" });
        } else {
          setState({
            kind: "error",
            message: err instanceof Error ? err.message : "Failed to fetch profile",
          });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [id]);

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
                {state.kind === "not-found" ? "User not found" : "Profile"}
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
              There is no profile at this address.
            </p>
          </section>
        )}
      </main>
    );
  }

  const { profile } = state;
  const name = getAuthorName(profile);
  const isOwn = user?.id === profile.id;
  const meta = [joinedLine(profile.created_at)];
  if (projects) meta.push(plural(projects.length, "project"));
  if (articles) meta.push(plural(articles.length, "article"));

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
          {isOwn && (
            <Link href="/profile" className="btn-secondary w-full sm:w-auto">
              <PencilIcon className="w-4 h-4" />
              Edit profile
            </Link>
          )}
        </div>
      </section>

      <section className="py-8 px-4 sm:px-6">
        <div className="max-w-6xl mx-auto grid gap-6 lg:gap-8 lg:grid-cols-[320px_minmax(0,1fr)] items-start">
          <aside className="bg-white rounded-xl border border-border p-5 sm:p-6">
            <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">
              About
            </h2>
            <ProfileAbout info={profile.info} />
          </aside>

          <div className="space-y-10 min-w-0">
            <section aria-labelledby="profile-projects">
              <SectionHeading id="profile-projects" title="Projects" count={projects?.length} />
              {projects === null ? (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div className="skeleton aspect-[4/3] rounded-xl" />
                  <div className="skeleton aspect-[4/3] rounded-xl" />
                  <div className="skeleton aspect-[4/3] rounded-xl hidden md:block" />
                </div>
              ) : projects.length === 0 ? (
                <p className="text-sm text-muted-foreground">No projects yet.</p>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4 items-start">
                  {projects.map((project) => (
                    <ProjectTile
                      key={project.id}
                      id={project.id}
                      href={`/projects/${project.slug ?? project.id}`}
                      imageUrl={project.main_image_thumb_url}
                      title={project.title}
                      tagline={project.tagline}
                      categoryName={project.category_name}
                      roleLabel={ROLE_LABELS[project.role]}
                    />
                  ))}
                </div>
              )}
            </section>

            <section aria-labelledby="profile-articles">
              <SectionHeading id="profile-articles" title="Articles" count={articles?.length} />
              {articles === null ? (
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="skeleton aspect-[16/9] rounded-lg" />
                  <div className="skeleton aspect-[16/9] rounded-lg" />
                </div>
              ) : articles.length === 0 ? (
                <p className="text-sm text-muted-foreground">No articles yet.</p>
              ) : (
                <div className="grid gap-4 sm:grid-cols-2 items-start">
                  {articles.map((article) => (
                    <ArticleCard
                      key={article.id}
                      article={article}
                      projectTitle={article.project.title}
                      href={
                        article.project.slug && article.slug
                          ? `/projects/${article.project.slug}/articles/${article.slug}`
                          : undefined
                      }
                      variant="grid"
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
