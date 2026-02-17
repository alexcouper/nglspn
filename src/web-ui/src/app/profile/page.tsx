"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { PencilIcon, EyeIcon, CloudArrowUpIcon } from "@heroicons/react/24/outline";
import { ArrowPathIcon } from "@heroicons/react/24/solid";
import { useAuth } from "@/contexts/auth";
import { api } from "@/lib/api";
import { EditProfile, type ProfileFormData } from "./EditProfile";
import { ReadOnlyProfile } from "./ReadOnlyProfile";
import { Settings } from "./Settings";

type ViewMode = "edit" | "preview";

export default function ProfilePage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading, refreshUser } = useAuth();

  const [viewMode, setViewMode] = useState<ViewMode>("edit");
  const [formData, setFormData] = useState<ProfileFormData | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (user && !formData) {
      setFormData({
        first_name: user.first_name || "",
        last_name: user.last_name || "",
        info: user.info || "",
      });
    }
  }, [user, formData]);

  const handleFormChange = useCallback((data: ProfileFormData) => {
    setFormData(data);
  }, []);

  const handleSave = async () => {
    if (!formData) return;

    setIsSaving(true);
    setError("");
    setSuccessMessage("");

    try {
      await api.auth.updateCurrentUser({
        first_name: formData.first_name,
        last_name: formData.last_name,
        info: formData.info,
      });
      await refreshUser();
      setSuccessMessage("Profile updated successfully!");
      setTimeout(() => setSuccessMessage(""), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update profile");
    } finally {
      setIsSaving(false);
    }
  };

  if (authLoading) {
    return (
      <main className="min-h-screen bg-muted pt-14">
        <section className="bg-white border-b border-border py-10 px-4 sm:px-6">
          <div className="max-w-2xl mx-auto">
            <div className="skeleton h-7 w-24" />
          </div>
        </section>
        <section className="py-8 px-4 sm:px-6">
          <div className="max-w-2xl mx-auto">
            <div className="bg-white rounded-xl border border-border p-6">
              <div className="skeleton h-5 w-1/3 mb-4" />
              <div className="skeleton h-10 w-full mb-3" />
              <div className="skeleton h-10 w-full mb-3" />
              <div className="skeleton h-24 w-full" />
            </div>
          </div>
        </section>
      </main>
    );
  }

  if (!isAuthenticated || !user) {
    return null;
  }

  return (
    <main className="min-h-screen bg-muted pt-14">
      <section className="bg-white border-b border-border py-10 px-4 sm:px-6">
        <div className="max-w-2xl mx-auto">
          <h1 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight">
            Profile
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Manage your account
          </p>
        </div>
      </section>

      <section className="py-8 px-4 sm:px-6">
        <div className="max-w-2xl mx-auto">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm mb-4">
              {error}
            </div>
          )}

          {successMessage && (
            <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 px-4 py-3 rounded-lg text-sm mb-4">
              {successMessage}
            </div>
          )}

          <div className="bg-white rounded-xl border border-border">
            {/* Toolbar */}
            <div className="flex items-center justify-between px-5 py-3 border-b border-border">
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setViewMode("edit")}
                  title="Edit"
                  className={`p-2 rounded-lg transition-colors ${
                    viewMode === "edit"
                      ? "bg-accent-subtle text-accent"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  }`}
                >
                  <PencilIcon className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setViewMode("preview")}
                  title="Preview"
                  className={`p-2 rounded-lg transition-colors ${
                    viewMode === "preview"
                      ? "bg-accent-subtle text-accent"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  }`}
                >
                  <EyeIcon className="w-4 h-4" />
                </button>
              </div>

              <button
                onClick={handleSave}
                disabled={isSaving}
                className="btn-primary text-sm py-2 px-4"
              >
                {isSaving ? (
                  <ArrowPathIcon className="w-4 h-4 animate-spin" />
                ) : (
                  <span className="flex items-center gap-1.5">
                    <CloudArrowUpIcon className="w-4 h-4" />
                    Save
                  </span>
                )}
              </button>
            </div>

            <div className="p-5">
              {viewMode === "edit" && formData ? (
                <EditProfile
                  formData={formData}
                  onChange={handleFormChange}
                  email={user.email}
                />
              ) : (
                formData && (
                  <ReadOnlyProfile
                    profile={{
                      id: user.id,
                      first_name: formData.first_name,
                      last_name: formData.last_name,
                      info: formData.info,
                    }}
                  />
                )
              )}
            </div>
          </div>

          <Settings
            emailOptInCompetitionResults={user.email_opt_in_competition_results}
            emailOptInPlatformUpdates={user.email_opt_in_platform_updates}
            optInToExternalPromotions={user.opt_in_to_external_promotions}
          />
        </div>
      </section>
    </main>
  );
}
