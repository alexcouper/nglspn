import { ProjectsList } from "./ProjectsList";

export default function MyProjectsPage() {
  return (
    <main className="min-h-screen bg-muted pt-14">
      <section className="bg-white border-b border-border py-10 px-4 sm:px-6">
        <div className="max-w-3xl mx-auto">
          <h1 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight">
            My Projects
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Manage your submissions
          </p>
        </div>
      </section>

      <section className="py-8 px-4 sm:px-6">
        <div className="max-w-3xl mx-auto">
          <ProjectsList />
        </div>
      </section>
    </main>
  );
}
