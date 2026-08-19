import Link from "next/link";
import type { CategoryItem } from "@/lib/api";

// Shared chrome rather than part of the projects page: /latest and /projects are
// peer views of the same place, so they render the identical bar and moving
// between them costs one click.
export type ListingTab = { kind: "latest" } | { kind: "discover" } | { kind: "category"; slug: string };

interface ListingTabsProps {
  categories: CategoryItem[];
  active: ListingTab;
}

export function ListingTabs({ categories, active }: ListingTabsProps) {
  const withProjects = categories.filter((c) => c.project_count > 0);

  return (
    <div className="sticky top-14 z-10 bg-white border-b border-border">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 flex items-center gap-6">
        <nav
          className="flex gap-6 overflow-x-auto scrollbar-hide flex-1"
          aria-label="Section tabs"
        >
          <TabLink href="/latest" active={active.kind === "latest"} label="Latest" />
          <TabLink
            href="/projects"
            active={active.kind === "discover"}
            label="Discover"
          />
          {withProjects.map((cat) => (
            <TabLink
              key={cat.id}
              href={`/projects?category=${cat.slug}`}
              active={active.kind === "category" && active.slug === cat.slug}
              label={cat.name}
            />
          ))}
        </nav>
        <Link
          href="/create"
          className="hidden sm:inline-block shrink-0 text-sm font-medium bg-accent hover:bg-accent-hover text-white px-3.5 py-1.5 rounded-md transition-colors duration-150"
        >
          Create a project
        </Link>
      </div>
    </div>
  );
}

function TabLink({
  href,
  active,
  label,
}: {
  href: string;
  active: boolean;
  label: string;
}) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`whitespace-nowrap py-3 text-sm font-medium border-b-2 transition-colors ${
        active
          ? "border-accent text-accent"
          : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
      }`}
    >
      {label}
    </Link>
  );
}
