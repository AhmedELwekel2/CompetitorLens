"use client";

import Link from "next/link";
import { ArrowRight, LayoutDashboard } from "lucide-react";
import { useAuth } from "@/lib/auth";
import type { User } from "@/lib/api";

/** Where a signed-in user should go from the landing page, with a fitting label. */
function appDestination(user: User) {
  if (
    user.role !== "ADMIN" &&
    (user.status === "PENDING" || user.status === "REJECTED")
  ) {
    return { href: "/pending-approval", label: "View your status" };
  }
  return { href: "/market-analysis", label: "Go to dashboard" };
}

type Variant = "nav" | "hero" | "band" | "link";

/**
 * Renders the call-to-action buttons on the landing page. Swaps between
 * signed-out ("Sign in" / "Get started") and signed-in ("Go to dashboard")
 * states. While auth is resolving it shows the signed-out layout to avoid
 * layout shift, then updates once the user is known.
 */
export function AuthCta({ variant }: { variant: Variant }) {
  const { user } = useAuth();
  const dest = user ? appDestination(user) : null;

  if (variant === "nav") {
    if (dest) {
      return (
        <Link
          href={dest.href}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-[13.5px] font-semibold text-white bg-primary hover:bg-primary-hover shadow-card transition-colors cursor-pointer"
        >
          {dest.label}
          <ArrowRight size={15} aria-hidden />
        </Link>
      );
    }
    return (
      <>
        <Link
          href="/login"
          className="hidden sm:inline-flex px-3.5 py-2 text-[13.5px] font-medium text-text-secondary hover:text-text-heading transition-colors cursor-pointer"
        >
          Sign in
        </Link>
        <Link
          href="/login"
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-[13.5px] font-semibold text-white bg-primary hover:bg-primary-hover shadow-card transition-colors cursor-pointer"
        >
          Get started
          <ArrowRight size={15} aria-hidden />
        </Link>
      </>
    );
  }

  if (variant === "hero") {
    return (
      <>
        <Link
          href={dest ? dest.href : "/login"}
          className="inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl text-[15px] font-semibold text-white bg-primary hover:bg-primary-hover shadow-pop transition-colors cursor-pointer"
        >
          {dest ? dest.label : "Get started free"}
          <ArrowRight size={17} aria-hidden />
        </Link>
        <a
          href="#how"
          className="inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl text-[15px] font-semibold text-text-heading bg-bg-card border border-border hover:border-primary/40 shadow-soft transition-colors cursor-pointer"
        >
          See how it works
        </a>
      </>
    );
  }

  if (variant === "band") {
    if (dest) {
      return (
        <Link
          href={dest.href}
          className="inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-xl text-[15px] font-semibold text-primary bg-white hover:bg-white/90 shadow-pop transition-colors cursor-pointer"
        >
          <LayoutDashboard size={17} aria-hidden />
          {dest.label}
        </Link>
      );
    }
    return (
      <>
        <Link
          href="/login"
          className="inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-xl text-[15px] font-semibold text-primary bg-white hover:bg-white/90 shadow-pop transition-colors cursor-pointer"
        >
          Get started free
          <ArrowRight size={17} aria-hidden />
        </Link>
        <Link
          href="/login"
          className="inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-xl text-[15px] font-semibold text-white border border-white/25 hover:bg-white/10 transition-colors cursor-pointer"
        >
          Sign in
        </Link>
      </>
    );
  }

  // variant === "link" (footer)
  return (
    <Link
      href={dest ? dest.href : "/login"}
      className="hover:text-text-heading transition-colors"
    >
      {dest ? dest.label : "Sign in"}
    </Link>
  );
}
