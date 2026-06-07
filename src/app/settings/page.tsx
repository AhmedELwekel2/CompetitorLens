"use client";

import { useState, useEffect } from "react";
import TopBar from "@/components/TopBar";
import {
  ShieldCheck,
  ChevronRight,
  FileText,
  Loader2,
  Activity,
  Coins,
  Zap,
  BarChart3,
  TrendingUp,
  Clock,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import {
  getSettings,
  updateSettings,
  getUsageStats,
  Settings as SettingsType,
  UsageStats,
} from "@/lib/api";

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`bg-bg-card rounded-2xl border border-border shadow-card ${className}`}>{children}</div>;
}

function Toggle({ enabled, onChange }: { enabled: boolean; onChange: () => void }) {
  return (
    <button
      onClick={onChange}
      className={`relative w-11 h-6 rounded-full transition-colors flex-shrink-0 ${enabled ? "bg-primary" : "bg-border"}`}
    >
      <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform ${enabled ? "left-[22px]" : "left-0.5"}`} />
    </button>
  );
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return n.toLocaleString();
}

/** Parse a naive-UTC ISO string from the backend as a proper UTC date */
function parseUTC(iso: string): Date {
  return new Date(iso.includes("Z") || iso.includes("+") ? iso : iso + "Z");
}

function formatDate(iso: string): string {
  if (!iso) return "—";
  try {
    return parseUTC(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

export default function SettingsPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState("limits");
  const [settings, setSettingsState] = useState<SettingsType | null>(null);
  const [usageStats, setUsageStats] = useState<UsageStats | null>(null);
  const [usageLoading, setUsageLoading] = useState(false);

  useEffect(() => {
    getSettings()
      .then((s) => setSettingsState(s))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (activeTab === "limits") {
      setUsageLoading(true);
      getUsageStats()
        .then((s) => setUsageStats(s))
        .catch(() => {})
        .finally(() => setUsageLoading(false));
    }
  }, [activeTab]);

  const handleToggle = async (field: string, value: boolean) => {
    const update: Record<string, boolean> = {};
    update[field] = value;
    const s = await updateSettings(update);
    setSettingsState(s);
  };

  const initials = user?.avatar_initials || "U";
  const memberSince = user?.created_at
    ? parseUTC(user.created_at).toLocaleDateString("en-US", {
        month: "long",
        year: "numeric",
      })
    : "";

  return (
    <>
      <TopBar placeholder="Search intelligence data..." hideActions hideSearch />

      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text-heading">Settings</h1>
        <p className="text-sm text-text-secondary mt-2">
          Manage your account preferences and monitor usage limits.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)] gap-6">
        {/* Left column */}
        <div className="space-y-6">
          <Card className="p-6 text-center">
            <div className="w-24 h-24 rounded-full bg-gradient-to-br from-sidebar to-sidebar/80 mx-auto mb-4 flex items-center justify-center text-white text-2xl font-bold">
              {initials}
            </div>
            <h2 className="text-lg font-bold text-text-heading">{user?.full_name || "User"}</h2>
            <p className="text-xs text-text-muted mt-1">{user?.email || ""}</p>
            {user?.professional_title && (
              <p className="text-[11px] text-text-secondary mt-0.5">{user.professional_title}</p>
            )}

            <div className="mt-5 space-y-1">
              {[
                { id: "profile", label: "Profile Information", icon: FileText },
                { id: "security", label: "Security & Privacy", icon: ShieldCheck },
                { id: "limits", label: "Usage Limits", icon: Activity },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center justify-between px-4 py-3 rounded-lg text-[13px] font-medium transition-colors ${
                    activeTab === tab.id ? "bg-primary text-white" : "text-text-secondary hover:bg-bg-main"
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <tab.icon size={14} />
                    {tab.label}
                  </span>
                  <ChevronRight size={14} />
                </button>
              ))}
            </div>
          </Card>

          {/* Notifications */}
          <Card className="p-5">
            <h3 className="text-[10px] font-semibold uppercase tracking-[0.12em] text-text-muted mb-4">
              Notification Alerts
            </h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[13px] font-semibold text-text-heading">Email Summary</p>
                  <p className="text-[11px] text-text-muted">Weekly intelligence digest</p>
                </div>
                <Toggle
                  enabled={settings?.email_summary_enabled ?? true}
                  onChange={() => handleToggle("email_summary_enabled", !(settings?.email_summary_enabled ?? true))}
                />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[13px] font-semibold text-text-heading">Volatility Alerts</p>
                  <p className="text-[11px] text-text-muted">Sudden sentiment shifts</p>
                </div>
                <Toggle
                  enabled={settings?.volatility_alerts_enabled ?? false}
                  onChange={() => handleToggle("volatility_alerts_enabled", !(settings?.volatility_alerts_enabled ?? false))}
                />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[13px] font-semibold text-text-heading">API Status</p>
                  <p className="text-[11px] text-text-muted">System health updates</p>
                </div>
                <Toggle
                  enabled={settings?.api_status_alerts_enabled ?? true}
                  onChange={() => handleToggle("api_status_alerts_enabled", !(settings?.api_status_alerts_enabled ?? true))}
                />
              </div>
            </div>
          </Card>
        </div>

        {/* Right column */}
        <div className="space-y-6">
          {/* Profile Details — Read-only informational */}
          {activeTab === "profile" && (
            <Card className="p-6">
              <div className="flex items-center gap-3 mb-5">
                <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                  <FileText size={20} className="text-primary" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-text-heading">Profile Details</h2>
                  <p className="text-xs text-text-secondary">Your account information and credentials.</p>
                </div>
              </div>

              <div className="space-y-4">
                {/* Full Name */}
                <div>
                  <label className="text-[10px] font-semibold uppercase tracking-[0.12em] text-text-muted block mb-2">Full Name</label>
                  <div className="w-full px-4 py-3 text-[13.5px] rounded-lg border border-border bg-bg-main/50 text-text-primary">
                    {user?.full_name || "—"}
                  </div>
                </div>

                {/* Professional Title */}
                <div>
                  <label className="text-[10px] font-semibold uppercase tracking-[0.12em] text-text-muted block mb-2">Professional Title</label>
                  <div className="w-full px-4 py-3 text-[13.5px] rounded-lg border border-border bg-bg-main/50 text-text-primary">
                    {user?.professional_title || "—"}
                  </div>
                </div>

                {/* Email */}
                <div>
                  <label className="text-[10px] font-semibold uppercase tracking-[0.12em] text-text-muted block mb-2">Contact Email</label>
                  <div className="w-full px-4 py-3 text-[13.5px] rounded-lg border border-border bg-bg-main/50 text-text-primary">
                    {user?.email || "—"}
                  </div>
                </div>

                {/* Member since */}
                <div>
                  <label className="text-[10px] font-semibold uppercase tracking-[0.12em] text-text-muted block mb-2">Member Since</label>
                  <div className="w-full px-4 py-3 text-[13.5px] rounded-lg border border-border bg-bg-main/50 text-text-primary">
                    {memberSince || "—"}
                  </div>
                </div>

                {/* Account Status */}
                <div>
                  <label className="text-[10px] font-semibold uppercase tracking-[0.12em] text-text-muted block mb-2">Account Status</label>
                  <div className="flex items-center gap-2 px-4 py-3 rounded-lg border border-border bg-bg-main/50">
                    <span className={`w-2 h-2 rounded-full ${user?.is_active ? "bg-accent-green" : "bg-negative"}`} />
                    <span className="text-[13.5px] text-text-primary">{user?.is_active ? "Active" : "Inactive"}</span>
                  </div>
                </div>
              </div>

              <div className="border-t border-border pt-5 mt-5">
                <p className="text-[11px] text-text-muted">
                  To update your profile information, please contact your account administrator.
                </p>
              </div>
            </Card>
          )}

          {/* Security & Privacy */}
          {activeTab === "security" && (
            <Card className="p-6">
              <div className="flex items-center gap-3 mb-5">
                <div className="w-10 h-10 rounded-xl bg-accent-green/15 flex items-center justify-center">
                  <ShieldCheck size={20} className="text-accent-green" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-text-heading">Security & Privacy</h2>
                  <p className="text-xs text-text-secondary">Your account security settings and privacy controls.</p>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 rounded-lg border border-border bg-bg-main/50">
                  <div>
                    <p className="text-[13px] font-semibold text-text-heading">Two-Factor Authentication</p>
                    <p className="text-[11px] text-text-muted">Add an extra layer of security to your account</p>
                  </div>
                  <span className="text-[11px] px-3 py-1 rounded-full bg-border text-text-secondary font-medium">Not Enabled</span>
                </div>

                <div className="flex items-center justify-between p-4 rounded-lg border border-border bg-bg-main/50">
                  <div>
                    <p className="text-[13px] font-semibold text-text-heading">Session Management</p>
                    <p className="text-[11px] text-text-muted">Your current session is active and secure</p>
                  </div>
                  <span className="text-[11px] px-3 py-1 rounded-full bg-accent-green/15 text-accent-green font-medium">Active</span>
                </div>

                <div className="flex items-center justify-between p-4 rounded-lg border border-border bg-bg-main/50">
                  <div>
                    <p className="text-[13px] font-semibold text-text-heading">Data Privacy</p>
                    <p className="text-[11px] text-text-muted">Your data is encrypted and stored securely</p>
                  </div>
                  <span className="text-[11px] px-3 py-1 rounded-full bg-accent-green/15 text-accent-green font-medium">Protected</span>
                </div>
              </div>

              <div className="border-t border-border pt-5 mt-5">
                <p className="text-[11px] text-text-muted">
                  For security concerns or to report an issue, please contact support.
                </p>
              </div>
            </Card>
          )}

          {/* Usage Limits */}
          {activeTab === "limits" && (
            <>
              {usageLoading && (
                <Card className="p-12 flex items-center justify-center">
                  <Loader2 size={24} className="animate-spin text-primary" />
                  <span className="ml-3 text-sm text-text-secondary">Loading usage data…</span>
                </Card>
              )}

              {!usageLoading && usageStats && (
                <>
                  {/* Summary cards */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {/* Tokens this month */}
                    <Card className="p-5">
                      <div className="flex items-center gap-2 mb-3">
                        <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                          <Zap size={16} className="text-primary" />
                        </div>
                        <span className="text-[10px] font-semibold uppercase tracking-[0.1em] text-text-muted">Tokens This Month</span>
                      </div>
                      <p className="text-2xl font-bold text-text-heading">{formatNumber(usageStats.tokens_this_month)}</p>
                      <p className="text-[11px] text-text-muted mt-1">of {formatNumber(usageStats.monthly_token_limit)} limit</p>
                      <div className="mt-3 w-full h-2 rounded-full bg-border">
                        <div
                          className="h-2 rounded-full bg-primary transition-all"
                          style={{ width: `${Math.min(100, (usageStats.tokens_this_month / usageStats.monthly_token_limit) * 100)}%` }}
                        />
                      </div>
                    </Card>

                    {/* Analyses this month */}
                    <Card className="p-5">
                      <div className="flex items-center gap-2 mb-3">
                        <div className="w-8 h-8 rounded-lg bg-accent-green/15 flex items-center justify-center">
                          <BarChart3 size={16} className="text-accent-green" />
                        </div>
                        <span className="text-[10px] font-semibold uppercase tracking-[0.1em] text-text-muted">Analyses This Month</span>
                      </div>
                      <p className="text-2xl font-bold text-text-heading">{usageStats.analyses_this_month}</p>
                      <p className="text-[11px] text-text-muted mt-1">of {usageStats.monthly_analysis_limit} limit</p>
                      <div className="mt-3 w-full h-2 rounded-full bg-border">
                        <div
                          className="h-2 rounded-full bg-accent-green transition-all"
                          style={{ width: `${Math.min(100, (usageStats.analyses_this_month / usageStats.monthly_analysis_limit) * 100)}%` }}
                        />
                      </div>
                    </Card>

                    {/* Estimated cost */}
                    <Card className="p-5">
                      <div className="flex items-center gap-2 mb-3">
                        <div className="w-8 h-8 rounded-lg bg-yellow-500/15 flex items-center justify-center">
                          <Coins size={16} className="text-yellow-500" />
                        </div>
                        <span className="text-[10px] font-semibold uppercase tracking-[0.1em] text-text-muted">Est. Cost This Month</span>
                      </div>
                      <p className="text-2xl font-bold text-text-heading">${usageStats.cost_this_month.toFixed(2)}</p>
                      <p className="text-[11px] text-text-muted mt-1">Total: ${usageStats.estimated_cost.toFixed(2)}</p>
                    </Card>

                    {/* Average tokens */}
                    <Card className="p-5">
                      <div className="flex items-center gap-2 mb-3">
                        <div className="w-8 h-8 rounded-lg bg-purple-500/15 flex items-center justify-center">
                          <TrendingUp size={16} className="text-purple-500" />
                        </div>
                        <span className="text-[10px] font-semibold uppercase tracking-[0.1em] text-text-muted">Avg Tokens / Analysis</span>
                      </div>
                      <p className="text-2xl font-bold text-text-heading">{formatNumber(usageStats.avg_tokens_per_analysis)}</p>
                      <p className="text-[11px] text-text-muted mt-1">{usageStats.total_analyses} total analyses</p>
                    </Card>
                  </div>

                  {/* Token usage breakdown */}
                  <Card className="p-6">
                    <div className="flex items-center gap-3 mb-5">
                      <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                        <Activity size={20} className="text-primary" />
                      </div>
                      <div>
                        <h2 className="text-base font-bold text-text-heading">Token Usage Overview</h2>
                        <p className="text-xs text-text-secondary">Detailed breakdown of your token consumption.</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
                      <div className="p-4 rounded-lg border border-border bg-bg-main/50">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-text-muted mb-1">Total Tokens Used</p>
                        <p className="text-lg font-bold text-text-heading">{formatNumber(usageStats.total_tokens)}</p>
                      </div>
                      <div className="p-4 rounded-lg border border-border bg-bg-main/50">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-text-muted mb-1">Monthly Limit</p>
                        <p className="text-lg font-bold text-text-heading">{formatNumber(usageStats.monthly_token_limit)}</p>
                      </div>
                      <div className="p-4 rounded-lg border border-border bg-bg-main/50">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-text-muted mb-1">Remaining</p>
                        <p className={`text-lg font-bold ${usageStats.monthly_token_limit - usageStats.tokens_this_month > 50000 ? "text-accent-green" : "text-negative"}`}>
                          {formatNumber(Math.max(0, usageStats.monthly_token_limit - usageStats.tokens_this_month))}
                        </p>
                      </div>
                    </div>

                    {/* Progress bar */}
                    <div className="mb-2">
                      <div className="flex justify-between text-[11px] text-text-muted mb-1">
                        <span>Monthly Token Usage</span>
                        <span>{((usageStats.tokens_this_month / usageStats.monthly_token_limit) * 100).toFixed(1)}%</span>
                      </div>
                      <div className="w-full h-3 rounded-full bg-border">
                        <div
                          className={`h-3 rounded-full transition-all ${
                            (usageStats.tokens_this_month / usageStats.monthly_token_limit) > 0.9
                              ? "bg-negative"
                              : (usageStats.tokens_this_month / usageStats.monthly_token_limit) > 0.7
                              ? "bg-yellow-500"
                              : "bg-primary"
                          }`}
                          style={{ width: `${Math.min(100, (usageStats.tokens_this_month / usageStats.monthly_token_limit) * 100)}%` }}
                        />
                      </div>
                    </div>
                  </Card>

                  {/* Recent usage table */}
                  <Card className="p-6">
                    <div className="flex items-center gap-3 mb-5">
                      <div className="w-10 h-10 rounded-xl bg-purple-500/15 flex items-center justify-center">
                        <Clock size={20} className="text-purple-500" />
                      </div>
                      <div>
                        <h2 className="text-base font-bold text-text-heading">Recent Activity</h2>
                        <p className="text-xs text-text-secondary">Your most recent analysis usage.</p>
                      </div>
                    </div>

                    {usageStats.recent_usage.length === 0 ? (
                      <div className="text-center py-8">
                        <BarChart3 size={32} className="mx-auto text-text-muted mb-3" />
                        <p className="text-sm text-text-secondary">No analyses yet. Run your first analysis to see usage data.</p>
                      </div>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="w-full text-[13px]">
                          <thead>
                            <tr className="border-b border-border">
                              <th className="text-left py-3 px-2 text-[10px] font-semibold uppercase tracking-[0.1em] text-text-muted">Analysis</th>
                              <th className="text-left py-3 px-2 text-[10px] font-semibold uppercase tracking-[0.1em] text-text-muted">Type</th>
                              <th className="text-right py-3 px-2 text-[10px] font-semibold uppercase tracking-[0.1em] text-text-muted">Tokens</th>
                              <th className="text-right py-3 px-2 text-[10px] font-semibold uppercase tracking-[0.1em] text-text-muted">Est. Cost</th>
                              <th className="text-right py-3 px-2 text-[10px] font-semibold uppercase tracking-[0.1em] text-text-muted">Date</th>
                            </tr>
                          </thead>
                          <tbody>
                            {usageStats.recent_usage.map((item) => (
                              <tr key={item.id} className="border-b border-border/50 hover:bg-bg-main/30">
                                <td className="py-3 px-2 text-text-primary font-medium max-w-[200px] truncate">{item.title}</td>
                                <td className="py-3 px-2">
                                  <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${
                                    item.type === "MARKET"
                                      ? "bg-primary/10 text-primary"
                                      : "bg-accent-green/10 text-accent-green"
                                  }`}>
                                    {item.type === "MARKET" ? "Market" : "Business"}
                                  </span>
                                </td>
                                <td className="py-3 px-2 text-right text-text-secondary">{formatNumber(item.tokens)}</td>
                                <td className="py-3 px-2 text-right text-text-secondary">${item.cost.toFixed(4)}</td>
                                <td className="py-3 px-2 text-right text-text-muted">{formatDate(item.created_at)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </Card>
                </>
              )}

              {!usageLoading && !usageStats && (
                <Card className="p-12 text-center">
                  <Activity size={32} className="mx-auto text-text-muted mb-3" />
                  <p className="text-sm text-text-secondary">Unable to load usage data. Please try again later.</p>
                </Card>
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}