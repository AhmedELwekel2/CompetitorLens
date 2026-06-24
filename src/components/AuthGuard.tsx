"use client";

import { useAuth } from "@/lib/auth";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, ReactNode } from "react";
import { Loader2 } from "lucide-react";
import type { User } from "@/lib/api";

// Pages reachable without being signed in.
const publicPages = ["/", "/welcome", "/login", "/pending-approval"];

// A signed-in but not-yet-approved (or rejected) non-admin user can only
// reach the pending screen and the public landing.
function awaitingApproval(user: User) {
  return (
    user.role !== "ADMIN" &&
    (user.status === "PENDING" || user.status === "REJECTED")
  );
}

function FullScreenLoader() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-main">
      <Loader2 className="animate-spin text-primary" size={28} />
    </div>
  );
}

export function AuthGuard({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const isPublic = publicPages.includes(pathname);

  useEffect(() => {
    if (loading) return;

    // Not signed in → block anything that isn't public.
    if (!user) {
      if (!isPublic) router.replace("/login");
      return;
    }

    // Signed in but sitting on the login page → send into the app.
    if (pathname === "/login") {
      router.replace(awaitingApproval(user) ? "/pending-approval" : "/market-analysis");
      return;
    }

    // Awaiting approval → confine to the pending screen (landing still allowed).
    if (
      awaitingApproval(user) &&
      pathname !== "/pending-approval" &&
      pathname !== "/welcome" &&
      pathname !== "/"
    ) {
      router.replace("/pending-approval");
    }
  }, [user, loading, pathname, isPublic, router]);

  // ── Render gating (prevents protected content / sidebar flashing) ──
  if (loading) {
    return isPublic ? <>{children}</> : <FullScreenLoader />;
  }
  if (!user) {
    return isPublic ? <>{children}</> : <FullScreenLoader />;
  }
  if (pathname === "/login") {
    return <FullScreenLoader />; // redirecting into the app
  }
  if (
    awaitingApproval(user) &&
    pathname !== "/pending-approval" &&
    pathname !== "/welcome" &&
    pathname !== "/"
  ) {
    return <FullScreenLoader />; // redirecting to pending screen
  }

  return <>{children}</>;
}
