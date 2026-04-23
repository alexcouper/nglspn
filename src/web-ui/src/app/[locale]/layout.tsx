import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { setRequestLocale } from "next-intl/server";
import { Suspense } from "react";
import { AuthProvider } from "@/contexts/auth";
import { EditableMessagesProvider } from "@/contexts/editable-messages";
import { Navigation } from "@/components/Navigation";
import { Footer } from "@/components/Footer";
import { routing } from "@/i18n/routing";
import { LocaleHtmlLang } from "@/components/LocaleHtmlLang";
import { readEditModeFromServer } from "@/lib/i18n/edit-mode-cookie";
import { loadMessages } from "@/lib/i18n/messages";
import type { Locale } from "@/i18n/config";

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return {
    alternates: {
      canonical: locale === "is" ? "/" : `/${locale}`,
      languages: { is: "/", en: "/en", "x-default": "/" },
    },
  };
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  setRequestLocale(locale);

  const { merged, localeOnly, english } = await loadMessages(locale as Locale);
  const editMode = await readEditModeFromServer();

  return (
    <EditableMessagesProvider
      locale={locale as Locale}
      initialMessages={merged}
      localeOnlyMessages={localeOnly}
      enMessages={english}
      editMode={editMode}
    >
      <LocaleHtmlLang locale={locale} />
      <AuthProvider>
        <Suspense>
          <Navigation />
        </Suspense>
        <Suspense>
          <div className="flex-1 flex flex-col">{children}</div>
        </Suspense>
        <Footer />
      </AuthProvider>
    </EditableMessagesProvider>
  );
}
