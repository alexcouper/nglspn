"use client";

export default function ProjectError({ reset }: { reset: () => void }) {
  return (
    <main className="min-h-screen bg-muted pt-14">
      <section className="py-8 px-4 sm:px-6">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-2xl font-bold mb-4">Something went wrong</h1>
          <p className="text-muted-foreground mb-6">
            We couldn&apos;t load this project. This may be a temporary issue.
          </p>
          <button
            onClick={reset}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            Try again
          </button>
        </div>
      </section>
    </main>
  );
}
