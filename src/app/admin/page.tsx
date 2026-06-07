"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  ShieldCheck,
  Users,
  UserCheck,
  UserX,
  Clock,
  Search,
  Loader2,
  Trash2,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
  BarChart3,
  Zap,
  DollarSign,
  FileText,
  X,
  Activity,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import {
  getAdminUsers,
  getAdminStats,
  updateAdminUser,
  deleteAdminUser,
  getUserUsageList,
  getUserUsageDetail,
  AdminUser,
  AdminStats,
  UserUsage,
  UserUsageDetail,
} from "@/lib/api";

const statusColors: Record<string, string> = {
  PENDING: "bg-amber-100 text-amber-700",
  APPROVED: "bg-emerald-100 text-emerald-700",
  REJECTED: "bg-red-100 text-red-700",
};

const roleColors: Record<string, string> = {
  ADMIN: "bg-purple-100 text-purple-700",
  USER: "bg-blue-100 text-blue-700",
};

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function formatCost(n: number): string {
  if (n < 0.01) return "$0.00";
  return `$${n.toFixed(2)}`;
}

/** Parse a naive-UTC ISO string from the backend as a proper UTC date */
function parseUTC(iso: string): Date {
  return new Date(iso.includes("Z") || iso.includes("+") ? iso : iso + "Z");
}

export default function AdminDashboardPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [usageData, setUsageData] = useState<UserUsage[]>([]);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState("");

  // User detail modal
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [userDetail, setUserDetail] = useState<UserUsageDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const perPage = 10;

  // Redirect non-admins
  useEffect(() => {
    if (!authLoading && (!user || user.role !== "ADMIN")) {
      router.push("/login");
    }
  }, [user, authLoading, router]);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [statsData, usersData, usage] = await Promise.all([
        getAdminStats(),
        getAdminUsers({
          page,
          per_page: perPage,
          search: search || undefined,
          status: filterStatus || undefined,
        }),
        getUserUsageList(),
      ]);
      setStats(statsData);
      setUsers(usersData.items);
      setTotalPages(usersData.total_pages);
      setUsageData(usage);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, [page, search, filterStatus]);

  useEffect(() => {
    if (user?.role === "ADMIN") {
      fetchData();
    }
  }, [user, fetchData]);

  // Load user detail when selected
  useEffect(() => {
    if (!selectedUserId) {
      setUserDetail(null);
      return;
    }
    (async () => {
      setDetailLoading(true);
      try {
        const detail = await getUserUsageDetail(selectedUserId);
        setUserDetail(detail);
      } catch {
        setUserDetail(null);
      } finally {
        setDetailLoading(false);
      }
    })();
  }, [selectedUserId]);

  // Merge usage data into users for the table
  const usageMap = new Map(usageData.map((u) => [u.user_id, u]));

  const handleStatusChange = async (userId: string, status: "PENDING" | "APPROVED" | "REJECTED") => {
    setActionLoading(userId);
    try {
      await updateAdminUser(userId, { status });
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update user");
    } finally {
      setActionLoading(null);
    }
  };

  const handleRoleChange = async (userId: string, role: "ADMIN" | "USER") => {
    setActionLoading(userId);
    try {
      await updateAdminUser(userId, { role });
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update role");
    } finally {
      setActionLoading(null);
    }
  };

  const handleToggleActive = async (userId: string, currentActive: boolean) => {
    setActionLoading(userId);
    try {
      await updateAdminUser(userId, { is_active: !currentActive });
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update user");
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (userId: string, userName: string) => {
    if (!confirm(`Are you sure you want to delete user "${userName}"? This cannot be undone.`)) return;
    setActionLoading(userId);
    try {
      await deleteAdminUser(userId);
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete user");
    } finally {
      setActionLoading(null);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchData();
  };

  if (authLoading || !user || user.role !== "ADMIN") {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-primary" size={32} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3 mb-1">
          <ShieldCheck size={24} className="text-amber-500" />
          <h1 className="text-2xl font-bold text-text-heading">Admin Dashboard</h1>
        </div>
        <p className="text-sm text-text-secondary">Manage users, approvals, and monitor system usage.</p>
      </div>

      {/* Error */}
      {error && (
        <div className="p-3 rounded-lg bg-negative/10 border border-negative/20 text-sm text-negative flex items-center gap-2">
          <AlertTriangle size={16} />
          {error}
          <button onClick={() => setError("")} className="ml-auto text-negative/60 hover:text-negative">✕</button>
        </div>
      )}

      {/* Stats Cards */}
      {stats && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <StatCard icon={Users} label="Total Users" value={stats.total_users} color="text-blue-600" bg="bg-blue-50" />
            <StatCard icon={Clock} label="Pending" value={stats.pending_users} color="text-amber-600" bg="bg-amber-50" />
            <StatCard icon={UserCheck} label="Approved" value={stats.approved_users} color="text-emerald-600" bg="bg-emerald-50" />
            <StatCard icon={UserX} label="Rejected" value={stats.rejected_users} color="text-red-600" bg="bg-red-50" />
            <StatCard icon={UserCheck} label="Active" value={stats.active_users} color="text-primary" bg="bg-indigo-50" />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard icon={FileText} label="Total Analyses" value={stats.total_analyses} color="text-violet-600" bg="bg-violet-50" />
            <StatCard icon={BarChart3} label="Completed" value={stats.completed_analyses} color="text-emerald-600" bg="bg-emerald-50" />
            <StatCard icon={Zap} label="Total Tokens" value={formatTokens(stats.total_tokens)} color="text-amber-600" bg="bg-amber-50" isText />
            <StatCard icon={DollarSign} label="Est. Cost" value={formatCost(stats.estimated_cost)} color="text-rose-600" bg="bg-rose-50" isText />
          </div>
        </>
      )}

      {/* Filters */}
      <div className="bg-white rounded-2xl border border-border shadow-card p-5">
        <form onSubmit={handleSearch} className="flex flex-wrap gap-3 items-center mb-4">
          <div className="flex-1 min-w-[200px] relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name or email..."
              className="w-full pl-9 pr-4 py-2.5 text-[13px] rounded-lg border border-border bg-bg-main placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/15 focus:border-primary/40"
            />
          </div>
          <select
            value={filterStatus}
            onChange={(e) => { setFilterStatus(e.target.value); setPage(1); }}
            className="px-4 py-2.5 text-[13px] rounded-lg border border-border bg-bg-main text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/15"
          >
            <option value="">All Statuses</option>
            <option value="PENDING">Pending</option>
            <option value="APPROVED">Approved</option>
            <option value="REJECTED">Rejected</option>
          </select>
          <button
            type="submit"
            className="px-5 py-2.5 rounded-lg bg-primary text-white text-[13px] font-semibold hover:bg-primary-hover transition-colors"
          >
            Search
          </button>
        </form>

        {/* Users Table */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="animate-spin text-primary" size={28} />
          </div>
        ) : users.length === 0 ? (
          <div className="text-center py-12 text-text-muted text-sm">
            No users found.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-[13px]">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-3 text-[10px] font-semibold uppercase tracking-wider text-text-muted">User</th>
                  <th className="text-left py-3 px-3 text-[10px] font-semibold uppercase tracking-wider text-text-muted">Status</th>
                  <th className="text-left py-3 px-3 text-[10px] font-semibold uppercase tracking-wider text-text-muted">Role</th>
                  <th className="text-center py-3 px-3 text-[10px] font-semibold uppercase tracking-wider text-text-muted">Reports</th>
                  <th className="text-center py-3 px-3 text-[10px] font-semibold uppercase tracking-wider text-text-muted">Tokens</th>
                  <th className="text-center py-3 px-3 text-[10px] font-semibold uppercase tracking-wider text-text-muted">Est. Cost</th>
                  <th className="text-left py-3 px-3 text-[10px] font-semibold uppercase tracking-wider text-text-muted">Last Activity</th>
                  <th className="text-center py-3 px-3 text-[10px] font-semibold uppercase tracking-wider text-text-muted">Active</th>
                  <th className="text-right py-3 px-3 text-[10px] font-semibold uppercase tracking-wider text-text-muted">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => {
                  const usage = usageMap.get(u.id);
                  return (
                    <tr key={u.id} className="border-b border-border-light hover:bg-bg-main/50 transition-colors">
                      <td className="py-3 px-3">
                        <button
                          onClick={() => setSelectedUserId(u.id)}
                          className="flex items-center gap-3 text-left hover:opacity-80 transition-opacity"
                        >
                          <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary text-xs font-bold">
                            {u.avatar_initials || "U"}
                          </div>
                          <div>
                            <p className="font-medium text-text-heading">{u.full_name}</p>
                            <p className="text-text-muted text-[11px]">{u.email}</p>
                          </div>
                        </button>
                      </td>
                      <td className="py-3 px-3">
                        <span className={`inline-flex px-2.5 py-1 rounded-full text-[11px] font-semibold ${statusColors[u.status] || "bg-gray-100 text-gray-700"}`}>
                          {u.status}
                        </span>
                      </td>
                      <td className="py-3 px-3">
                        <select
                          value={u.role}
                          onChange={(e) => handleRoleChange(u.id, e.target.value as "ADMIN" | "USER")}
                          disabled={actionLoading === u.id}
                          className={`text-[11px] font-semibold rounded-full px-2.5 py-1 border-0 cursor-pointer ${roleColors[u.role]}`}
                        >
                          <option value="USER">USER</option>
                          <option value="ADMIN">ADMIN</option>
                        </select>
                      </td>
                      <td className="py-3 px-3 text-center">
                        <div className="flex items-center justify-center gap-1.5">
                          <FileText size={12} className="text-text-muted" />
                          <span className="font-medium text-text-heading">{usage?.total_analyses ?? 0}</span>
                          {usage && usage.completed_analyses > 0 && (
                            <span className="text-[10px] text-emerald-600">({usage.completed_analyses}✓)</span>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-3 text-center">
                        <div className="flex items-center justify-center gap-1">
                          <Zap size={12} className="text-amber-500" />
                          <span className="font-medium text-text-heading">{usage ? formatTokens(usage.total_tokens) : "0"}</span>
                        </div>
                      </td>
                      <td className="py-3 px-3 text-center">
                        <span className="font-medium text-rose-600">{usage ? formatCost(usage.estimated_cost) : "$0.00"}</span>
                      </td>
                      <td className="py-3 px-3 text-text-muted text-[12px]">
                        {usage?.last_activity
                          ? parseUTC(usage.last_activity).toLocaleDateString() + " " + parseUTC(usage.last_activity).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                          : "—"
                        }
                      </td>
                      <td className="py-3 px-3 text-center">
                        <button
                          onClick={() => handleToggleActive(u.id, u.is_active)}
                          disabled={actionLoading === u.id}
                          className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors mx-auto ${u.is_active ? "bg-accent-green" : "bg-gray-300"}`}
                        >
                          <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${u.is_active ? "translate-x-4.5" : "translate-x-1"}`} />
                        </button>
                      </td>
                      <td className="py-3 px-3">
                        <div className="flex items-center justify-end gap-1.5">
                          {u.status !== "APPROVED" && (
                            <button
                              onClick={() => handleStatusChange(u.id, "APPROVED")}
                              disabled={actionLoading === u.id}
                              className="px-2.5 py-1.5 rounded-md bg-emerald-50 text-emerald-600 text-[11px] font-semibold hover:bg-emerald-100 transition-colors disabled:opacity-50"
                              title="Approve"
                            >
                              {actionLoading === u.id ? <Loader2 size={12} className="animate-spin" /> : "Approve"}
                            </button>
                          )}
                          {u.status !== "REJECTED" && (
                            <button
                              onClick={() => handleStatusChange(u.id, "REJECTED")}
                              disabled={actionLoading === u.id}
                              className="px-2.5 py-1.5 rounded-md bg-red-50 text-red-600 text-[11px] font-semibold hover:bg-red-100 transition-colors disabled:opacity-50"
                              title="Reject"
                            >
                              {actionLoading === u.id ? <Loader2 size={12} className="animate-spin" /> : "Reject"}
                            </button>
                          )}
                          <button
                            onClick={() => handleDelete(u.id, u.full_name)}
                            disabled={actionLoading === u.id}
                            className="p-1.5 rounded-md text-red-400 hover:bg-red-50 hover:text-red-600 transition-colors disabled:opacity-50"
                            title="Delete user"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-border-light">
            <p className="text-[12px] text-text-muted">
              Page {page} of {totalPages}
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="p-2 rounded-lg border border-border hover:bg-bg-main transition-colors disabled:opacity-40"
              >
                <ChevronLeft size={16} />
              </button>
              <button
                onClick={() => setPage(Math.min(totalPages, page + 1))}
                disabled={page === totalPages}
                className="p-2 rounded-lg border border-border hover:bg-bg-main transition-colors disabled:opacity-40"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* User Detail Modal */}
      {selectedUserId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40" onClick={() => setSelectedUserId(null)}>
          <div className="bg-white rounded-2xl border border-border shadow-2xl w-full max-w-2xl max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            {detailLoading ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 className="animate-spin text-primary" size={28} />
              </div>
            ) : userDetail ? (
              <div className="p-6">
                {/* Header */}
                <div className="flex items-start justify-between mb-5">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary text-sm font-bold">
                      {userDetail.full_name?.split(" ").map(n => n[0]).join("").slice(0, 2).toUpperCase() || "U"}
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-text-heading">{userDetail.full_name}</h3>
                      <p className="text-sm text-text-muted">{userDetail.email}</p>
                    </div>
                  </div>
                  <button onClick={() => setSelectedUserId(null)} className="p-1.5 rounded-lg hover:bg-bg-main transition-colors text-text-muted">
                    <X size={18} />
                  </button>
                </div>

                {/* User Stats */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
                  <div className="bg-violet-50 rounded-lg p-3 text-center">
                    <p className="text-lg font-bold text-violet-600">{userDetail.total_analyses}</p>
                    <p className="text-[10px] text-text-muted font-medium uppercase">Total Reports</p>
                  </div>
                  <div className="bg-emerald-50 rounded-lg p-3 text-center">
                    <p className="text-lg font-bold text-emerald-600">{userDetail.completed_analyses}</p>
                    <p className="text-[10px] text-text-muted font-medium uppercase">Completed</p>
                  </div>
                  <div className="bg-amber-50 rounded-lg p-3 text-center">
                    <p className="text-lg font-bold text-amber-600">{formatTokens(userDetail.total_tokens)}</p>
                    <p className="text-[10px] text-text-muted font-medium uppercase">Tokens Used</p>
                  </div>
                  <div className="bg-rose-50 rounded-lg p-3 text-center">
                    <p className="text-lg font-bold text-rose-600">{formatCost(userDetail.estimated_cost)}</p>
                    <p className="text-[10px] text-text-muted font-medium uppercase">Est. Cost</p>
                  </div>
                </div>

                {/* Failed/Processing counts */}
                {(userDetail.failed_analyses > 0 || userDetail.processing_analyses > 0) && (
                  <div className="flex items-center gap-4 mb-5 px-1">
                    {userDetail.failed_analyses > 0 && (
                      <span className="text-[12px] text-red-500 font-medium">{userDetail.failed_analyses} failed</span>
                    )}
                    {userDetail.processing_analyses > 0 && (
                      <span className="text-[12px] text-amber-500 font-medium">{userDetail.processing_analyses} processing</span>
                    )}
                    {userDetail.last_activity && (
                      <span className="text-[12px] text-text-muted ml-auto">
                        Last active: {parseUTC(userDetail.last_activity).toLocaleString()}
                      </span>
                    )}
                  </div>
                )}

                {/* Recent Analyses */}
                <div>
                  <h4 className="text-sm font-semibold text-text-heading mb-3 flex items-center gap-2">
                    <Activity size={14} />
                    Recent Analyses
                  </h4>
                  {userDetail.recent_analyses.length === 0 ? (
                    <p className="text-sm text-text-muted py-4 text-center">No analyses yet.</p>
                  ) : (
                    <div className="space-y-2">
                      {userDetail.recent_analyses.map((a) => (
                        <div key={a.id} className="flex items-center justify-between p-3 rounded-lg bg-bg-main border border-border-light">
                          <div className="min-w-0 flex-1">
                            <p className="text-[13px] font-medium text-text-heading truncate">{a.title}</p>
                            <div className="flex items-center gap-2 mt-0.5">
                              {a.analysis_type && (
                                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${a.analysis_type === "MARKET" ? "bg-emerald-100 text-emerald-700" : "bg-indigo-100 text-indigo-700"}`}>
                                  {a.analysis_type}
                                </span>
                              )}
                              {a.status && (
                                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                                  a.status === "COMPLETED" ? "bg-emerald-100 text-emerald-700" :
                                  a.status === "FAILED" ? "bg-red-100 text-red-700" :
                                  "bg-amber-100 text-amber-700"
                                }`}>
                                  {a.status}
                                </span>
                              )}
                              {a.created_at && (
                                <span className="text-[10px] text-text-muted">
                                  {parseUTC(a.created_at).toLocaleDateString()}
                                </span>
                              )}
                            </div>
                          </div>
                          <div className="text-right ml-3">
                            <p className="text-[12px] font-medium text-amber-600">{formatTokens(a.tokens)}</p>
                            <p className="text-[10px] text-text-muted">tokens</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="p-6 text-center text-text-muted">Failed to load user details.</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  color,
  bg,
  isText,
}: {
  icon: React.ComponentType<{ size?: number; className?: string }>;
  label: string;
  value: number | string;
  color: string;
  bg: string;
  isText?: boolean;
}) {
  return (
    <div className="bg-white rounded-2xl border border-border shadow-card p-4 flex items-center gap-3 transition-shadow hover:shadow-pop">
      <div className={`w-10 h-10 rounded-xl ${bg} flex items-center justify-center`}>
        <Icon size={18} className={color} />
      </div>
      <div>
        <p className={`text-xl font-bold text-text-heading ${isText ? "text-lg" : ""}`}>{value}</p>
        <p className="text-[11px] text-text-muted font-medium">{label}</p>
      </div>
    </div>
  );
}