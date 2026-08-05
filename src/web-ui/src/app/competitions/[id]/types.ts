import type { ReviewCompetitionDetailResponse, ReviewProject } from "@/lib/api";

export type ReviewState =
  | { kind: "loading" }
  | { kind: "logged-out" }
  | { kind: "not-assigned" }
  | { kind: "error"; message: string }
  | {
      kind: "ready";
      data: ReviewCompetitionDetailResponse;
      // Both orders come from the server: `ranked` in saved position order,
      // `pool` in this reviewer's stable order. Never re-derived here.
      ranked: ReviewProject[];
      pool: ReviewProject[];
    };
