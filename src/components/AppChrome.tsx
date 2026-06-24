"use client";

import { usePathname } from "next/navigation";
import { ReactNode } from "react";
import Sidebar from "@/components/Sidebar";
import NotificationToast from "@/components/NotificationToast";
import { AuthGuard } from "@/components/AuthGuard";

// Routes that render full-bleed, without the app sidebar / padded shell:
// the landing page, auth screens, and the root redirect.
const bareRoutes = ["/", "/welcome", "/login", "/pending-approval"];

function isBare(pathname: string) {
  return bareRoutes.some(
    (route) =>
      pathname === route || (route !== "/" && pathname.startsWith(`${route}/`))
  );
}

/**
 * AuthGuard wraps every route so redirects/gating apply everywhere, but the
 * app chrome (sidebar + padded main) is only rendered for in-app pages.
 * Landing and auth pages own the full viewport.
 */
export function AppChrome({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  if (isBare(pathname)) {
    return <AuthGuard>{children}</AuthGuard>;
  }

  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <NotificationToast />
        <main className="flex-1 min-w-0 overflow-y-auto">
          <div className="p-5 lg:p-8 max-w-[1440px] animate-fade-in-up">
            {children}
          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
