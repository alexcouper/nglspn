import { Suspense } from "react";
import { ProjectsListing } from "./ProjectsListing";

export default function ProjectsPage() {
  return (
    <main className="min-h-screen bg-muted pt-14">
      <section className="bg-white border-b border-border py-10 px-4 sm:px-6">
        <div className="max-w-6xl mx-auto">
          <h1 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight">
            Projects
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Explore what the community is building
          </p>
        </div>
      </section>

      <section className="py-8 px-4 sm:px-6">
        <div className="max-w-6xl mx-auto">
          <Suspense
            fallback={
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {[1, 2, 3, 4, 5, 6].map((i) => (
                  <div key={i}>
                    <div className="skeleton aspect-video rounded-t-xl" />
                    <div className="bg-white border border-t-0 border-border rounded-b-xl p-4">
                      <div className="skeleton h-4 w-2/3 mb-2" />
                      <div className="skeleton h-3 w-1/3" />
                    </div>
                  </div>
                ))}
              </div>
            }
          >
            <ProjectsListing />
          </Suspense>
        </div>
      </section>
    </main>
  );
}
