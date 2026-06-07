"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Sparkles,
  TrendingUp,
  Building2,
  Clock,
  Settings,
  X,
  Menu,
  LogOut,
  Loader2,
  ShieldCheck,
} from "lucide-react";
import { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { useAnalysis } from "@/lib/analysis-context";

const navItems = [
  { href: "/market-analysis", label: "Market Analysis", icon: TrendingUp, type: "MARKET" as const },
  { href: "/business-analysis", label: "Business Analysis", icon: Building2, type: "BUSINESS" as const },
  { href: "/history", label: "History", icon: Clock, type: null },
  { href: "/settings", label: "Settings", icon: Settings, type: null },
];

const adminItems = [
  { href: "/admin", label: "Admin Dashboard", icon: ShieldCheck },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { market, business, notifications } = useAnalysis();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  const initials = user?.avatar_initials || "U";
  const displayName = user?.full_name || "Guest";
  const displayTitle = user?.professional_title || "Analyst";

  const isRunning = (type: "MARKET" | "BUSINESS") => {
    if (type === "MARKET") return market.loading;
    if (type === "BUSINESS") return business.loading;
    return false;
  };

  return (
    <>
      {/* Mobile hamburger */}
      <button
        onClick={() => setOpen(true)}
        className="lg:hidden fixed top-4 left-4 z-50 p-2 rounded-lg bg-sidebar text-white shadow-lg"
        aria-label="Open menu"
      >
        <Menu size={20} />
      </button>

      {/* Overlay */}
      {open && (
        <div
          className="lg:hidden fixed inset-0 bg-black/40 z-40"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed top-0 left-0 h-full z-50 w-[260px] flex flex-col
          transition-transform duration-300 ease-in-out
          lg:translate-x-0 lg:static lg:z-auto
          lg:h-screen lg:sticky lg:top-0
          ${open ? "translate-x-0" : "-translate-x-full"}
        `}
        style={{
          background: "linear-gradient(180deg, #211D54 0%, #1E1B4B 55%, #181542 100%)",
          boxShadow: "1px 0 0 rgba(255,255,255,0.04), 8px 0 30px -12px rgba(30,27,75,0.45)",
        }}
      >
        {/* Close button mobile */}
        <button
          onClick={() => setOpen(false)}
          className="lg:hidden absolute top-4 right-4 text-white/60 hover:text-white"
          aria-label="Close menu"
        >
          <X size={18} />
        </button>

        {/* Logo */}
        <div className="px-5 pt-6 pb-8">
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center shadow-lg"
              style={{
                background: "linear-gradient(135deg, #8B5CF6 0%, #6D28D9 50%, #2DD4A8 130%)",
                boxShadow: "0 6px 16px -4px rgba(139,92,246,0.55)",
              }}
            >
              <Sparkles size={18} className="text-white" strokeWidth={2.2} />
            </div>
            <div>
              <h1
                className="font-bold text-[18px] leading-none tracking-tight"
                style={{
                  background: "linear-gradient(90deg, #fff 0%, #a78bfa 60%, #2DD4A8 100%)",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  backgroundClip: "text",
                }}
              >
                sx
              </h1>
              <p className="text-white/40 text-[9.5px] font-semibold uppercase tracking-[0.18em] mt-0.5">
                Trusted Advisor
              </p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 space-y-1">
          {/* Admin links */}
          {user?.role === "ADMIN" && (
            <>
              {adminItems.map((item) => {
                const isActive = pathname === item.href;
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`
                      flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13.5px] font-medium transition-all duration-200 relative
                      ${
                        isActive
                          ? "bg-sidebar-active text-amber-300 ring-1 ring-amber-300/25 shadow-[inset_3px_0_0_0_var(--color-neutral)]"
                          : "text-amber-400/75 hover:text-amber-300 hover:bg-sidebar-hover"
                      }
                    `}
                  >
                    <Icon size={18} strokeWidth={isActive ? 2.2 : 1.8} />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
              <div className="my-2 border-t border-white/10" />
            </>
          )}
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            const running = item.type ? isRunning(item.type) : false;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`
                  flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13.5px] font-medium transition-all duration-200 relative
                  ${
                    isActive
                      ? "bg-sidebar-active text-white ring-1 ring-accent-green/30 shadow-[inset_3px_0_0_0_var(--color-accent-green)]"
                      : "text-white/60 hover:text-white/90 hover:bg-sidebar-hover"
                  }
                `}
              >
                {running ? (
                  <Loader2 size={18} className="animate-spin text-accent-green" />
                ) : (
                  <Icon size={18} strokeWidth={isActive ? 2.2 : 1.8} className={isActive ? "text-accent-green" : ""} />
                )}
                <span>{item.label}</span>
                {running && (
                  <span className="ml-auto">
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-green opacity-75" />
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-accent-green" />
                    </span>
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* User profile */}
        <div className="px-4 py-5 border-t border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-primary flex items-center justify-center text-white text-xs font-bold">
              {initials}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-white text-[13px] font-medium truncate">
                {displayName}
              </p>
              <p className="text-white/40 text-[11px] truncate">
                {displayTitle}
              </p>
            </div>
            {user && (
              <button
                onClick={logout}
                className="text-white/40 hover:text-white/80 transition-colors"
                title="Sign out"
              >
                <LogOut size={16} />
              </button>
            )}
          </div>
        </div>
      </aside>
    </>
  );
}