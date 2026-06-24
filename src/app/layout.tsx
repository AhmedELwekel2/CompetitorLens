import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import { AnalysisProvider } from "@/lib/analysis-context";
import { AppChrome } from "@/components/AppChrome";

export const metadata: Metadata = {
  title: "sx — Trusted Advisor Intelligence",
  description:
    "AI-powered competitive intelligence and market sentiment analysis",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-bg-main">
        <AuthProvider>
          <AnalysisProvider>
            <AppChrome>{children}</AppChrome>
          </AnalysisProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
