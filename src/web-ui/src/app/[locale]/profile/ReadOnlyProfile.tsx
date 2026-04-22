"use client";

import ReactMarkdown from "react-markdown";
import type { PublicUserProfile } from "@/lib/api";

interface ReadOnlyProfileProps {
  profile: PublicUserProfile;
}

export function ReadOnlyProfile({ profile }: ReadOnlyProfileProps) {
  const fullName = [profile.first_name, profile.last_name].filter(Boolean).join(" ");

  return (
    <div className="bg-white rounded-xl border border-border p-6">
      <div className="space-y-5">
        <div>
          <h1 className="text-xl font-semibold text-foreground tracking-tight">
            {fullName || "Anonymous"}
          </h1>
        </div>

        <div>
          <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
            About
          </h2>
          {profile.info ? (
            <article className="markdown">
              <ReactMarkdown>{profile.info}</ReactMarkdown>
            </article>
          ) : (
            <p className="text-muted-foreground text-sm italic">No information provided</p>
          )}
        </div>
      </div>
    </div>
  );
}
