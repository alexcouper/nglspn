"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/auth";
import { BreadcrumbProvider } from "./BreadcrumbContext";
import { Breadcrumbs } from "./Breadcrumbs";

export default function MyReviewsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();

  const isReviewer = user?.groups?.includes("REVIEWERS") ?? false;

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  if (!authLoading && !isAuthenticated) {
    return null;
  }

  const renderContent = () => {
    if (authLoading) {
      return (
        <div className="bg-white rounded-xl border border-border p-8">
          <div className="skeleton h-5 w-1/3 mb-3" />
          <div className="skeleton h-4 w-2/3" />
        </div>
      );
    }

    if (!isReviewer) {
      return (
        <div className="bg-white rounded-xl border border-border p-8 text-center">
          <p className="text-muted-foreground text-sm">
            Interested in helping rank the next set of projects? Get in touch:{" "}
            <a
              href="mailto:admin@naglasupan.is"
              className="text-accent hover:text-accent-hover transition-colors"
            >
              alex@naglasupan.is
            </a>
          </p>
        </div>
      );
    }

    return (
      <>
        <Breadcrumbs />
        {children}
      </>
    );
  };

  const content = (
    <main className="min-h-screen bg-muted pt-14">
      <section className="bg-white border-b border-border py-10 px-4 sm:px-6">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight">
            My Reviews
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Rank projects for competitions
          </p>
        </div>
      </section>
      <section className="py-8 px-4 sm:px-6">
        <div className="max-w-4xl mx-auto">{renderContent()}</div>
      </section>
    </main>
  );

  if (isReviewer && !authLoading) {
    return <BreadcrumbProvider>{content}</BreadcrumbProvider>;
  }

  return content;
}
