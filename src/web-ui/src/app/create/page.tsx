"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { api } from "@/lib/api";

/**
 * Creating a project, and nothing else. Entering a competition is a separate
 * act on a published project — this page deliberately knows nothing about
 * rounds, and takes no competition parameter.
 */
export default function CreateProjectPage() {
  const router = useRouter();
  const { isReady, isLoading: authLoading } = useRequireAuth();
  const [url, setUrl] = useState("");
  const [iOwnThis, setIOwnThis] = useState(true);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    try {
      new URL(url);
    } catch {
      setError("Please enter a valid URL");
      return;
    }

    setIsLoading(true);

    try {
      const project = await api.myProjects.create({
        website_url: url,
        is_community_tipoff: !iOwnThis,
      });
      router.push(`/my-projects/${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit project");
    } finally {
      setIsLoading(false);
    }
  };

  if (authLoading || !isReady) {
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
            Create a project
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Add it as a draft, then publish it when it&apos;s ready.
          </p>
        </div>
      </section>

      <section className="py-8 px-4 sm:px-6">
        <div className="max-w-lg mx-auto">
          <div className="bg-white border border-border rounded-xl p-6">
            <h2 className="text-foreground font-semibold mb-4">
              Start a new project
            </h2>
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

              <fieldset className="space-y-2">
                <legend className="label mb-1">Who made this project?</legend>
                <label htmlFor="ownership-mine" className="flex items-start gap-2 cursor-pointer">
                  <input
                    id="ownership-mine"
                    type="radio"
                    name="ownership"
                    checked={iOwnThis}
                    onChange={() => setIOwnThis(true)}
                    className="mt-1"
                  />
                  <span className="text-sm">
                    <span className="text-foreground font-medium">Mine</span>
                    <span className="block text-xs text-muted-foreground">I made this project.</span>
                  </span>
                </label>
                <label htmlFor="ownership-tipoff" className="flex items-start gap-2 cursor-pointer">
                  <input
                    id="ownership-tipoff"
                    type="radio"
                    name="ownership"
                    checked={!iOwnThis}
                    onChange={() => setIOwnThis(false)}
                    className="mt-1"
                  />
                  <span className="text-sm">
                    <span className="text-foreground font-medium">Tipoff</span>
                    <span className="block text-xs text-muted-foreground">Someone else made this — I&apos;m flagging it for the community.</span>
                  </span>
                </label>
              </fieldset>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full btn-primary py-2.5"
              >
                {isLoading ? "Creating..." : "Create Draft"}
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
