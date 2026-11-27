import type { CompetitionSummary, CompetitionWinnerRef, FrontPageArticle } from "@/lib/api";
import { getCompetitionDeadline } from "@/lib/competition-dates";

export const SPOTLIGHT_SIZE = 3;

export type CompetitionSlot =
  | { state: "voting"; competition: CompetitionSummary; daysLeft: number }
  | { state: "accepting"; competition: CompetitionSummary; daysLeft: number }
  | { state: "closed"; competition: CompetitionSummary; winner: CompetitionWinnerRef };

export interface DiscoverTop {
  lead: FrontPageArticle | null;
  second: FrontPageArticle | null;
  slot: CompetitionSlot | null;
  spotlight: FrontPageArticle[];
}

interface Input {
  // Null where the fetch failed; the part that depends on it is left out.
  recent: FrontPageArticle[] | null;
  spotlight: FrontPageArticle[] | null;
  competitions: CompetitionSummary[] | null;
  today: Date;
}

export function selectDiscoverTop({ recent, spotlight, competitions, today }: Input): DiscoverTop {
  const [lead = null, second = null] = recent ?? [];
  const shown = new Set([lead?.id, second?.id]);

  return {
    lead,
    second,
    slot: selectSlot(competitions ?? [], dateKey(today)),
    spotlight: (spotlight ?? []).filter((a) => !shown.has(a.id)).slice(0, SPOTLIGHT_SIZE),
  };
}

// Voting comes first: the next round opens the day the previous one closes,
// so an open round is nearly always there and would hide voting entirely.
function selectSlot(competitions: CompetitionSummary[], today: string): CompetitionSlot | null {
  const inVoting = competitions.find(
    (c) => c.status === "voting" && deadlineOf(c) >= today,
  );
  if (inVoting) {
    return { state: "voting", competition: inVoting, daysLeft: daysBetween(today, deadlineOf(inVoting)) };
  }

  const accepting = competitions.find((c) => c.status === "accepting_applications");
  if (accepting) {
    return { state: "accepting", competition: accepting, daysLeft: daysBetween(today, deadlineOf(accepting)) };
  }

  const lastClosed = competitions.find((c) => c.status === "closed");
  if (lastClosed?.winner) {
    return { state: "closed", competition: lastClosed, winner: lastClosed.winner };
  }
  return null;
}

function deadlineOf(competition: CompetitionSummary): string {
  return getCompetitionDeadline(
    competition.status,
    competition.submission_deadline,
    competition.voting_end_date,
  ).slice(0, 10);
}

// Calendar dates as YYYY-MM-DD in UTC, which is Iceland's time zone all year.
function dateKey(date: Date): string {
  return date.toISOString().slice(0, 10);
}

const DAY_MS = 24 * 60 * 60 * 1000;

function daysBetween(from: string, to: string): number {
  return Math.max(0, Math.round((Date.parse(to) - Date.parse(from)) / DAY_MS));
}
