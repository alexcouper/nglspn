"use client";

import Link from "next/link";
import { ArrowLeftIcon } from "@heroicons/react/24/outline";
import { useAuth } from "@/contexts/auth";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { Settings } from "./Settings";

// Account settings on their own page. They used to sit under the profile
// editor; the public fields and the private preferences have nothing to do
// with each other, and the editor now navigates away on Save.
export default function SettingsPage() {
  const { isLoading: authLoading } = useRequireAuth();
  const { user, isAuthenticated } = useAuth();

  if (authLoading || !isAuthenticated || !user) {
    return (
      <main className="min-h-screen bg-muted pt-14">
        <section className="bg-white border-b border-border py-10 px-4 sm:px-6">
          <div className="max-w-2xl mx-auto">
            <div className="skeleton h-7 w-40" />
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-muted pt-14">
      <section className="bg-white border-b border-border py-10 px-4 sm:px-6">
        <div className="max-w-2xl mx-auto">
          <Link
            href="/profile"
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-3"
          >
            <ArrowLeftIcon className="w-4 h-4" />
            Edit profile
          </Link>
          <h1 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight">
            Account settings
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Signed in as {user.email}. Emails and privacy; nothing here is shown
            on your profile.
          </p>
        </div>
      </section>

      <section className="py-8 px-4 sm:px-6">
        <div className="max-w-2xl mx-auto">
          <Settings
            optInToExternalPromotions={user.opt_in_to_external_promotions}
            discussionEmailFrequency={user.discussion_email_frequency}
            articleEmailFrequency={user.article_email_frequency}
          />
        </div>
      </section>
    </main>
  );
}
