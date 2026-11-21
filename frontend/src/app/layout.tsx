import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import { Suspense } from "react";

import { ClientList, ClientListSkeleton } from "@/components/client-list";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";

import "./globals.css";

const geistSans = Geist({ variable: "--font-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "STR Search · Deal recommendations",
  description: "Fewer, better-fit deals for each client, with the reasons why.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col md:flex-row">
        <TooltipProvider>
          <aside className="bg-sidebar border-sidebar-border shrink-0 border-b md:sticky md:top-0 md:h-screen md:w-80 md:overflow-y-auto md:border-r md:border-b-0">
            <div className="border-sidebar-border border-b px-4 py-3">
              <Link href="/" className="font-semibold">
                STR Search
              </Link>
              <p className="text-muted-foreground text-xs">Deal recommendations for reps</p>
            </div>
            <Suspense fallback={<ClientListSkeleton />}>
              <ClientList />
            </Suspense>
          </aside>
          <main className="min-w-0 flex-1 p-4 md:p-8">{children}</main>
        </TooltipProvider>
        <Toaster />
      </body>
    </html>
  );
}
