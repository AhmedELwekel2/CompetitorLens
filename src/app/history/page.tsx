"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import TopBar from "@/components/TopBar";
import {
  Download,
  Plus,
  Calendar,
  ChevronLeft,
  ChevronRight,
  MoreVertical,
  Building2,
  TrendingUp,
  Clock,
  Globe,
  FileText,
  BarChart3,
  Target,
  Trash2,
  Loader2,
} from "lucide-react";
import {
  getHistory,
  getHistoryStats,
  deleteAnalysis,
  AnalysisRecord,
  HistoryStats,
} from "@/lib/api";

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`bg-bg-card rounded-xl border border-border ${className}`}>{children}</div>;
}

const typeIcons: Record<string, typeof BarChart3> = {
  MARKET: BarChart3,
  SINGLE: Building2,
};

type FilterType = "All" | "Market" | "Single";

export default function HistoryPage() {
  const [filter, setFilter] = useState<FilterType>("All");
  const [page, setPage] = useState(1);
  const [reports, setReports] = useState<AnalysisRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [stats, setStats] = useState<HistoryStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [menuOpen, setMenuOpen] = useState<string | null>(null);

  const perPage = 12;

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [historyRes, statsRes] = await Promise.all([
        getHistory({
          page,
          per_page: perPage,
          analysis_type: filter === "All" ? undefined : filter.toUpperCase(),
        }),
        getHistoryStats(),
      ]);
      setReports(historyRes.items);
      setTotal(historyRes.total);
      setTotalPages(historyRes.total_pages);
      setStats(statsRes);
    } catch {
      // If not authenticated, show empty
      setReports([]);
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, [page, filter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this analysis?")) return;
    try {
      await deleteAnalysis(id);
      fetchData();
    } catch {}
    setMenuOpen(null);
  };

  const formatDate = (iso: string) => {
    // Backend stores naive UTC timestamps (no timezone suffix).
    // Append 'Z' so JavaScript treats them as UTC and converts to local time correctly.
    const d = new Date(iso.includes("Z") || iso.includes("+") ? iso : iso + "Z");
    return d.toLocaleDateString("en-US", {
      month: "short", day: "numeric", year: "numeric",
    }) + " · " + d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
  };

  return (
    <>
      <TopBar placeholder="Search reports, entities, or dates..." hideActions />

      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold text-text-heading">Analysis History</h1>
          <p className="text-sm text-text-secondary mt-2 max-w-xl">
            Review and manage your complete historical archive of market sentiment reports.
          </p>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          <a href="/market-analysis" className="px-4 py-2.5 rounded-lg bg-primary text-white text-sm font-semibold hover:bg-primary-hover transition-colors flex items-center gap-2">
            <Plus size={15} /> New Analysis
          </a>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-5">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-1 text-[13px] text-text-secondary">
            <span className="font-medium mr-1">Type:</span>
            {(["All", "Market", "Single"] as FilterType[]).map((f) => (
              <button
                key={f}
                onClick={() => { setFilter(f); setPage(1); }}
                className={`px-3 py-1.5 rounded-md text-[12.5px] font-medium transition-colors ${
                  filter === f ? "bg-sidebar text-white" : "text-text-secondary hover:bg-bg-main"
                }`}
              >{f}</button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2 text-[13px] text-text-secondary">
          <span>Showing {reports.length ? (page - 1) * perPage + 1 : 0}-{Math.min(page * perPage, total)} of {total} reports</span>
          <div className="flex items-center gap-1 ml-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="w-8 h-8 rounded-lg border border-border flex items-center justify-center hover:bg-bg-main disabled:opacity-40"
            >
              <ChevronLeft size={14} />
            </button>
            <span className="w-8 h-8 rounded-lg bg-primary text-white flex items-center justify-center text-xs font-bold">{page}</span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="w-8 h-8 rounded-lg border border-border flex items-center justify-center hover:bg-bg-main disabled:opacity-40"
            >
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* Table */}
      <Card className="overflow-hidden mb-6">
        <div className="hidden sm:grid grid-cols-[2fr_0.7fr_1.2fr_0.8fr_0.4fr] gap-4 px-5 py-3 bg-bg-main border-b border-border text-[10px] font-semibold uppercase tracking-[0.1em] text-text-muted">
          <span>Report Name</span>
          <span>Type</span>
          <span>Date</span>
          <span>Status</span>
          <span>Actions</span>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 size={24} className="text-primary animate-spin" />
          </div>
        ) : reports.length === 0 ? (
          <div className="text-center py-16 text-text-muted text-sm">
            No analyses found. Run your first analysis to see results here.
          </div>
        ) : (
          reports.map((r, i) => {
            const Icon = typeIcons[r.analysis_type] || FileText;
            const isMarket = r.analysis_type === "MARKET";
            const isProcessing = r.status === "PROCESSING";
            const isFailed = r.status === "FAILED";
            return (
              <div
                key={r.id}
                className={`grid grid-cols-1 sm:grid-cols-[2fr_0.7fr_1.2fr_0.8fr_0.4fr] gap-2 sm:gap-4 px-5 py-4 items-center border-b border-border-light hover:bg-bg-main/50 transition-colors ${
                  i === reports.length - 1 ? "border-b-0" : ""
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-bg-main flex items-center justify-center flex-shrink-0">
                    <Icon size={15} className="text-text-secondary" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-[13px] font-semibold text-text-heading truncate">{r.title}</p>
                    <p className="text-[11px] text-text-muted truncate">{r.subtitle}</p>
                  </div>
                </div>

                <div>
                  <span className={`inline-block px-2.5 py-1 rounded text-[10px] font-bold uppercase tracking-wider ${
                    isMarket ? "bg-accent-green/15 text-accent-green" : "bg-single-badge/15 text-single-badge"
                  }`}>{r.analysis_type}</span>
                </div>

                <span className="text-xs text-text-secondary">{formatDate(r.created_at)}</span>

                <div className="flex items-center gap-1.5">
                  {isProcessing ? (
                    <>
                      <Loader2 size={12} className="text-primary animate-spin" />
                      <span className="text-xs font-medium text-primary">Processing</span>
                    </>
                  ) : isFailed ? (
                    <>
                      <span className="w-2 h-2 rounded-full bg-negative" />
                      <span className="text-xs font-medium text-negative">Failed</span>
                    </>
                  ) : (
                    <>
                      <span className="w-2 h-2 rounded-full bg-positive" />
                      <span className="text-xs font-medium text-positive">Completed</span>
                    </>
                  )}
                </div>

                <div className="relative">
                  <button
                    onClick={() => setMenuOpen(menuOpen === r.id ? null : r.id)}
                    className="w-8 h-8 rounded-lg hover:bg-bg-main flex items-center justify-center text-text-muted hover:text-text-primary ml-auto sm:ml-0"
                  >
                    <MoreVertical size={16} />
                  </button>
                  {menuOpen === r.id && (
                    <div className="absolute right-0 top-9 w-36 bg-white border border-border rounded-lg shadow-lg z-10 py-1">
                      <Link
                        href={`/history/${r.id}`}
                        onClick={() => setMenuOpen(null)}
                        className="block w-full text-left px-3 py-2 text-xs text-text-primary hover:bg-bg-main"
                      >
                        View
                      </Link>
                      <button
                        onClick={() => handleDelete(r.id)}
                        className="w-full text-left px-3 py-2 text-xs text-negative hover:bg-bg-main flex items-center gap-2"
                      >
                        <Trash2 size={13} /> Delete
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-5 py-3 border-t border-border">
            <span className="text-xs text-text-muted">Page {page} of {totalPages}</span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="px-4 py-2 rounded-lg border border-border text-xs font-medium text-text-muted disabled:opacity-40"
              >Previous</button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="px-4 py-2 rounded-lg border border-border text-xs font-medium text-text-heading hover:bg-bg-main disabled:opacity-40"
              >Next</button>
            </div>
          </div>
        )}
      </Card>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="p-5">
          <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-text-muted">Total Reports</span>
          <p className="text-3xl font-bold text-text-heading mt-1">{stats?.total_reports ?? 0}</p>
          {stats && stats.growth_pct !== 0 && (
            <div className={`flex items-center gap-1.5 mt-2 text-xs font-medium ${stats.growth_pct > 0 ? "text-accent-green" : "text-negative"}`}>
              <TrendingUp size={13} />
              {stats.growth_pct > 0 ? "+" : ""}{stats.growth_pct}% from last month
            </div>
          )}
        </Card>
        <Card className="p-5">
          <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-text-muted">Competitors Analyzed</span>
          <p className="text-3xl font-bold text-text-heading mt-1">{stats?.total_competitors_analyzed ?? 0}</p>
          <div className="flex items-center gap-1.5 mt-2 text-xs text-text-muted">
            <Clock size={13} /> Across all sessions
          </div>
        </Card>
        <Card className="p-5 relative overflow-hidden">
          <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-text-muted">Active Monitoring</span>
          <p className="text-3xl font-bold text-text-heading mt-1">{stats?.active_monitoring ?? 0} Entities</p>
          <div className="flex items-center gap-2 mt-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-primary text-white">LIVE</span>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-sidebar text-white">TRACKING</span>
          </div>
          <div className="absolute -bottom-4 -right-4 w-20 h-20 rounded-full border-4 border-border-light opacity-50" />
          <div className="absolute -bottom-6 -right-6 w-24 h-24 rounded-full border-4 border-border-light opacity-30" />
        </Card>
      </div>
    </>
  );
}
