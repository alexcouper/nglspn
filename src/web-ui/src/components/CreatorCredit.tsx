import Link from "next/link";
import type { Project } from "@/lib/api";
import { getAuthorName } from "@/lib/utils";

interface CreatorCreditProps {
  project: Project;
}

export function CreatorCredit({ project }: CreatorCreditProps) {
  const displayOwners = project.contributors.filter(
    (c) => c.role === "owner" && c.full_edit && !c.user.is_system_user
  );
  const creatorIsOwner = displayOwners.some(
    (c) => c.user.id === project.creator.id
  );
  const label = creatorIsOwner ? "Created by" : "Suggested by";
  const creatorName = getAuthorName(project.creator);

  return (
    <p
      className="text-xs text-muted-foreground"
      data-testid="creator-credit"
    >
      {label}{" "}
      <Link
        href={`/users/${project.creator.id}`}
        className="text-foreground hover:text-accent transition-colors"
      >
        {creatorName}
      </Link>
    </p>
  );
}
