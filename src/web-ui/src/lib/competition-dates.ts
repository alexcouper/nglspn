/**
 * Returns the relevant deadline date string based on competition status.
 * - accepting_applications: submission_deadline
 * - voting/closed: voting_end_date, falling back to submission_deadline
 */
export function getCompetitionDeadline(
  status: string,
  submissionDeadline: string,
  votingEndDate: string | null | undefined
): string {
  if (status === "accepting_applications") {
    return submissionDeadline;
  }
  return votingEndDate ?? submissionDeadline;
}
