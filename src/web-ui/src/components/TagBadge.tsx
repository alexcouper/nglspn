"use client";

interface TagBadgeProps {
  name: string;
  color?: string | null;
  size?: "sm" | "md";
}

export function TagBadge({ name, size = "sm" }: TagBadgeProps) {
  const sizeClasses = {
    sm: "px-2 py-0.5 text-[11px]",
    md: "px-2.5 py-0.5 text-xs",
  };

  return (
    <span
      className={`inline-block rounded-full font-medium leading-relaxed bg-accent-subtle text-accent ${sizeClasses[size]}`}
    >
      {name}
    </span>
  );
}

interface TagGroupProps {
  categoryName: string;
  tags: Array<{ name: string; color?: string | null }>;
}

export function TagGroup({ categoryName, tags }: TagGroupProps) {
  if (tags.length === 0) return null;

  return (
    <div className="space-y-1.5">
      <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
        {categoryName}
      </span>
      <div className="flex flex-wrap gap-1">
        {tags.map((tag) => (
          <TagBadge key={tag.name} name={tag.name} />
        ))}
      </div>
    </div>
  );
}
