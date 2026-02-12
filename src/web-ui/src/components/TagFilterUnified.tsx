"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import type { TagGrouped } from "@/lib/api";

interface TagData {
  id: string;
  name: string;
  slug: string;
  color: string | null;
  category_id?: string | null;
  category_slug?: string | null;
}

interface CategoryData {
  id: string;
  name: string;
  slug: string;
}

interface GroupedTagData {
  category: CategoryData;
  tags: TagData[];
}

// Common props for both modes
interface BaseTagFilterProps {
  multiSelect?: boolean;
  useUrlParams?: boolean;
  onFilterChange?: (selected: string[]) => void;
}

// API mode props - fetches tags from API
interface ApiModeProps extends BaseTagFilterProps {
  mode: "api";
  withProjects?: boolean;
  competitionId?: string;
}

// Local mode props - uses provided data
interface LocalModeProps extends BaseTagFilterProps {
  mode: "local";
  tags: TagData[];
  categories?: CategoryData[];
  selectedIds?: string[];
}

export type TagFilterUnifiedProps = ApiModeProps | LocalModeProps;

export function TagFilterUnified(props: TagFilterUnifiedProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [groupedTags, setGroupedTags] = useState<GroupedTagData[]>([]);
  const [isLoading, setIsLoading] = useState(props.mode === "api");
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set()
  );

  const multiSelect = props.multiSelect ?? true;
  const useUrlParams = props.useUrlParams ?? props.mode === "api";

  // Get selected tags from URL
  const tagsParam = searchParams.get("tags");
  const selectedFromUrl = useMemo(
    () => tagsParam?.split(",").filter(Boolean) || [],
    [tagsParam]
  );

  // Get selected IDs from props (for local mode)
  const propsSelectedIds = props.mode === "local" ? props.selectedIds : undefined;

  // Determine the selected IDs based on mode
  const selectedIds = useMemo(() => {
    if (props.mode === "api") {
      // In API mode, we use slugs from URL
      return selectedFromUrl;
    }
    // In local mode, use selectedIds from props
    return propsSelectedIds || [];
  }, [props.mode, selectedFromUrl, propsSelectedIds]);

  // For API mode, track slugs separately for matching
  const selectedSlugs = props.mode === "api" ? selectedFromUrl : [];

  // For local mode, group tags by category
  const localGroupedTags = useMemo(() => {
    if (props.mode !== "local") return [];

    const { tags, categories } = props;
    const groups: Map<string, { category: CategoryData | null; tags: TagData[] }> = new Map();
    const categoryMap = new Map<string, CategoryData>();
    categories?.forEach((cat) => categoryMap.set(cat.id, cat));

    for (const tag of tags) {
      const catId = tag.category_id || "uncategorized";
      if (!groups.has(catId)) {
        const category = tag.category_id ? categoryMap.get(tag.category_id) || null : null;
        groups.set(catId, { category, tags: [] });
      }
      groups.get(catId)!.tags.push(tag);
    }

    // Sort tags within each group
    for (const group of groups.values()) {
      group.tags.sort((a, b) => a.name.localeCompare(b.name));
    }

    // Convert to array and sort by category name
    return Array.from(groups.entries())
      .map(([id, data]) => ({
        category: data.category || { id, name: "Other", slug: "other" },
        tags: data.tags,
      }))
      .sort((a, b) => {
        if (a.category.slug === "other") return 1;
        if (b.category.slug === "other") return -1;
        return a.category.name.localeCompare(b.category.name);
      });
  }, [props]);

  // Load tags from API if in API mode
  const loadTags = useCallback(async () => {
    if (props.mode !== "api") return;

    try {
      const data = await api.tags.listGrouped({
        withProjects: props.withProjects ?? true,
      });

      // Transform API response to our format
      const transformed: GroupedTagData[] = data.map((group: TagGrouped) => ({
        category: {
          id: group.category.id,
          name: group.category.name,
          slug: group.category.slug,
        },
        tags: group.tags.map((tag) => ({
          id: tag.id,
          name: tag.name,
          slug: tag.slug,
          color: tag.color,
          category_id: tag.category_id,
          category_slug: tag.category_slug,
        })),
      }));

      setGroupedTags(transformed);

      // Auto-expand categories that have selected tags
      const categoriesWithSelection = new Set<string>();
      transformed.forEach((group) => {
        if (group.tags.some((tag) => selectedSlugs.includes(tag.slug))) {
          categoriesWithSelection.add(group.category.id);
        }
      });
      if (categoriesWithSelection.size > 0) {
        setExpandedCategories(categoriesWithSelection);
      }
    } catch {
      // Silently fail - tags are optional
    } finally {
      setIsLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.mode]);

  useEffect(() => {
    if (props.mode === "api") {
      loadTags();
    }
  }, [loadTags, props.mode]);

  // Use local or API grouped tags
  const displayGroups = props.mode === "local" ? localGroupedTags : groupedTags;

  const toggleTag = (tag: TagData) => {
    const identifier = props.mode === "api" ? tag.slug : tag.id;

    let newSelected: string[];
    if (multiSelect) {
      newSelected = selectedIds.includes(identifier)
        ? selectedIds.filter((s) => s !== identifier)
        : [...selectedIds, identifier];
    } else {
      // Single select - toggle off if same, otherwise select new
      newSelected = selectedIds.includes(identifier) ? [] : [identifier];
    }

    if (useUrlParams) {
      updateURL(newSelected);
    }
    props.onFilterChange?.(newSelected);
  };

  const updateURL = (tags: string[]) => {
    const params = new URLSearchParams(searchParams.toString());
    if (tags.length > 0) {
      params.set("tags", tags.join(","));
    } else {
      params.delete("tags");
    }
    router.push(`?${params.toString()}`, { scroll: false });
  };

  const toggleCategory = (categoryId: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(categoryId)) {
        next.delete(categoryId);
      } else {
        next.add(categoryId);
      }
      return next;
    });
  };

  const clearAll = () => {
    if (useUrlParams) {
      updateURL([]);
    }
    props.onFilterChange?.([]);
  };

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-8 bg-muted rounded-lg" />
        ))}
      </div>
    );
  }

  if (displayGroups.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-foreground">Filter by Tag</h3>
        {selectedIds.length > 0 && (
          <button
            onClick={clearAll}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            Clear {multiSelect ? "all" : "filter"}
          </button>
        )}
      </div>

      {displayGroups.map((group) => {
        const isExpanded = expandedCategories.has(group.category.id);
        const identifier = props.mode === "api" ? "slug" : "id";
        const selectedInCategory = group.tags.filter((tag) =>
          selectedIds.includes(tag[identifier])
        ).length;

        return (
          <div
            key={group.category.id}
            className="border border-border rounded-xl overflow-hidden"
          >
            <button
              onClick={() => toggleCategory(group.category.id)}
              className="w-full flex items-center justify-between px-3 py-2 bg-muted hover:bg-muted/80 transition-colors text-left"
            >
              <span className="text-sm font-medium text-foreground">
                {group.category.name}
                {selectedInCategory > 0 && (
                  <span className="ml-1.5 inline-flex items-center justify-center w-5 h-5 text-xs bg-accent text-white rounded-full">
                    {selectedInCategory}
                  </span>
                )}
              </span>
              <svg
                className={`w-4 h-4 text-muted-foreground transition-transform ${
                  isExpanded ? "rotate-180" : ""
                }`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </button>

            {isExpanded && (
              <div className="px-3 py-2 flex flex-wrap gap-1.5">
                {group.tags.map((tag) => {
                  const tagIdentifier = props.mode === "api" ? tag.slug : tag.id;
                  const isSelected = selectedIds.includes(tagIdentifier);

                  return (
                    <button
                      key={tag.id}
                      onClick={() => toggleTag(tag)}
                      className={`px-2.5 py-1 rounded-full text-xs font-medium transition-all ${
                        isSelected
                          ? "bg-accent text-white"
                          : "bg-accent-subtle text-accent hover:bg-accent/15"
                      }`}
                    >
                      {tag.name}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
