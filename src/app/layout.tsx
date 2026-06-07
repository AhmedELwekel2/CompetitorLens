import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import NotificationToast from "@/components/NotificationToast";
import { AuthProvider } from "@/lib/auth";
import { AnalysisProvider } from "@/lib/analysis-context";
import { AuthGuard } from "@/components/AuthGuard";

export const metadata: Metadata = {
  title: "sx — Trusted Advisor Intelligence",
  description: "AI-powered competitive intelligence and market sentiment analysis",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen flex bg-bg-main">
        <AuthProvider>
          <AnalysisProvider>
            <AuthGuard>
              <Sidebar />
              <NotificationToast />
              <main className="flex-1 min-w-0 overflow-y-auto">
                <div className="p-5 lg:p-8 max-w-[1440px] animate-fade-in-up">
                  {children}
                </div>
              </main>
            </AuthGuard>
          </AnalysisProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
