"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function RootPage() {
  const router = useRouter();

  useEffect(() => {
    // The site root always lands on the public landing page.
    // The landing page itself adapts for signed-in users ("Go to dashboard").
    router.replace("/welcome");
  }, [router]);

  return null;
}
