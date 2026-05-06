import { NotificationsFeed } from "./NotificationsFeed";

export const metadata = {
  title: "Notifications - naglasúpan",
};

export default function NotificationsPage() {
  return (
    <main className="min-h-screen bg-muted pt-14">
      <section className="bg-white border-b border-border py-10 px-4 sm:px-6">
        <div className="max-w-3xl mx-auto">
          <h1 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight">
            Notifications
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Discussions on your projects and threads you&apos;ve joined
          </p>
        </div>
      </section>

      <section className="py-8 px-4 sm:px-6">
        <div className="max-w-3xl mx-auto">
          <NotificationsFeed />
        </div>
      </section>
    </main>
  );
}
