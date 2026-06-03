"use client";

import TopBar from "@/components/TopBar";
import {
  ArrowRight,
  Settings2,
  ShieldCheck,
  Lightbulb,
  Building2,
  Coffee,
  Dumbbell,
  ChevronDown,
  Loader2,
  XCircle,
  CheckCircle2,
  Star,
  BarChart3,
} from "lucide-react";
import { useState } from "react";
import { useAnalysis } from "@/lib/analysis-context";
import MarkdownRenderer from "@/components/MarkdownRenderer";

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`bg-bg-card rounded-xl border border-border ${className}`}>{children}</div>;
}

const recentEntities = [
  { name: "Global Tech Solutions", time: "Analyzed 2h ago", icon: Building2 },
  { name: "The Roasting Hub", time: "Analyzed yesterday", icon: Coffee },
  { name: "Apex Fitness Center", time: "Analyzed 3d ago", icon: Dumbbell },
];

export default function BusinessAnalysisPage() {
  const [depth, setDepth] = useState<"standard" | "sentiment">("standard");
  const [url, setUrl] = useState("");
  const [maxReviews, setMaxReviews] = useState("100");
  const { business, startBusinessAnalysis, cancelAnalysis, resetAnalysis } = useAnalysis();

  const loading = business.loading;
  const error = business.error;
  const data = business.data;
  const completed = business.completed;

  const handleRun = () => {
    if (!url.trim()) return;
    startBusinessAnalysis(
      {
        google_maps_url: url.trim(),
        max_reviews: parseInt(maxReviews) || 200,
      },
      { url: url.trim(), maxReviews: parseInt(maxReviews) || 200, depth }
    );
  };

  const handleCancel = () => {
    cancelAnalysis("BUSINESS");
  };

  const handleNewAnalysis = () => {
    resetAnalysis("BUSINESS");
  };

  const hasResults = data && data.competitorsAnalyzed && data.competitorsAnalyzed.length > 0;

  return (
    <>
      <TopBar placeholder="Search insights..." />

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text-heading">Single Business Analysis</h1>
        <p className="text-sm text-text-secondary mt-2 max-w-2xl">
          Extract high-fidelity competitive intelligence from any Google Maps listing.
          Our AI-driven engine analyzes sentiment, peak hours, and customer pain points.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)] gap-6 mb-8">
        {/* Left: form + results */}
        <div className="space-y-6">
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                <Settings2 size={20} className="text-primary" />
              </div>
              <div>
                <h2 className="text-base font-bold text-text-heading">Analysis Parameters</h2>
                <p className="text-xs text-text-secondary">Configure the target entity details below</p>
              </div>
            </div>

            <div className="mb-5">
              <label className="text-[10px] font-semibold uppercase tracking-[0.12em] text-text-muted block mb-2">
                Google Maps Business URL
              </label>
              <input
                type="url"
                placeholder="https://www.google.com/maps/place/..."
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                disabled={loading}
                className="w-full px-4 py-3 text-[13.5px] rounded-lg border border-border bg-bg-main placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/15 focus:border-primary/40"
              />
              <p className="text-[11px] text-text-muted mt-1.5">
                Ensure the URL includes the CID or place ID for accurate mapping.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
              <div>
                <label className="text-[10px] font-semibold uppercase tracking-[0.12em] text-text-muted block mb-2">
                  Max Reviews (Optional)
                </label>
                <div className="relative">
                  <select
                    value={maxReviews}
                    onChange={(e) => setMaxReviews(e.target.value)}
                    disabled={loading}
                    className="w-full px-4 py-3 text-[13.5px] rounded-lg border border-border bg-white text-text-primary appearance-none focus:outline-none focus:ring-2 focus:ring-primary/15 focus:border-primary/40"
                  >
                    <option value="100">Last 100 Reviews</option>
                    <option value="250">Last 250 Reviews</option>
                    <option value="500">Last 500 Reviews</option>
                  </select>
                  <ChevronDown size={16} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none" />
                </div>
              </div>
              <div>
                <label className="text-[10px] font-semibold uppercase tracking-[0.12em] text-text-muted block mb-2">
                  Analysis Depth
                </label>
                <div className="flex border border-border rounded-lg overflow-hidden">
                  <button
                    onClick={() => setDepth("standard")}
                    disabled={loading}
                    className={`flex-1 py-3 text-[13px] font-medium transition-colors ${
                      depth === "standard" ? "bg-white text-text-heading shadow-sm" : "bg-bg-main text-text-muted hover:text-text-secondary"
                    }`}
                  >Standard</button>
                  <button
                    onClick={() => setDepth("sentiment")}
                    disabled={loading}
                    className={`flex-1 py-3 text-[13px] font-medium transition-colors ${
                      depth === "sentiment" ? "bg-white text-text-heading shadow-sm" : "bg-bg-main text-text-muted hover:text-text-secondary"
                    }`}
                  >Sentiment Focus</button>
                </div>
              </div>
            </div>

            {loading ? (
              <button
                onClick={handleCancel}
                className="w-full py-4 rounded-lg bg-negative text-white text-sm font-bold uppercase tracking-wider hover:bg-red-600 transition-colors flex items-center justify-center gap-3"
              >
                <XCircle size={18} /> Cancel Analysis
              </button>
            ) : completed && hasResults ? (
              <button
                onClick={handleNewAnalysis}
                className="w-full py-4 rounded-lg bg-primary text-white text-sm font-bold uppercase tracking-wider hover:bg-primary-hover transition-colors flex items-center justify-center gap-3"
              >
                <ArrowRight size={18} /> New Analysis
              </button>
            ) : (
              <button
                onClick={handleRun}
                disabled={!url.trim() || loading}
                className="w-full py-4 rounded-lg bg-primary text-white text-sm font-bold uppercase tracking-wider hover:bg-primary-hover transition-colors flex items-center justify-center gap-3 disabled:opacity-50"
              >
                Run Competitive Analysis <ArrowRight size={18} />
              </button>
            )}
          </Card>

          {/* Error */}
          {error && (
            <Card className="p-5 border-negative/30 bg-negative/5">
              <div className="flex items-center gap-3 text-negative">
                <XCircle size={20} />
                <p className="text-sm font-medium">{error}</p>
              </div>
            </Card>
          )}

          {/* Results */}
          {hasResults && (
            <>
              {completed && (
                <div className="flex items-center gap-2 text-accent-green">
                  <CheckCircle2 size={18} />
                  <span className="text-sm font-semibold">Analysis Complete</span>
                </div>
              )}

              {data!.analysisTitle && (
                <h2 className="text-lg font-bold text-text-heading">{data!.analysisTitle}</h2>
              )}

              {/* KPI row */}
              <div className="grid grid-cols-3 gap-3">
                <Card className="p-4 text-center">
                  <Star size={18} className="text-amber-500 mx-auto mb-1" />
                  <p className="text-2xl font-bold text-text-heading">{data!.avgGoogleRating}</p>
                  <p className="text-[10px] text-text-muted uppercase">Rating</p>
                </Card>
                <Card className="p-4 text-center">
                  <BarChart3 size={18} className="text-primary mx-auto mb-1" />
                  <p className="text-2xl font-bold text-text-heading">{data!.totalReview}</p>
                  <p className="text-[10px] text-text-muted uppercase">Reviews</p>
                </Card>
                <Card className="p-4 text-center">
                  <Building2 size={18} className="text-accent-green mx-auto mb-1" />
                  <p className="text-2xl font-bold text-text-heading">{data!.competitorsAnalyzedNumber}</p>
                  <p className="text-[10px] text-text-muted uppercase">Entity</p>
                </Card>
              </div>

              {/* Sentiment bar */}
              {data!.pieChart && data!.pieChart.positive != null && (
                <Card className="p-5">
                  <h3 className="text-sm font-bold text-text-heading mb-3">{data!.pieChart.title}</h3>
                  <div className="h-4 rounded-full overflow-hidden flex bg-bg-main mb-3">
                    <div className="bg-positive h-full" style={{ width: `${data!.pieChart.positive}%` }} />
                    <div className="bg-neutral h-full" style={{ width: `${data!.pieChart.neutral}%` }} />
                    <div className="bg-negative h-full" style={{ width: `${data!.pieChart.negative}%` }} />
                  </div>
                  <div className="flex gap-4 text-xs text-text-secondary">
                    <span><span className="inline-block w-2 h-2 rounded-full bg-positive mr-1" />Positive: {data!.pieChart.positive?.toFixed(1)}%</span>
                    <span><span className="inline-block w-2 h-2 rounded-full bg-neutral mr-1" />Neutral: {data!.pieChart.neutral?.toFixed(1)}%</span>
                    <span><span className="inline-block w-2 h-2 rounded-full bg-negative mr-1" />Negative: {data!.pieChart.negative?.toFixed(1)}%</span>
                  </div>
                </Card>
              )}

              {/* AI Insights */}
              {data!.competitorsDetails?.some((d) => d.aiInsights) && (
                <Card className="p-5">
                  <h3 className="text-sm font-bold text-text-heading mb-3">AI-Powered Insights</h3>
                  {data!.competitorsDetails!.filter((d) => d.aiInsights).map((d, i) => (
                    <MarkdownRenderer key={i} content={d.aiInsights} />
                  ))}
                </Card>
              )}
            </>
          )}

          {/* Tips */}
          {!hasResults && !loading && !error && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Card className="p-5 flex gap-3">
                <Lightbulb size={18} className="text-accent-green flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="text-sm font-bold text-text-heading mb-1">Precision Tip</h3>
                  <p className="text-xs text-text-secondary leading-relaxed">
                    For local competitors, use the "Full History" option to uncover seasonal service fluctuations.
                  </p>
                </div>
              </Card>
              <Card className="p-5 flex gap-3">
                <ShieldCheck size={18} className="text-accent-green flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="text-sm font-bold text-text-heading mb-1">Data Privacy</h3>
                  <p className="text-xs text-text-secondary leading-relaxed">
                    All scraped data is anonymized and stored in your private vault. We never share your analysis targets.
                  </p>
                </div>
              </Card>
            </div>
          )}
        </div>

        {/* Right sidebar */}
        <div className="space-y-6">
          <div className="rounded-xl overflow-hidden bg-gradient-to-br from-sidebar to-sidebar/90 p-6 text-white">
            <div className="w-full h-24 rounded-lg bg-white/5 mb-4 flex items-center justify-center">
              <div className="grid grid-cols-3 gap-1 opacity-40">
                {Array.from({ length: 9 }).map((_, i) => (
                  <div key={i} className="w-4 h-4 rounded bg-accent-green/40" />
                ))}
              </div>
            </div>
            <h3 className="text-lg font-bold mb-2">Advanced Sentiment Engine</h3>
            <p className="text-sm text-white/70 leading-relaxed">
              Uncover the "why" behind the star ratings using NLP models trained for B2B intelligence.
            </p>
          </div>

          <Card className="p-5">
            <div className="flex items-center justify-between mb-4">
              <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-text-muted">Recent Entities</span>
              <button className="text-xs font-semibold text-primary hover:underline">View All</button>
            </div>
            <div className="space-y-3.5">
              {recentEntities.map((e) => {
                const Icon = e.icon;
                return (
                  <div key={e.name} className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-bg-main flex items-center justify-center flex-shrink-0">
                      <Icon size={16} className="text-text-secondary" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-[13px] font-medium text-text-heading truncate">{e.name}</p>
                      <p className="text-[11px] text-text-muted">{e.time}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>
      </div>

      {/* Process steps */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-8">
        {[
          { num: "01", title: "Data Extraction", desc: "We retrieve structured data from the GMB listing, including reviews, attributes, and user-submitted photos." },
          { num: "02", title: "Sentiment Scoring", desc: "Our NLP model scores individual reviews based on service quality, pricing perception, and staff interactions." },
          { num: "03", title: "Opportunity Mapping", desc: "We cross-reference competitors to find gaps in the market where your competitor is failing and you can excel." },
        ].map((s) => (
          <div key={s.num}>
            <span className="text-3xl font-bold text-primary/20">{s.num}</span>
            <h3 className="text-xs font-bold uppercase tracking-wider text-text-heading mt-1 mb-2">{s.title}</h3>
            <p className="text-xs text-text-secondary leading-relaxed">{s.desc}</p>
          </div>
        ))}
      </div>
    </>
  );
}