"use client";

import ReactMarkdown from "react-markdown";

interface Props {
  info: string;
  // Shown in place of the markdown when there is nothing to render.
  emptyText?: string;
}

// The one rendering of a user's About text, shared by the public profile and
// the edit page's Preview so the two cannot drift. Images are dropped: a
// public page under someone's name should not be a place to hot-link
// third-party content. react-markdown already discards raw HTML.
export function ProfileAbout({ info, emptyText = "Nothing written yet." }: Props) {
  if (!info.trim()) {
    return <p className="text-sm italic text-muted-foreground">{emptyText}</p>;
  }
  return (
    <div className="markdown text-[15px] leading-relaxed" data-testid="profile-about">
      <ReactMarkdown disallowedElements={["img"]}>{info}</ReactMarkdown>
    </div>
  );
}
