import Link from "next/link";
import { useTranslations } from "next-intl";
import type { Project } from "@/lib/api";
import { getAuthorName } from "@/lib/utils";

interface CreatorCreditProps {
  project: Project;
}

export function CreatorCredit({ project }: CreatorCreditProps) {
  const t = useTranslations("projects.creatorCredit");
  const displayOwners = project.contributors.filter(
    (c) => c.role === "owner" && c.full_edit && !c.user.is_system_user
  );
  const creatorIsOwner = displayOwners.some(
    (c) => c.user.id === project.creator.id
  );
  const creatorName = getAuthorName(project.creator);

  return (
    <p
      className="text-xs text-muted-foreground"
      data-testid="creator-credit"
    >
      {t.rich(creatorIsOwner ? "createdBy" : "tippedOffBy", {
        name: creatorName,
        link: (chunks) => (
          <Link
            href={`/users/${project.creator.id}`}
            className="text-foreground hover:text-accent transition-colors"
          >
            {chunks}
          </Link>
        ),
      })}
    </p>
  );
}
