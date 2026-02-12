"use client";

import { useState, useEffect, use } from "react";
import { api, type PublicUserProfile } from "@/lib/api";
import { ReadOnlyProfile } from "@/app/profile/ReadOnlyProfile";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function PublicUserProfilePage({ params }: PageProps) {
  const { id } = use(params);
  const [profile, setProfile] = useState<PublicUserProfile | null>(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchProfile = async () => {
      setIsLoading(true);
      setError("");
      try {
        const data = await api.users.getPublicProfile(id);
        setProfile(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch profile");
      }
      setIsLoading(false);
    };

    fetchProfile();
  }, [id]);

  const fullName = profile
    ? [profile.first_name, profile.last_name].filter(Boolean).join(" ") || "Anonymous"
    : "Profile";

  return (
    <main className="min-h-screen bg-muted pt-14">
      <section className="bg-white border-b border-border py-10 px-4 sm:px-6">
        <div className="max-w-2xl mx-auto">
          <h1 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight">
            {fullName}
          </h1>
        </div>
      </section>

      <section className="py-8 px-4 sm:px-6">
        <div className="max-w-2xl mx-auto">
          {isLoading ? (
            <div className="bg-white rounded-xl border border-border p-6">
              <div className="skeleton h-5 w-1/3 mb-4" />
              <div className="skeleton h-4 w-2/3 mb-2" />
              <div className="skeleton h-4 w-1/2" />
            </div>
          ) : error ? (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          ) : !profile ? (
            <p className="text-muted-foreground text-sm text-center py-12">User not found</p>
          ) : (
            <ReadOnlyProfile profile={profile} />
          )}
        </div>
      </section>
    </main>
  );
}
