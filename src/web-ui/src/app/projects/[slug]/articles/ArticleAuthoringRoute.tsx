"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Project } from "@/lib/api";
import { describeApiError } from "@/lib/api/errors";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { ArticleAuthoringPage } from "./ArticleAuthoringPage";
import { ArticleAuthoringSkeleton } from "./ArticleAuthoringSkeleton";

interface Props {
  // A slug or a UUID — `MyProjectArticles` routes with `project.slug ?? project.id`
  // and `GET /api/projects/{identifier}` takes either.
  projectRef: string;
  // Always an existing article: the New article button creates the draft before
  // routing here, so this wrapper only ever serves the /edit route.
  articleId: string;
}

// Loads the project client-side so the request carries the bearer token.
// The route page above this is a server component, and no server component
// here can authenticate — the token is in localStorage — so a server fetch
// always looks anonymous to the backend, which 404s any project that is not
// APPROVED. That is why authoring used to be unreachable on a project still in
// review. Everything below this line already authenticates its own calls.
export function ArticleAuthoringRoute({ projectRef, articleId }: Props) {
  const { isReady } = useRequireAuth();
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState("");

  // The editor is by far the largest thing on this route — the bundle budget
  // gives it 400 kB against 40 kB for everything else. next/dynamic only starts
  // its import when the component first renders, and ArticleAuthoringPage does
  // not render until the project below has landed, so the biggest download
  // would otherwise queue behind a round trip it does not depend on. Warmed
  // here it downloads alongside the project. Same specifier as the dynamic()
  // in ArticleAuthoringPage, so this is the same chunk, not a second copy.
  // `isReady` is read from the stored token, not the network, so gating on it
  // costs nothing and spares a visitor on their way to /login the 400 kB.
  useEffect(() => {
    if (!isReady) return;
    void import("./ArticleEditor");
  }, [isReady]);

  useEffect(() => {
    // Not signed in: useRequireAuth is already routing to /login. Requesting
    // the project first would only show a "not found" on the way out — the same
    // dead end this change exists to remove.
    if (!isReady) return;

    let cancelled = false;
    api.projects
      .get(projectRef)
      .then((loaded) => {
        if (!cancelled) setProject(loaded);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(describeApiError(err, "Couldn't open this project."));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [projectRef, isReady]);

  if (error) {
    return (
      <div className="max-w-2xl mx-auto py-12 px-4 text-center">
        <h1 className="text-lg font-semibold text-foreground">
          Couldn&apos;t open this project
        </h1>
        <p className="text-sm text-muted-foreground mt-2" role="alert">
          {error}
        </p>
        <div className="mt-6">
          <Link
            href="/my-projects"
            className="text-sm text-accent hover:text-accent-hover"
          >
            Back to my projects
          </Link>
        </div>
      </div>
    );
  }

  if (!project) {
    return <ArticleAuthoringSkeleton />;
  }

  return <ArticleAuthoringPage project={project} articleId={articleId} />;
}
