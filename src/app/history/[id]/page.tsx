"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import TopBar from "@/components/TopBar";
import MarkdownRenderer from "@/components/MarkdownRenderer";
import {
  ArrowLeft,
  BarChart3,
  Building2,
  Loader2,
  Star,
  Users,
  ExternalLink,
  ShieldCheck,
} from "lucide-react";
import { getAnalysis, AnalysisRecord } from "@/lib/api";

/* ── Types ────────────────────────────────────────────────────────────────── */

type CompetitorFromDB = {
  id: string;
  name: string;
  address: string;
  google_maps_url: string;
  google_rating: number;
  total_reviews: number;
  positive_pct: number;
  negative_pct: number;
  neutral_pct: number;
  avg_polarity: number;
  gm_reviews_count: number;
  trustpilot_url: string;
  trustpilot_rating: string | null;
  trust_score: string | null;
  trustpilot_reviews_count: number;
  ai_insights: string;
};

type AnalysisDetail = AnalysisRecord & {
  competitors: CompetitorFromDB[];
};

type ResultPayload = {
  analysisTitle?: string | null;
  competitorsAnalyzedNumber?: number | null;
  totalReview?: number | null;
  avgGoogleRating?: number | null;
  competitorsAnalyzed?: Array<Record<string, unknown>> | null;
  competitorsDetails?: Array<Record<string, unknown>> | null;
  competitorSentimentComparisonChart?: Array<Record<string, unknown>> | null;
  reviewsAnalyzedPerCompetitor?: Array<Record<string, unknown>> | null;
  pieChart?: {
    title: string | null;
    positive: number | null;
    negative: number | null;
    neutral: number | null;
  } | null;
  trustpilotData?: Array<Record<string, unknown>> | null;
};

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`bg-bg-card rounded-xl border border-border ${className}`}>{children}</div>;
}

/* ── Page ──────────────────────────────────────────────────────────────────── */

export default function HistoryDetailPage() {
  const params = useParams();
  const id = String(params?.id || "");
  const [report, setReport] = useState<AnalysisDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getAnalysis(id)
      .then((res) => setReport(res as AnalysisDetail))
      .catch((err) => setError(err?.message || "Failed to load report."))
      .finally(() => setLoading(false));
  }, [id]);

  const result = (report?.result_data || {}) as ResultPayload;
  const dbCompetitors = report?.competitors || [];

  // Prefer result_data for KPIs, fall back to DB competitor aggregation
  const competitorsCount =
    result.competitorsAnalyzedNumber ?? dbCompetitors.length ?? 0;
  const totalReviews =
    result.totalReview ??
    dbCompetitors.reduce((sum, c) => sum + (c.total_reviews || 0), 0);
  const avgRating =
    result.avgGoogleRating ??
    (dbCompetitors.length
      ? (
          dbCompetitors.reduce((s, c) => s + (c.google_rating || 0), 0) /
          dbCompetitors.length
        ).toFixed(1)
      : 0);

  return (
    <>
      <TopBar placeholder="Search reports..." hideActions />

      <div className="mb-6 flex items-center gap-3">
        <Link
          href="/history"
          className="inline-flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary"
        >
          <ArrowLeft size={16} /> Back to History
        </Link>
      </div>

      {loading ? (
        <Card className="p-10 flex items-center justify-center">
          <Loader2 size={24} className="text-primary animate-spin" />
        </Card>
      ) : error ? (
        <Card className="p-6">
          <div className="flex flex-col items-center text-center py-8">
            <p className="text-negative font-medium mb-2">{error}</p>
            <p className="text-xs text-text-muted">
              The report may have been deleted or the server is unavailable.
            </p>
          </div>
        </Card>
      ) : report ? (
        <div className="space-y-6">
          {/* Header */}
          <div>
            <h1 className="text-2xl font-bold text-text-heading">{report.title}</h1>
            <p className="text-sm text-text-secondary mt-1">{report.subtitle}</p>
          </div>

          {/* KPI row */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card className="p-5">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Users size={18} className="text-primary" />
                </div>
                <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-text-muted">
                  Competitors
                </span>
              </div>
              <p className="text-3xl font-bold text-text-heading">{competitorsCount}</p>
            </Card>
            <Card className="p-5">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-9 h-9 rounded-lg bg-accent-green/10 flex items-center justify-center">
                  <BarChart3 size={18} className="text-accent-green" />
                </div>
                <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-text-muted">
                  Reviews
                </span>
              </div>
              <p className="text-3xl font-bold text-text-heading">{totalReviews}</p>
            </Card>
            <Card className="p-5">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-9 h-9 rounded-lg bg-amber-50 flex items-center justify-center">
                  <Star size={18} className="text-amber-500" />
                </div>
                <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-text-muted">
                  Avg Rating
                </span>
              </div>
              <p className="text-3xl font-bold text-text-heading">{avgRating}</p>
            </Card>
          </div>

          {/* Sentiment bar from result_data pieChart */}
          {result.pieChart && result.pieChart.positive != null && (
            <Card className="p-5">
              <h3 className="text-sm font-bold text-text-heading mb-3">
                {result.pieChart.title || "Sentiment Distribution"}
              </h3>
              <div className="h-4 rounded-full overflow-hidden flex bg-bg-main mb-3">
                <div className="bg-positive h-full" style={{ width: `${result.pieChart.positive}%` }} />
                <div className="bg-neutral h-full" style={{ width: `${result.pieChart.neutral}%` }} />
                <div className="bg-negative h-full" style={{ width: `${result.pieChart.negative}%` }} />
              </div>
              <div className="flex gap-4 text-xs text-text-secondary">
                <span>
                  <span className="inline-block w-2 h-2 rounded-full bg-positive mr-1" />
                  Positive: {result.pieChart.positive?.toFixed(1)}%
                </span>
                <span>
                  <span className="inline-block w-2 h-2 rounded-full bg-neutral mr-1" />
                  Neutral: {result.pieChart.neutral?.toFixed(1)}%
                </span>
                <span>
                  <span className="inline-block w-2 h-2 rounded-full bg-negative mr-1" />
                  Negative: {result.pieChart.negative?.toFixed(1)}%
                </span>
              </div>
            </Card>
          )}

          {/* Competitor cards from DB competitors */}
          {dbCompetitors.length > 0 && (
            <Card className="p-6">
              <h2 className="text-sm font-bold text-text-heading mb-4">
                Competitors
              </h2>
              <div className="space-y-4">
                {dbCompetitors.map((comp) => (
                  <div
                    key={comp.id}
                    className="p-4 rounded-lg bg-bg-main border border-border-light"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-xs font-semibold text-primary">
                        {comp.name}
                      </p>
                      <div className="flex items-center gap-2">
                        {comp.google_maps_url && (
                          <a
                            href={comp.google_maps_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-[10px] text-blue-600 hover:text-blue-700"
                          >
                            <ExternalLink size={10} /> Maps
                          </a>
                        )}
                        {comp.trustpilot_url && (
                          <a
                            href={comp.trustpilot_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-[10px] text-emerald-600 hover:text-emerald-700"
                          >
                            <ShieldCheck size={10} /> Trustpilot
                          </a>
                        )}
                      </div>
                    </div>

                    {/* Rating / reviews row */}
                    <div className="flex items-center gap-4 mb-3 text-[11px] text-text-muted">
                      <span className="flex items-center gap-1">
                        <Star size={10} className="text-amber-500" />{" "}
                        {comp.google_rating}
                      </span>
                      <span>{comp.total_reviews} reviews</span>
                      {comp.address && <span>{comp.address}</span>}
                      {comp.trustpilot_rating && (
                        <span className="text-emerald-600 font-medium flex items-center gap-1">
                          <ShieldCheck size={10} /> TP: {comp.trustpilot_rating}
                        </span>
                      )}
                    </div>

                    {/* Sentiment bar for this competitor */}
                    <div className="h-2.5 rounded-full overflow-hidden flex bg-bg-card mb-3">
                      <div
                        className="bg-positive h-full"
                        style={{ width: `${comp.positive_pct}%` }}
                      />
                      <div
                        className="bg-neutral h-full"
                        style={{ width: `${comp.neutral_pct}%` }}
                      />
                      <div
                        className="bg-negative h-full"
                        style={{ width: `${comp.negative_pct}%` }}
                      />
                    </div>
                    <div className="flex gap-3 text-[10px] text-text-muted mb-3">
                      <span className="text-positive font-medium">
                        +{comp.positive_pct.toFixed(1)}%
                      </span>
                      <span className="text-neutral font-medium">
                        {comp.neutral_pct.toFixed(1)}%
                      </span>
                      <span className="text-negative font-medium">
                        -{comp.negative_pct.toFixed(1)}%
                      </span>
                    </div>

                    {/* AI Insights rendered as Markdown */}
                    {comp.ai_insights && (
                      <div className="pt-3 border-t border-border-light">
                        <MarkdownRenderer content={comp.ai_insights} />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Fallback: try result_data competitors if DB has none */}
          {!dbCompetitors.length &&
            result.competitorsAnalyzed &&
            result.competitorsAnalyzed.length > 0 && (
              <Card className="p-6">
                <h2 className="text-sm font-bold text-text-heading mb-4">
                  Competitors
                </h2>
                <div className="space-y-4">
                  {result.competitorsAnalyzed.map((comp, idx) => {
                    const detail =
                      (result.competitorsDetails?.[idx] || {}) as Record<
                        string,
                        unknown
                      >;
                    const name = String(
                      (comp as Record<string, unknown>).name ||
                        `Competitor ${idx + 1}`
                    );
                    const aiInsights = String(
                      (detail as Record<string, unknown>).aiInsights || ""
                    );
                    const googleMaps = String(
                      (detail as Record<string, unknown>).googleMaps || ""
                    );
                    const trustpilotUrl = String(
                      (detail as Record<string, unknown>).trustpilotUrl || ""
                    );
                    return (
                      <div
                        key={idx}
                        className="p-4 rounded-lg bg-bg-main border border-border-light"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <p className="text-xs font-semibold text-primary">
                            {name}
                          </p>
                          <div className="flex items-center gap-2">
                            {googleMaps && (
                              <a
                                href={googleMaps}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-[10px] text-blue-600 hover:text-blue-700"
                              >
                                <ExternalLink size={10} /> Maps
                              </a>
                            )}
                            {trustpilotUrl && (
                              <a
                                href={trustpilotUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-[10px] text-emerald-600 hover:text-emerald-700"
                              >
                                <ExternalLink size={10} /> Trustpilot
                              </a>
                            )}
                          </div>
                        </div>
                        {aiInsights && <MarkdownRenderer content={aiInsights} />}
                      </div>
                    );
                  })}
                </div>
              </Card>
            )}

          {/* No data at all */}
          {!dbCompetitors.length &&
            !result.competitorsAnalyzed?.length && (
              <Card className="p-6">
                <div className="text-sm text-text-muted text-center py-8">
                  No competitor data was saved for this report.
                </div>
              </Card>
            )}
        </div>
      ) : null}
    </>
  );
}