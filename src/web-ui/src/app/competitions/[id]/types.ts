import type { ReviewCompetitionDetailResponse, ReviewProject } from "@/lib/api";

export type ReviewState =
  | { kind: "loading" }
  | { kind: "logged-out" }
  | { kind: "not-assigned" }
  | { kind: "error"; message: string }
  | {
      kind: "ready";
      data: ReviewCompetitionDetailResponse;
      projects: ReviewProject[];
    };
