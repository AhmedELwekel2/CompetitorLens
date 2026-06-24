"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function RootPage() {
  const router = useRouter();
  const { user, loading } = useAuth();

  useEffect(() => {
    if (loading) return;
    // Signed in → into the app; otherwise → public landing.
    router.replace(user ? "/market-analysis" : "/welcome");
  }, [user, loading, router]);

  return null;
}
