import type { components } from "../api-types";
import type { APIClient } from "./base";

export type Competition = components["schemas"]["CompetitionResponse"];
export type CompetitionOverview =
  components["schemas"]["CompetitionOverviewResponse"];
export type CompetitionOverviewListResponse =
  components["schemas"]["CompetitionOverviewListResponse"];
export type CompetitionListResponse =
  components["schemas"]["CompetitionListResponse"];
export type CompetitionProject =
  components["schemas"]["CompetitionProjectResponse"];
export type Tag = components["schemas"]["TagResponse"];
export type CompetitionSummary =
  components["schemas"]["CompetitionSummaryResponse"];
export type ActiveOrRecentResponse =
  components["schemas"]["ActiveOrRecentResponse"];

export class CompetitionsClient {
  constructor(private client: APIClient) {}

  async list(): Promise<CompetitionOverviewListResponse> {
    return this.client.request<CompetitionOverviewListResponse>(
      "/api/competitions"
    );
  }

  async listWithProjects(): Promise<CompetitionListResponse> {
    return this.client.request<CompetitionListResponse>(
      "/api/competitions/with-projects"
    );
  }

  async get(competitionId: string): Promise<Competition> {
    return this.client.request<Competition>(
      `/api/competitions/${competitionId}`
    );
  }

  async getActiveOrRecent(): Promise<ActiveOrRecentResponse> {
    return this.client.request<ActiveOrRecentResponse>(
      "/api/competitions/active-or-most-recent"
    );
  }
}
