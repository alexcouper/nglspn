"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import type { TagGrouped, TagWithCategory } from "@/lib/api";
import type { SelectedTag } from "@/components/TagSelector";

interface TagSidebarSelectorProps {
  selectedTagIds: string[];
  onChange: (tagIds: string[], tags: SelectedTag[]) => void;
}

export function TagSidebarSelector({
  selectedTagIds,
  onChange,
}: TagSidebarSelectorProps) {
  const [groupedTags, setGroupedTags] = useState<TagGrouped[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set()
  );
  const [suggestingFor, setSuggestingFor] = useState<string | null>(null);
  const [suggestName, setSuggestName] = useState("");
  const [isSuggesting, setIsSuggesting] = useState(false);

  const loadTags = useCallback(async () => {
    try {
      const data = await api.tags.listGrouped();
      setGroupedTags(data);
    } catch {
      setError("Failed to load tags");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTags();
  }, [loadTags]);

  const allTags = groupedTags.flatMap((g) => g.tags);

  const getSelectedTags = (ids: string[]): SelectedTag[] => {
    return ids
      .map((id) => {
        const tag = allTags.find((t) => t.id === id);
        if (!tag) return null;
        return { id: tag.id, name: tag.name, slug: tag.slug, color: tag.color };
      })
      .filter((t): t is SelectedTag => t !== null);
  };

  const addTag = (tagId: string) => {
    if (selectedTagIds.includes(tagId)) return;
    const newIds = [...selectedTagIds, tagId];
    onChange(newIds, getSelectedTags(newIds));
  };

  const removeTag = (tagId: string) => {
    const newIds = selectedTagIds.filter((id) => id !== tagId);
    onChange(newIds, getSelectedTags(newIds));
  };

  const toggleExpanded = (categoryId: string) => {
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

  const handleSuggest = async (categoryId: string) => {
    if (!suggestName.trim()) return;
    setIsSuggesting(true);
    try {
      const newTag = await api.tags.suggest({
        name: suggestName.trim(),
        category_id: categoryId,
      });
      setGroupedTags((prev) =>
        prev.map((group) => {
          if (group.category.id === categoryId) {
            return { ...group, tags: [...group.tags, newTag] };
          }
          return group;
        })
      );
      const newIds = [...selectedTagIds, newTag.id];
      const newSelectedTag: SelectedTag = {
        id: newTag.id,
        name: newTag.name,
        slug: newTag.slug,
        color: newTag.color,
      };
      onChange(newIds, [...getSelectedTags(selectedTagIds), newSelectedTag]);
      setSuggestName("");
      setSuggestingFor(null);
    } catch {
      setError("Failed to suggest tag");
    } finally {
      setIsSuggesting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-10 bg-muted rounded-lg animate-pulse" />
        ))}
      </div>
    );
  }

  if (error) {
    return <div className="text-red-600 text-sm">{error}</div>;
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-foreground">Tags</h3>
      {groupedTags.map((group) => {
        const isExpanded = expandedCategories.has(group.category.id);
        const selectedInCategory = group.tags.filter((t) =>
          selectedTagIds.includes(t.id)
        );
        const unselectedInCategory = group.tags.filter(
          (t) => !selectedTagIds.includes(t.id)
        );

        return (
          <div key={group.category.id} className="space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                {group.category.name}
              </span>
              <button
                onClick={() => toggleExpanded(group.category.id)}
                className="text-xs text-accent hover:text-accent-hover transition-colors"
              >
                {isExpanded ? "Done" : "+ Add"}
              </button>
            </div>

            {selectedInCategory.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {selectedInCategory.map((tag) => (
                  <span
                    key={tag.id}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-accent text-white"
                  >
                    {tag.name}
                    <button
                      onClick={() => removeTag(tag.id)}
                      className="hover:bg-white/20 rounded-full p-0.5 -mr-0.5 transition-colors"
                      aria-label={`Remove ${tag.name}`}
                    >
                      <svg
                        className="w-3 h-3"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M6 18L18 6M6 6l12 12"
                        />
                      </svg>
                    </button>
                  </span>
                ))}
              </div>
            )}

            {isExpanded && (
              <div className="space-y-2 pl-1">
                {unselectedInCategory.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {unselectedInCategory.map((tag: TagWithCategory) => (
                      <button
                        key={tag.id}
                        onClick={() => addTag(tag.id)}
                        className="px-2 py-0.5 rounded-full text-xs font-medium bg-accent-subtle text-accent hover:bg-accent/15 transition-colors"
                      >
                        {tag.name}
                        {tag.status === "pending" && (
                          <span className="opacity-75" title="Pending review">
                            {" "}
                            *
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                )}

                {suggestingFor === group.category.id ? (
                  <div className="flex items-center gap-1.5">
                    <input
                      type="text"
                      value={suggestName}
                      onChange={(e) => setSuggestName(e.target.value)}
                      placeholder="Tag name"
                      className="flex-1 min-w-0 px-2 py-1 text-xs border border-border rounded focus:outline-none focus:ring-1 focus:ring-accent"
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          handleSuggest(group.category.id);
                        } else if (e.key === "Escape") {
                          setSuggestingFor(null);
                          setSuggestName("");
                        }
                      }}
                    />
                    <button
                      onClick={() => handleSuggest(group.category.id)}
                      disabled={isSuggesting || !suggestName.trim()}
                      className="px-2 py-1 text-xs bg-accent text-white rounded hover:bg-accent/90 disabled:opacity-50"
                    >
                      {isSuggesting ? "..." : "Add"}
                    </button>
                    <button
                      onClick={() => {
                        setSuggestingFor(null);
                        setSuggestName("");
                      }}
                      className="text-xs text-muted-foreground hover:text-foreground"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setSuggestingFor(group.category.id)}
                    className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                  >
                    + Suggest new
                  </button>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
