import type { Article, Project, PublicUserProfile } from "@/lib/api";
import { getAuthorName } from "@/lib/utils";

// Where an article lives: on a project, or under its author's own name. The
// render page, its onward footer and the back control all take one of these
// rather than a Project, so the two route files can share them.
export type Container =
  | { kind: "project"; project: Project }
  | { kind: "author"; author: PublicUserProfile };

export function projectContainer(project: Project): Container {
  return { kind: "project", project };
}

export function authorContainer(author: PublicUserProfile): Container {
  return { kind: "author", author };
}

/** The page the container itself is read on. */
export function containerHref(container: Container): string {
  if (container.kind === "project") {
    const { project } = container;
    return `/projects/${project.slug ?? project.id}`;
  }
  return `/users/${container.author.id}`;
}

/** The anchor on that page where its articles are listed. */
export function containerArticlesHref(container: Container): string {
  return container.kind === "project"
    ? `${containerHref(container)}#articles`
    : `${containerHref(container)}#profile-articles`;
}

/** What the container is called where a flag or heading names it. */
export function containerTitle(container: Container): string {
  return container.kind === "project"
    ? container.project.title
    : getAuthorName(container.author);
}

/** The public URL of an article with `slug` in this container. */
export function articleHref(container: Container, slug: string): string {
  return `${containerHref(container)}/articles/${slug}`;
}

/** The public URL of a loaded article, or null while it has no slug. */
export function articleHrefOf(article: Article): string | null {
  if (!article.slug) return null;
  if (article.project) {
    return `/projects/${article.project.slug ?? article.project.id}/articles/${article.slug}`;
  }
  if (article.author) return `/users/${article.author.id}/articles/${article.slug}`;
  return null;
}
