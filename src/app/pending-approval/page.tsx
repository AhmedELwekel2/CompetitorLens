"use client";

import { useRouter } from "next/navigation";
import { TrendingUp, Clock, ArrowLeft } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useEffect } from "react";

export default function PendingApprovalPage() {
  const router = useRouter();
  const { user, logout } = useAuth();

  useEffect(() => {
    // If user is approved and admin, go to admin dashboard
    // If user is approved, go to market analysis
    if (user?.role === "ADMIN") {
      router.push("/admin");
    } else if (user?.status === "APPROVED") {
      router.push("/market-analysis");
    }
  }, [user, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-main p-4">
      <div className="w-full max-w-md text-center">
        {/* Logo */}
        <div className="flex items-center gap-2.5 justify-center mb-8">
          <div className="w-10 h-10 rounded-lg bg-sidebar flex items-center justify-center">
            <TrendingUp size={22} className="text-accent-green" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-text-heading leading-tight">CompetitorLens</h1>
            <p className="text-accent-green text-[10px] font-semibold uppercase tracking-[0.12em]">Trusted Advisor</p>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-border p-8">
          <div className="w-16 h-16 rounded-full bg-amber-50 flex items-center justify-center mx-auto mb-5">
            <Clock size={32} className="text-amber-500" />
          </div>

          <h2 className="text-xl font-bold text-text-heading mb-2">
            Registration Successful!
          </h2>
          <p className="text-sm text-text-secondary mb-6 leading-relaxed">
            Your account has been created and is currently <span className="font-semibold text-amber-600">pending admin approval</span>.
            You'll be able to access the full dashboard once an administrator approves your account.
          </p>

          <div className="bg-bg-main rounded-lg p-4 mb-6">
            <p className="text-[12px] text-text-muted mb-1">Registered as</p>
            <p className="text-sm font-medium text-text-heading">{user?.full_name || user?.email}</p>
          </div>

          <p className="text-[12px] text-text-muted mb-5">
            You will receive access once approved. Please check back later.
          </p>

          <div className="flex items-center gap-3 justify-center">
            <button
              onClick={() => { logout(); router.push("/login"); }}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg border border-border text-sm font-medium text-text-secondary hover:bg-bg-main transition-colors"
            >
              <ArrowLeft size={16} />
              Back to Login
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}