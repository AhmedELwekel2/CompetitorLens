"use client";

import { useAuth } from "@/lib/auth";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, ReactNode } from "react";

const publicPages = ["/login", "/pending-approval"];

export function AuthGuard({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (loading || !user) return;
    // Skip for public pages and admin users
    if (publicPages.includes(pathname) || user.role === "ADMIN") return;

    if (user.status === "PENDING" && pathname !== "/pending-approval") {
      router.push("/pending-approval");
    } else if (user.status === "REJECTED" && pathname !== "/pending-approval") {
      router.push("/pending-approval");
    }
  }, [user, loading, pathname, router]);

  return <>{children}</>;
}