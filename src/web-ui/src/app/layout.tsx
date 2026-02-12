import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { Suspense } from "react";
import { AuthProvider } from "@/contexts/auth";
import { MaintenanceProvider } from "@/contexts/maintenance";
import { Navigation } from "@/components/Navigation";
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

export const metadata: Metadata = {
  title: "naglasúpan",
  description: "All great things start small",
  openGraph: {
    title: "naglasúpan",
    description: "All great things start small",
    images: [
      {
        url: "/naglasupan.png",
        width: 595,
        height: 539,
        alt: "naglasúpan",
      },
    ],
  },
  twitter: {
    card: "summary",
    title: "naglasúpan",
    description: "All great things start small",
    images: ["/naglasupan.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${jetbrainsMono.variable} antialiased`}>
        <MaintenanceProvider>
          <AuthProvider>
            <Suspense>
              <Navigation />
            </Suspense>
            {children}
          </AuthProvider>
        </MaintenanceProvider>
      </body>
    </html>
  );
}
