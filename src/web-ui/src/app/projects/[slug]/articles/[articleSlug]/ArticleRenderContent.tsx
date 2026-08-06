"use client";

import { useEffect } from "react";
import Link from "next/link";
import { ChevronLeftIcon } from "@heroicons/react/24/outline";
import ReactMarkdown from "react-markdown";
import rehypePrismPlus from "rehype-prism-plus";
import rehypeRaw from "rehype-raw";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import { articleSanitizeSchema } from "../sanitize-schema";
import "../article-markdown.css";
import { useAuth } from "@/contexts/auth";
import type { Article, Project } from "@/lib/api";
import { api } from "@/lib/api";
import { formatDate, getAuthorName } from "@/lib/utils";

interface Props {
  project: Project;
  article: Article;
}

export function ArticleRenderContent({ project, article }: Props) {
  const { isAuthenticated } = useAuth();

  const publishedAt = article.published_at
    ? new Date(article.published_at)
    : null;
  const isDraft = article.state !== "published";

  const projectSlug = project.slug ?? project.id;

  useEffect(() => {
    if (!isAuthenticated) return;
    api.notifications.markArticleThread(article.id).catch(() => {
      // Best-effort; the bell will eventually reconcile from the server.
    });
  }, [article.id, isAuthenticated]);

  return (
    <article className="sm:py-8 sm:px-6">
      {/*
        Breadcrumb sits above the panel so the article body itself opens with
        its title. On mobile (< sm) the panel is full-bleed and the breadcrumb
        needs `px-4` to align with the panel's inner content padding; on
        desktop it picks up the panel's `sm:px-10` content alignment.
      */}
      <div className="max-w-3xl mx-auto px-4 pt-4 pb-3 sm:px-10 sm:pt-0 sm:pb-4">
        <Link
          href={`/projects/${projectSlug}#articles`}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ChevronLeftIcon className="w-4 h-4" />
          {project.title}
        </Link>
      </div>

      {/*
        Mobile (< sm): full-bleed — no rounded corners, no border, no outer
        padding. Article fills viewport edge-to-edge.
        Desktop (>= sm): centered panel, rounded, bordered, padded — the
        article is the only on-page surface besides the nav bar.
      */}
      <div className="max-w-3xl mx-auto bg-white sm:rounded-xl sm:border sm:border-border px-4 py-6 sm:px-10 sm:py-10">
        {isDraft && (
          <div className="mb-4 inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full bg-amber-50 border border-amber-200 text-amber-800 text-xs font-medium">
            Draft — visible only to the author and project editors
          </div>
        )}

        <h1 className="text-3xl sm:text-4xl font-semibold text-foreground tracking-tight">
          {article.title}
        </h1>

        <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
          {publishedAt && (
            <time dateTime={publishedAt.toISOString()}>
              {formatDate(publishedAt)}
            </time>
          )}
          {article.author && !article.author.is_system_user && (
            <span>
              by{" "}
              <Link
                href={`/users/${article.author.id}`}
                className="text-foreground hover:text-accent transition-colors"
              >
                {getAuthorName(article.author)}
              </Link>
            </span>
          )}
          <span className="font-semibold uppercase tracking-wide text-accent text-xs">
            {article.channel.name}
          </span>
        </div>

        {/* No image band above the body. The listing image describes the
            article in a list; an author who wants an image at the top of the
            piece inserts one into the body. */}
        <div className="markdown markdown-article mt-8">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            // Plugin order matters: rehypeRaw first to turn HTML strings into
            // hast nodes; rehypePrismPlus second so it can syntax-highlight
            // fenced code blocks into <span class="token …"> tokens;
            // rehypeSanitize last to strip anything outside the allowlist
            // (which now permits className on pre/code/span so Prism's
            // output survives).
            rehypePlugins={[
              rehypeRaw,
              [rehypePrismPlus, { ignoreMissing: true }],
              [rehypeSanitize, articleSanitizeSchema],
            ]}
            components={{
              table: ({ children }) => (
                <div className="my-6 overflow-x-auto">
                  <table className="w-full text-sm border border-border rounded-lg overflow-hidden border-collapse">
                    {children}
                  </table>
                </div>
              ),
              thead: ({ children }) => (
                <thead className="bg-muted">{children}</thead>
              ),
              tr: ({ children }) => (
                <tr className="border-b border-border last:border-b-0">
                  {children}
                </tr>
              ),
              th: ({ children }) => (
                <th className="px-3.5 py-2.5 text-left font-semibold text-foreground align-top">
                  {children}
                </th>
              ),
              td: ({ children }) => (
                <td className="px-3.5 py-2.5 text-left align-top">
                  {children}
                </td>
              ),
            }}
          >
            {article.body}
          </ReactMarkdown>
        </div>
      </div>
    </article>
  );
}
