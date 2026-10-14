import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getTranslations } from "next-intl/server";
import { AuthProvider } from "@/contexts/auth";
import { NotificationsProvider } from "@/contexts/notifications";
import { ToastsProvider } from "@/contexts/toasts";
import { Navigation } from "@/components/Navigation";
import { Footer } from "@/components/Footer";
import { NotificationToaster } from "@/components/NotificationToaster";
import { ToastContainer } from "@/components/ToastContainer";
import { PlausibleTracker } from "@/components/PlausibleTracker";
import { SITE_URL } from "@/lib/constants";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("common.meta");
  const title = t("title");
  const description = t("description");
  return {
    metadataBase: new URL(SITE_URL),
    title,
    description,
    icons: {
      icon: [
        { url: "/icons/favicon/favicon-32.png", sizes: "32x32", type: "image/png" },
        { url: "/icons/favicon/favicon-16.png", sizes: "16x16", type: "image/png" },
      ],
      apple: [{ url: "/icons/favicon/apple-touch-icon.png" }],
    },
    openGraph: {
      title,
      description,
      images: [
        {
          url: "/icons/app/logo.png",
          alt: title,
        },
      ],
    },
    twitter: {
      card: "summary",
      title,
      description,
      images: ["/icons/app/logo.png"],
    },
  };
}

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const locale = await getLocale();
  return (
    <html lang={locale}>
      <body className={`${inter.variable} ${jetbrainsMono.variable} antialiased min-h-screen flex flex-col`}>
        <PlausibleTracker />
        {/* Locale and messages are inherited from src/i18n/request.ts. */}
        <NextIntlClientProvider>
          <AuthProvider>
            <NotificationsProvider>
              <ToastsProvider>
                <Navigation />
                <div className="flex-1 flex flex-col">{children}</div>
                <Footer />
                <NotificationToaster />
                <ToastContainer />
              </ToastsProvider>
            </NotificationsProvider>
          </AuthProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
