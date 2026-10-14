import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { NotificationsFeed } from "./NotificationsFeed";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("notifications.page");
  return {
    title: t("metaTitle"),
  };
}

export default async function NotificationsPage() {
  const t = await getTranslations("notifications.page");
  return (
    <main className="min-h-screen bg-muted pt-14">
      <section className="bg-white border-b border-border py-10 px-4 sm:px-6">
        <div className="max-w-3xl mx-auto">
          <h1 className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight">
            {t("title")}
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            {t("subtitle")}
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
