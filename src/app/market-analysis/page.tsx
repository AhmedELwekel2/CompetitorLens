"use client";

import { useState } from "react";
import TopBar from "@/components/TopBar";
import {
  Zap,
  Lightbulb,
  Globe,
  Clock,
  Building2,
  TrendingUp,
  Search as SearchIcon,
  Loader2,
  CheckCircle2,
  XCircle,
  BarChart3,
  Users,
  Star,
  ExternalLink,
  ShieldCheck,
  MessageSquare,
} from "lucide-react";
import { useAnalysis } from "@/lib/analysis-context";
import MarkdownRenderer from "@/components/MarkdownRenderer";

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`bg-bg-card rounded-xl border border-border ${className}`}>{children}</div>;
}

export default function MarketAnalysisPage() {
  const [industry, setIndustry] = useState("");
  const [country, setCountry] = useState("");
  const { market, startMarketAnalysis, cancelAnalysis, resetAnalysis } = useAnalysis();

  const loading = market.loading;
  const error = market.error;
  const data = market.data;
  const completed = market.completed;

  const handleRun = () => {
    if (!industry.trim()) return;
    const countryLabel = country.trim() || "Global";
    startMarketAnalysis(
      {
        industry: industry.trim(),
        country: countryLabel,
      },
      { countryLabel }
    );
  };

  const handleCancel = () => {
    cancelAnalysis("MARKET");
  };

  const handleNewAnalysis = () => {
    resetAnalysis("MARKET");
  };

  const hasResults = data && data.competitorsAnalyzed && data.competitorsAnalyzed.length > 0;

  return (
    <>
      <TopBar placeholder="Search insights or reports..." hideActions />

      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text-heading">Market Analysis</h1>
        <p className="text-sm text-text-secondary mt-2 max-w-2xl">
          Leverage real-time intelligence to dissect industry trends, competitor
          movements, and emerging market opportunities.
        </p>
      </div>

      {/* Input bar */}
      <Card className="p-6 mb-6">
        <div className="flex flex-col md:flex-row gap-4 items-end">
          <div className="flex-1 w-full">
            <label className="text-[10px] font-semibold uppercase tracking-[0.12em] text-text-muted block mb-2">
              Industry / Business Type
            </label>
            <div className="relative">
              <Building2 size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-text-muted" />
              <input
                type="text"
                placeholder="e.g. Fintech, Sustainable Fashion, SaaS"
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleRun()}
                className="w-full pl-10 pr-4 py-3 text-[13.5px] rounded-lg border border-border bg-white placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/15 focus:border-primary/40"
                disabled={loading}
              />
            </div>
          </div>

          <div className="md:w-56 w-full">
            <label className="text-[10px] font-semibold uppercase tracking-[0.12em] text-text-muted block mb-2">
              Country / Region
            </label>
            <div className="relative">
              <Globe size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-text-muted" />
              <input
                type="text"
                placeholder="e.g. Global, United Kingdom, Egypt"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleRun()}
                disabled={loading}
                className="w-full pl-10 pr-4 py-3 text-[13.5px] rounded-lg border border-border bg-white placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/15 focus:border-primary/40"
              />
            </div>
          </div>

          {loading ? (
            <button
              onClick={handleCancel}
              className="w-full md:w-auto px-8 py-3 rounded-lg bg-negative text-white text-sm font-semibold hover:bg-red-600 transition-colors flex items-center justify-center gap-2 flex-shrink-0"
            >
              <XCircle size={16} /> Cancel
            </button>
          ) : completed && hasResults ? (
            <button
              onClick={handleNewAnalysis}
              className="w-full md:w-auto px-8 py-3 rounded-lg bg-primary text-white text-sm font-semibold hover:bg-primary-hover transition-colors flex items-center justify-center gap-2 flex-shrink-0"
            >
              <Zap size={16} /> New Analysis
            </button>
          ) : (
            <button
              onClick={handleRun}
              disabled={!industry.trim()}
              className="w-full md:w-auto px-8 py-3 rounded-lg bg-primary text-white text-sm font-semibold hover:bg-primary-hover transition-colors flex items-center justify-center gap-2 flex-shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Zap size={16} /> Run Analysis
            </button>
          )}
        </div>
      </Card>

      {/* Error */}
      {error && (
        <Card className="p-5 mb-6 border-negative/30 bg-negative/5">
          <div className="flex items-center gap-3 text-negative">
            <XCircle size={20} />
            <p className="text-sm font-medium">{error}</p>
          </div>
        </Card>
      )}

      {/* Loading state */}
      {loading && !hasResults && (
        <Card className="p-8 mb-6">
          <div className="flex flex-col items-center text-center py-8">
            <Loader2 size={40} className="text-primary animate-spin mb-4" />
            <h2 className="text-lg font-bold text-text-heading mb-2">Analyzing {industry}...</h2>
            <p className="text-sm text-text-secondary max-w-md">
              {data?.analysisTitle
                ? `Processing: ${data.analysisTitle}`
                : "Scanning competitive landscapes, pricing models, and sentiment trends..."}
            </p>
          </div>
        </Card>
      )}

      {/* Results */}
      {hasResults && (
        <>
          {/* Status banner */}
          {completed && (
            <div className="flex items-center gap-2 mb-4 text-accent-green">
              <CheckCircle2 size={18} />
              <span className="text-sm font-semibold">Analysis Complete</span>
            </div>
          )}

          {/* Title */}
          {data!.analysisTitle && (
            <h2 className="text-xl font-bold text-text-heading mb-5">{data!.analysisTitle}</h2>
          )}

          {/* KPI cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
            <Card className="p-5">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Users size={18} className="text-primary" />
                </div>
                <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-text-muted">Competitors</span>
              </div>
              <p className="text-3xl font-bold text-text-heading">{data!.competitorsAnalyzedNumber}</p>
            </Card>
            <Card className="p-5">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-9 h-9 rounded-lg bg-accent-green/10 flex items-center justify-center">
                  <BarChart3 size={18} className="text-accent-green" />
                </div>
                <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-text-muted">Reviews Analyzed</span>
              </div>
              <p className="text-3xl font-bold text-text-heading">{data!.totalReview}</p>
            </Card>
            <Card className="p-5">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-9 h-9 rounded-lg bg-amber-50 flex items-center justify-center">
                  <Star size={18} className="text-amber-500" />
                </div>
                <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-text-muted">Avg Rating</span>
              </div>
              <p className="text-3xl font-bold text-text-heading">{data!.avgGoogleRating}</p>
            </Card>
          </div>

          {/* Sentiment pie */}
          {data!.pieChart && data!.pieChart.positive != null && (
            <Card className="p-6 mb-6">
              <h3 className="text-sm font-bold text-text-heading mb-4">{data!.pieChart.title}</h3>
              <div className="flex items-center gap-6 flex-wrap">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-positive" />
                  <span className="text-sm text-text-secondary">Positive: <strong className="text-text-heading">{data!.pieChart.positive?.toFixed(1)}%</strong></span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-negative" />
                  <span className="text-sm text-text-secondary">Negative: <strong className="text-text-heading">{data!.pieChart.negative?.toFixed(1)}%</strong></span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-neutral" />
                  <span className="text-sm text-text-secondary">Neutral: <strong className="text-text-heading">{data!.pieChart.neutral?.toFixed(1)}%</strong></span>
                </div>
              </div>
              {/* Visual bar */}
              <div className="mt-4 h-4 rounded-full overflow-hidden flex bg-bg-main">
                <div className="bg-positive h-full transition-all" style={{ width: `${data!.pieChart.positive}%` }} />
                <div className="bg-neutral h-full transition-all" style={{ width: `${data!.pieChart.neutral}%` }} />
                <div className="bg-negative h-full transition-all" style={{ width: `${data!.pieChart.negative}%` }} />
              </div>
            </Card>
          )}

          {/* Reviews Breakdown (Google Maps vs Trustpilot) */}
          {data!.reviewsAnalyzedPerCompetitor && data!.reviewsAnalyzedPerCompetitor.some((r) => (r as Record<string, unknown>).googleMapsReviews || (r as Record<string, unknown>).trustpilotReviews) && (
            <Card className="p-6 mb-6">
              <h3 className="text-sm font-bold text-text-heading mb-4 flex items-center gap-2">
                <MessageSquare size={16} className="text-primary" />
                Review Sources Breakdown
              </h3>
              <div className="space-y-3">
                {data!.reviewsAnalyzedPerCompetitor.map((r, i) => {
                  const gmRev = (r as Record<string, unknown>).googleMapsReviews as number || 0;
                  const tpRev = (r as Record<string, unknown>).trustpilotReviews as number || 0;
                  const total = r.reviews || 1;
                  return (
                    <div key={i} className="flex items-center gap-3">
                      <span className="text-xs font-medium text-text-heading w-36 truncate">{r.name}</span>
                      <div className="flex-1 h-4 rounded-full overflow-hidden flex bg-bg-main">
                        <div className="bg-blue-500 h-full transition-all" style={{ width: `${(gmRev / total) * 100}%` }} title={`${gmRev} Google Maps reviews`} />
                        <div className="bg-emerald-500 h-full transition-all" style={{ width: `${(tpRev / total) * 100}%` }} title={`${tpRev} Trustpilot reviews`} />
                      </div>
                      <span className="text-[10px] text-text-muted whitespace-nowrap">{gmRev} GM / {tpRev} TP</span>
                    </div>
                  );
                })}
                <div className="flex items-center gap-4 mt-2 pt-2 border-t border-border-light">
                  <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-blue-500" />
                    <span className="text-[10px] text-text-muted">Google Maps</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                    <span className="text-[10px] text-text-muted">Trustpilot</span>
                  </div>
                </div>
              </div>
            </Card>
          )}

          {/* Competitor table */}
          <Card className="overflow-hidden mb-6">
            <div className="hidden sm:grid grid-cols-[2fr_0.6fr_0.6fr_0.7fr_0.7fr_0.6fr_0.8fr] gap-4 px-5 py-3 bg-bg-main border-b border-border text-[10px] font-semibold uppercase tracking-[0.1em] text-text-muted">
              <span>Competitor</span>
              <span>GM Rating</span>
              <span>Reviews</span>
              <span>Positive %</span>
              <span>Negative %</span>
              <span>Sentiment</span>
              <span>Trustpilot</span>
            </div>
            {data!.competitorsAnalyzed!.map((comp, i) => {
              const detail = data!.competitorsDetails?.[i];
              const tpUrl = detail?.trustpilotUrl;
              const tpRating = detail?.trustpilotRating;
              return (
                <div
                  key={i}
                  className="grid grid-cols-1 sm:grid-cols-[2fr_0.6fr_0.6fr_0.7fr_0.7fr_0.6fr_0.8fr] gap-2 sm:gap-4 px-5 py-4 items-center border-b border-border-light hover:bg-bg-main/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary font-bold text-xs">
                      {comp.name.charAt(0)}
                    </div>
                    <span className="text-[13px] font-semibold text-text-heading">{comp.name}</span>
                  </div>
                  <span className="text-xs text-text-primary font-medium flex items-center gap-1">
                    <Star size={12} className="text-amber-500" /> {comp.googleRating}
                  </span>
                  <span className="text-xs text-text-secondary">{comp.reviewsAnalyzed}</span>
                  <span className="text-xs font-medium text-positive">{comp.positivePercentage.toFixed(1)}%</span>
                  <span className="text-xs font-medium text-negative">{comp.negativePercentage.toFixed(1)}%</span>
                  <span className="text-xs font-medium text-text-heading">{comp.avgSentiment.toFixed(2)}</span>
                  <span className="text-xs">
                    {tpUrl ? (
                      <a href={tpUrl as string} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-emerald-600 hover:text-emerald-700 font-medium">
                        <ShieldCheck size={12} /> {tpRating || "View"}
                      </a>
                    ) : (
                      <span className="text-text-muted">—</span>
                    )}
                  </span>
                </div>
              );
            })}
          </Card>

          {/* Competitor sentiment comparison */}
          {data!.competitorSentimentComparisonChart && (
            <Card className="p-6 mb-6">
              <h3 className="text-sm font-bold text-text-heading mb-4">Sentiment Comparison</h3>
              <div className="space-y-3">
                {data!.competitorSentimentComparisonChart.map((c, i) => (
                  <div key={i}>
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-xs font-medium text-text-heading">{c.name}</span>
                      <span className="text-[10px] text-text-muted">
                        +{c.positive.toFixed(0)}% / -{c.negative.toFixed(0)}%
                      </span>
                    </div>
                    <div className="h-3 rounded-full overflow-hidden flex bg-bg-main">
                      <div className="bg-positive h-full" style={{ width: `${c.positive}%` }} />
                      <div className="bg-neutral h-full" style={{ width: `${c.neutral}%` }} />
                      <div className="bg-negative h-full" style={{ width: `${c.negative}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* AI Insights */}
          {data!.competitorsDetails && data!.competitorsDetails.some((d) => d.aiInsights) && (
            <Card className="p-6 mb-6">
              <h3 className="text-sm font-bold text-text-heading mb-4 flex items-center gap-2">
                <Lightbulb size={16} className="text-amber-400" />
                AI-Powered Insights
              </h3>
              <div className="space-y-4">
                {data!.competitorsDetails.filter((d) => d.aiInsights).map((d, i) => (
                  <div key={i} className="p-4 rounded-lg bg-bg-main border border-border-light">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-xs font-semibold text-primary">
                        {data!.competitorsAnalyzed?.[i]?.name || `Competitor ${i + 1}`}
                      </p>
                      <div className="flex items-center gap-2">
                        {d.googleMaps && (
                          <a href={d.googleMaps} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-[10px] text-blue-600 hover:text-blue-700">
                            <ExternalLink size={10} /> Maps
                          </a>
                        )}
                        {d.trustpilotUrl && (
                          <a href={d.trustpilotUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-[10px] text-emerald-600 hover:text-emerald-700">
                            <ShieldCheck size={10} /> Trustpilot
                          </a>
                        )}
                      </div>
                    </div>
                    <MarkdownRenderer content={d.aiInsights} />
                    <div className="flex items-center gap-4 mt-2">
                      {d.address && (
                        <p className="text-[11px] text-text-muted">{d.address}</p>
                      )}
                      {d.trustpilotRating && (
                        <span className="text-[11px] text-emerald-600 font-medium flex items-center gap-1">
                          <Star size={10} /> TP: {d.trustpilotRating}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Trustpilot Overview */}
          {data!.trustpilotData && data!.trustpilotData.length > 0 && (
            <Card className="p-6 mb-6">
              <h3 className="text-sm font-bold text-text-heading mb-4 flex items-center gap-2">
                <ShieldCheck size={16} className="text-emerald-500" />
                Trustpilot Data Overview
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {data!.trustpilotData.filter((tp) => tp.trustpilotUrl).map((tp, i) => {
                  const tpRec = tp as Record<string, unknown>;
                  const isVerified = Boolean(tpRec.verified);
                  const tpRating = tpRec.trustpilotRating;
                  const trustScore = tpRec.trustScore;
                  const totalTpReviews = tpRec.totalTrustpilotReviews;
                  const scrapedTp = tpRec.scrapedTrustpilotReviews;
                  return (
                  <div key={i} className="p-4 rounded-lg bg-bg-main border border-border-light">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold text-text-heading">{String(tpRec.name)}</span>
                      {isVerified && (
                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-700 text-[9px] font-bold">
                          <ShieldCheck size={9} /> Verified
                        </span>
                      )}
                    </div>
                    <div className="space-y-1.5">
                      {tpRating != null && (
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] text-text-muted">Rating</span>
                          <span className="text-[11px] font-semibold text-text-heading flex items-center gap-1">
                            <Star size={10} className="text-amber-500" /> {String(tpRating)}
                          </span>
                        </div>
                      )}
                      {trustScore != null && (
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] text-text-muted">Trust Score</span>
                          <span className="text-[11px] font-semibold text-text-heading">{String(trustScore)}</span>
                        </div>
                      )}
                      {totalTpReviews != null && (
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] text-text-muted">Total TP Reviews</span>
                          <span className="text-[11px] font-semibold text-text-heading">{Number(totalTpReviews)}</span>
                        </div>
                      )}
                      {scrapedTp != null && (
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] text-text-muted">Scraped</span>
                          <span className="text-[11px] font-semibold text-text-heading">{Number(scrapedTp)}</span>
                        </div>
                      )}
                      {tpRec.trustpilotUrl != null && (
                        <a href={String(tpRec.trustpilotUrl)} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-[10px] text-emerald-600 hover:text-emerald-700 mt-1">
                          <ExternalLink size={10} /> View on Trustpilot
                        </a>
                      )}
                    </div>
                  </div>
                  );
                })}
              </div>
              {data!.trustpilotData.filter((tp) => tp.trustpilotUrl).length === 0 && (
                <p className="text-xs text-text-muted text-center py-4">No Trustpilot data found for these competitors.</p>
              )}
            </Card>
          )}
        </>
      )}

      {/* Empty state (no results, not loading) */}
      {!hasResults && !loading && !error && (
        <>
          <Card className="p-8 mb-6 border-dashed border-2 border-border">
            <div className="flex flex-col items-center text-center py-12">
              <div className="w-24 h-24 rounded-2xl bg-accent-green/20 flex items-center justify-center mb-6 relative">
                <TrendingUp size={40} className="text-accent-green" />
                <SearchIcon size={20} className="text-accent-green absolute -bottom-1 -right-1" />
                <div className="absolute inset-0 rounded-2xl bg-accent-green/10 blur-xl scale-150" />
              </div>
              <h2 className="text-xl font-bold text-text-heading mb-2">Ready to generate insights?</h2>
              <p className="text-sm text-text-secondary max-w-md mb-6 leading-relaxed">
                Input your industry details above. Our Trusted Advisor AI will scan
                competitive landscapes, pricing models, and sentiment trends.
              </p>
              <div className="flex items-center gap-2 text-[11px] text-text-muted uppercase tracking-wider font-medium mb-4">
                <Clock size={13} />
                Estimated Analysis Time: 30-60 seconds
              </div>
              <div className="flex gap-1.5">
                <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 text-[10px] font-bold">AI</span>
                <span className="px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 text-[10px] font-bold">ML</span>
                <span className="px-2 py-0.5 rounded-full bg-orange-100 text-orange-700 text-[10px] font-bold">DS</span>
              </div>
            </div>
          </Card>

          {/* Tip cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card className="p-5">
              <Lightbulb size={20} className="text-amber-400 mb-3" />
              <h3 className="text-sm font-bold text-text-heading mb-1.5">Pro Tip</h3>
              <p className="text-xs text-text-secondary leading-relaxed">
                Use specific niche terms like "Neobank" instead of just "Banking" for more granular competitor mapping.
              </p>
            </Card>
            <Card className="p-5">
              <Globe size={20} className="text-accent-green mb-3" />
              <h3 className="text-sm font-bold text-text-heading mb-1.5">Regional Tuning</h3>
              <p className="text-xs text-text-secondary leading-relaxed">
                Market sentiment varies wildly by region. Select a specific country for localized regulatory insight.
              </p>
            </Card>
            <Card className="p-5">
              <Clock size={20} className="text-text-secondary mb-3" />
              <h3 className="text-sm font-bold text-text-heading mb-1.5">Saved Audits</h3>
              <p className="text-xs text-text-secondary leading-relaxed">
                Your analysis runs are automatically archived. You can revisit and compare snapshots in the History tab.
              </p>
            </Card>
          </div>
        </>
      )}
    </>
  );
}