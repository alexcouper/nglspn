type CompetitionStatus = "pending" | "accepting_applications" | "voting" | "closed";

interface CompetitionStatusBadgeProps {
  status: CompetitionStatus;
  className?: string;
}

export function CompetitionStatusBadge({ status, className = "" }: CompetitionStatusBadgeProps) {
  switch (status) {
    case "accepting_applications":
      return (
        <span className={`badge badge-success ${className}`}>
          <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full mr-1.5 pulse-dot inline-block" />
          Open
        </span>
      );
    case "voting":
      return (
        <span className={`badge bg-violet-500 text-white ${className}`}>
          <span className="w-1.5 h-1.5 bg-white rounded-full mr-1.5 pulse-dot inline-block" />
          Voting
        </span>
      );
    case "closed":
      return (
        <span className={`badge bg-slate-800/80 backdrop-blur-sm text-white ${className}`}>
          Completed
        </span>
      );
    default:
      return null;
  }
}
