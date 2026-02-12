"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import type { TagGrouped, TagWithCategory } from "@/lib/api";

export type SelectedTag = {
  id: string;
  name: string;
  slug: string;
  color: string | null;
};

interface TagSelectorProps {
  selectedTagIds: string[];
  onChange: (tagIds: string[], tags: SelectedTag[]) => void;
}

export function TagSelector({ selectedTagIds, onChange }: TagSelectorProps) {
  const [groupedTags, setGroupedTags] = useState<TagGrouped[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
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

  // Get all tags as a flat list for lookups
  const allTags = groupedTags.flatMap((g) => g.tags);

  const getSelectedTags = (ids: string[]): SelectedTag[] => {
    return ids
      .map((id) => {
        const tag = allTags.find((t) => t.id === id);
        if (!tag) return null;
        return {
          id: tag.id,
          name: tag.name,
          slug: tag.slug,
          color: tag.color,
        };
      })
      .filter((t): t is SelectedTag => t !== null);
  };

  const toggleTag = (tagId: string) => {
    const newIds = selectedTagIds.includes(tagId)
      ? selectedTagIds.filter((id) => id !== tagId)
      : [...selectedTagIds, tagId];
    onChange(newIds, getSelectedTags(newIds));
  };

  const handleSuggest = async (categoryId: string) => {
    if (!suggestName.trim()) return;

    setIsSuggesting(true);
    try {
      const newTag = await api.tags.suggest({
        name: suggestName.trim(),
        category_id: categoryId,
      });
      // Add the new tag to the local state
      setGroupedTags((prev) =>
        prev.map((group) => {
          if (group.category.id === categoryId) {
            return {
              ...group,
              tags: [...group.tags, newTag],
            };
          }
          return group;
        })
      );
      // Auto-select the new tag
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
      <div className="animate-pulse space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-20 bg-muted rounded-lg" />
        ))}
      </div>
    );
  }

  if (error) {
    return <div className="text-red-600 text-sm">{error}</div>;
  }

  return (
    <div className="space-y-6">
      {groupedTags.map((group) => (
        <div key={group.category.id}>
          <h4 className="text-sm font-medium text-foreground mb-2">
            {group.category.name}
          </h4>
          <div className="flex flex-wrap gap-2">
            {group.tags.map((tag: TagWithCategory) => (
              <TagCheckbox
                key={tag.id}
                tag={tag}
                checked={selectedTagIds.includes(tag.id)}
                onChange={() => toggleTag(tag.id)}
              />
            ))}
            {suggestingFor === group.category.id ? (
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={suggestName}
                  onChange={(e) => setSuggestName(e.target.value)}
                  placeholder="Tag name"
                  className="px-2 py-1 text-sm border rounded focus:outline-none focus:ring-1 focus:ring-accent"
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
                  className="px-2 py-1 text-sm bg-accent text-white rounded hover:bg-accent/90 disabled:opacity-50"
                >
                  {isSuggesting ? "..." : "Add"}
                </button>
                <button
                  onClick={() => {
                    setSuggestingFor(null);
                    setSuggestName("");
                  }}
                  className="px-2 py-1 text-sm text-muted-foreground hover:text-foreground"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <button
                onClick={() => setSuggestingFor(group.category.id)}
                className="px-2 py-1 text-sm text-muted-foreground hover:text-foreground border border-dashed border-border rounded-lg hover:border-foreground/30 transition-colors"
              >
                + Suggest
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

interface TagCheckboxProps {
  tag: TagWithCategory;
  checked: boolean;
  onChange: () => void;
}

function TagCheckbox({ tag, checked, onChange }: TagCheckboxProps) {
  return (
    <label
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full cursor-pointer transition-all text-sm ${
        checked
          ? "bg-accent text-white"
          : "bg-accent-subtle text-accent hover:bg-accent/15"
      }`}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="sr-only"
      />
      <span>{tag.name}</span>
      {tag.status === "pending" && (
        <span
          className="text-xs opacity-75"
          title="This tag is pending review"
        >
          *
        </span>
      )}
    </label>
  );
}
