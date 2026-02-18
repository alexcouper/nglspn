"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/auth";
import { api } from "@/lib/api";

export default function SubmitPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [url, setUrl] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    try {
      new URL(url);
    } catch {
      setError("Please enter a valid URL");
      return;
    }

    if (!description.trim()) {
      setError("Please provide a description");
      return;
    }

    setIsLoading(true);

    try {
      const project = await api.myProjects.create({ website_url: url, description });
      router.push(`/my-projects/${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit project");
    } finally {
      setIsLoading(false);
    }
  };

  if (authLoading || !isAuthenticated) {
    return (
      <main className="min-h-screen bg-muted flex items-center justify-center pt-14">
        <div className="text-muted-foreground text-sm">Loading...</div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-muted pt-14">
      <section className="bg-white border-b border-border py-10 px-4 sm:px-6">
        <div className="max-w-lg mx-auto">
          <h1 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight">
            Submit Your Project
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Share what you&apos;ve been building
          </p>
        </div>
      </section>

      <section className="py-8 px-4 sm:px-6">
        <div className="max-w-lg mx-auto">
          <div className="bg-white border border-border rounded-xl p-6">
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2.5 rounded-lg text-sm">
                  {error}
                </div>
              )}

              <div>
                <label htmlFor="url" className="label">Project URL</label>
                <input
                  id="url"
                  type="url"
                  required
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  className="input"
                  placeholder="https://your-project.com"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label htmlFor="description" className="label mb-0">Description</label>
                  <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
                    Markdown
                  </span>
                </div>
                <textarea
                  id="description"
                  required
                  rows={4}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="input resize-none"
                  placeholder="Tell us about your project..."
                />
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full btn-primary py-2.5"
              >
                {isLoading ? "Submitting..." : "Submit Project"}
              </button>
            </form>

            <p className="mt-6 text-center text-sm text-muted-foreground">
              <Link href="/" className="text-accent hover:text-accent-hover font-medium transition-colors">
                Back to home
              </Link>
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
