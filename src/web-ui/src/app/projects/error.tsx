"use client";

export default function ProjectsError({ reset }: { reset: () => void }) {
  return (
    <main className="min-h-screen bg-muted pt-14">
      <section className="py-20 px-4 sm:px-6">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-2xl font-bold mb-4">Something went wrong</h1>
          <p className="text-muted-foreground mb-6">
            We couldn&apos;t load projects. This may be a temporary issue.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-6 py-2.5 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 cursor-pointer font-medium shadow-sm"
          >
            Try again
          </button>
        </div>
      </section>
    </main>
  );
}
