import "server-only";

import type {
  ActiveOrRecentResponse,
  Competition,
  CompetitionOverviewListResponse,
  Project,
  ProjectListResponse,
} from "./index";

const API_URL =
  process.env.API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

async function serverFetch<T>(
  path: string,
  options?: { tags?: string[] }
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    next: { tags: options?.tags },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchProjects(params?: {
  sort_by?: string;
  sort_order?: string;
}): Promise<ProjectListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.sort_by) searchParams.set("sort_by", params.sort_by);
  if (params?.sort_order) searchParams.set("sort_order", params.sort_order);
  const query = searchParams.toString();
  const path = query ? `/api/projects?${query}` : "/api/projects";
  return serverFetch<ProjectListResponse>(path, { tags: ["projects"] });
}

export async function fetchProject(id: string): Promise<Project> {
  return serverFetch<Project>(`/api/projects/${id}`, {
    tags: ["projects", `project-${id}`],
  });
}

export async function fetchCompetitions(): Promise<CompetitionOverviewListResponse> {
  return serverFetch<CompetitionOverviewListResponse>("/api/competitions", {
    tags: ["competitions"],
  });
}

export async function fetchCompetition(
  idOrSlug: string
): Promise<Competition> {
  return serverFetch<Competition>(`/api/competitions/${idOrSlug}`, {
    tags: ["competitions", `competition-${idOrSlug}`],
  });
}

export async function fetchActiveOrRecentCompetition(): Promise<ActiveOrRecentResponse> {
  return serverFetch<ActiveOrRecentResponse>(
    "/api/competitions/active-or-most-recent",
    { tags: ["competitions"] }
  );
}

export async function getAllProjectIds(): Promise<string[]> {
  try {
    const data = await fetchProjects({ sort_by: "title", sort_order: "asc" });
    return data.projects.map((p) => p.id);
  } catch {
    return [];
  }
}

export async function getAllCompetitionSlugs(): Promise<string[]> {
  try {
    const data = await fetchCompetitions();
    return data.competitions.map((c) => c.slug);
  } catch {
    return [];
  }
}
