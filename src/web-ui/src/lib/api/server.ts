import "server-only";

import type {
  CategoryItem,
  Competition,
  CompetitionHighlightsResponse,
  CompetitionOverviewListResponse,
  DiscoverProject,
  Project,
  ProjectListResponse,
  WinnerProject,
} from "./index";

const API_URL =
  process.env.API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

export class ApiNotFoundError extends Error {
  constructor(path: string) {
    super(`Not found: ${path}`);
    this.name = "ApiNotFoundError";
  }
}

async function serverFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    if (res.status === 404) throw new ApiNotFoundError(path);
    throw new Error(`API error: ${res.status}`);
  }
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
  return serverFetch<ProjectListResponse>(path);
}

export async function fetchProject(id: string): Promise<Project> {
  return serverFetch<Project>(`/api/projects/${id}`);
}

export async function fetchCompetitions(): Promise<CompetitionOverviewListResponse> {
  return serverFetch<CompetitionOverviewListResponse>("/api/competitions");
}

export async function fetchCompetition(
  idOrSlug: string
): Promise<Competition> {
  return serverFetch<Competition>(`/api/competitions/${idOrSlug}`);
}

export async function fetchCompetitionHighlights(): Promise<CompetitionHighlightsResponse> {
  return serverFetch<CompetitionHighlightsResponse>(
    "/api/competitions/highlights"
  );
}

export async function fetchCategories(): Promise<CategoryItem[]> {
  return serverFetch<CategoryItem[]>("/api/projects/categories");
}

export async function fetchFeaturedProjects(): Promise<DiscoverProject[]> {
  return serverFetch<DiscoverProject[]>("/api/projects/featured");
}

export async function fetchNewArrivals(): Promise<DiscoverProject[]> {
  return serverFetch<DiscoverProject[]>("/api/projects/new-arrivals");
}

export async function fetchRecentTipoffs(): Promise<DiscoverProject[]> {
  return serverFetch<DiscoverProject[]>("/api/projects/recent-tipoffs");
}

export async function fetchWinners(): Promise<WinnerProject[]> {
  return serverFetch<WinnerProject[]>("/api/projects/winners");
}

export async function fetchMostDiscussed(): Promise<DiscoverProject[]> {
  return serverFetch<DiscoverProject[]>("/api/projects/most-discussed");
}
