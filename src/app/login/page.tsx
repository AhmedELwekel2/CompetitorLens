"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { TrendingUp, Loader2 } from "lucide-react";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const { login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "login") {
        await login(email, password);
        router.push("/market-analysis");
      } else {
        await register({ full_name: fullName, email, password });
        router.push("/pending-approval");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-main p-4">
      <div className="w-full max-w-md">
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
          <h2 className="text-xl font-bold text-text-heading mb-1">
            {mode === "login" ? "Welcome back" : "Create your account"}
          </h2>
          <p className="text-sm text-text-secondary mb-6">
            {mode === "login"
              ? "Sign in to access your competitive intelligence dashboard."
              : "Get started with AI-powered market analysis."}
          </p>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-negative/10 border border-negative/20 text-sm text-negative">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === "register" && (
              <div>
                <label className="text-[10px] font-semibold uppercase tracking-[0.12em] text-text-muted block mb-2">
                  Full Name
                </label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                  placeholder="Alexander Vance"
                  className="w-full px-4 py-3 text-[13.5px] rounded-lg border border-border bg-bg-main placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/15 focus:border-primary/40"
                />
              </div>
            )}
            <div>
              <label className="text-[10px] font-semibold uppercase tracking-[0.12em] text-text-muted block mb-2">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="you@company.com"
                className="w-full px-4 py-3 text-[13.5px] rounded-lg border border-border bg-bg-main placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/15 focus:border-primary/40"
              />
            </div>
            <div>
              <label className="text-[10px] font-semibold uppercase tracking-[0.12em] text-text-muted block mb-2">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                placeholder="••••••••"
                className="w-full px-4 py-3 text-[13.5px] rounded-lg border border-border bg-bg-main placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/15 focus:border-primary/40"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 rounded-lg bg-primary text-white text-sm font-bold hover:bg-primary-hover transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {loading && <Loader2 size={16} className="animate-spin" />}
              {mode === "login" ? "Sign In" : "Create Account"}
            </button>
          </form>

          <div className="mt-5 text-center">
            <button
              onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}
              className="text-sm text-primary hover:underline font-medium"
            >
              {mode === "login" ? "Don't have an account? Register" : "Already have an account? Sign in"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
