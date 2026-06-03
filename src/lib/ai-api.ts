/**
 * CompetitorLens AI API Client
 * Connects the Next.js frontend to the Flask AI API (ai_api/app.py).
 * All endpoints use SSE (Server-Sent Events) streaming.
 */

const AI_API_BASE = process.env.NEXT_PUBLIC_AI_API_URL || "/ai";

// ─── Shared Types ────────────────────────────────────────────────────────────

export interface MarketAnalysisPayload {
  analysisTitle: string | null;
  competitorsAnalyzedNumber: number | null;
  totalReview: number | null;
  avgGoogleRating: number | null;
  competitorsAnalyzed: Array<{
    name: string;
    googleRating: number;
    reviewsAnalyzed: number;
    positivePercentage: number;
    negativePercentage: number;
    avgSentiment: number;
    googleMapsReviewsCount?: number;
    trustpilotReviewsCount?: number;
  }> | null;
  pieChart: {
    title: string | null;
    positive: number | null;
    negative: number | null;
    neutral: number | null;
  } | null;
  competitorSentimentComparisonChart: Array<{
    name: string;
    positive: number;
    negative: number;
    neutral: number;
  }> | null;
  competitorRating_averageSentiment_chart: Array<{
    googleRating: number;
    averageSentiment: number;
    competitorName: string;
  }> | null;
  reviewsAnalyzedPerCompetitor: Array<{
    name: string;
    reviews: number;
  }> | null;
  competitorsDetails: Array<{
    address: string;
    googleMaps: string;
    aiInsights: string;
    trustpilotUrl?: string;
    trustpilotRating?: string;
    trustScore?: string;
    trustpilotReviewsCount?: number;
  }> | null;
  trustpilotData: Array<Record<string, unknown>> | null;
  outputFile: string | null;
  allTokensUsed: number;
  error?: string | null;
}

export interface TrustpilotAnalysisPayload {
  analysisTitle: string | null;
  trustpilotRating: number | null;
  trustScore: number | null;
  totalReviews: number | null;
  verified: boolean | null;
  businessCategories: string[] | null;
  pieChart: {
    title: string | null;
    positive: number | null;
    negative: number | null;
    neutral: number | null;
  } | null;
  starDistributionChart: Array<{ stars: string; count: number }> | null;
  sentimentOverTimeChart: unknown[] | null;
  topKeywords: string[] | null;
  recentReviews: Array<{
    author: string;
    stars: number;
    title: string;
    text: string;
    date: string;
  }> | null;
  fullAnalysis: string | null;
  allTokensUsed: number;
  error?: string | null;
}

// ─── Generic SSE Streamer ────────────────────────────────────────────────────

function createSSEStream<T>(
  endpoint: string,
  body: Record<string, unknown>,
  onData: (payload: T) => void,
  onError: (err: string) => void,
  onComplete: () => void,
): AbortController {
  const controller = new AbortController();

  fetch(`${AI_API_BASE}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: "Analysis request failed" }));
        onError(err.error || err.detail || "Analysis request failed");
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        onError("No response body");
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const payload = JSON.parse(line.slice(6)) as T;
              if (payload && typeof payload === "object" && "error" in payload && (payload as { error?: string | null }).error) {
                onError((payload as { error: string }).error);
              } else {
                onData(payload);
              }
            } catch {
              // skip malformed SSE lines
            }
          }
        }
      }
      onComplete();
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onError(err.message || "Network error");
      }
    });

  return controller;
}

// ─── Market Analysis ─────────────────────────────────────────────────────────

export interface MarketAnalysisParams {
  industry: string;
  country?: string;
  max_competitors?: number;
  reviews_per_competitor?: number;
}

  export function runAiMarketAnalysis(
    params: MarketAnalysisParams,
    onData: (payload: MarketAnalysisPayload) => void,
    onError: (err: string) => void,
    onComplete: () => void,
  ): AbortController {
    return createSSEStream<MarketAnalysisPayload>(
      "/customer-sentiment-analysis",
      {
        industry_field: params.industry,
        country: params.country || "Global",
        max_competitors: params.max_competitors,
        reviews_per_competitor: params.reviews_per_competitor,
      },
      onData,
      onError,
      onComplete,
    );
  }

// ─── Single Business Analysis ────────────────────────────────────────────────

export interface BusinessAnalysisParams {
  google_maps_url: string;
  max_reviews?: number;
  analysis_depth?: "standard" | "sentiment";
}

  export function runAiBusinessAnalysis(
    params: BusinessAnalysisParams,
    onData: (payload: MarketAnalysisPayload) => void,
    onError: (err: string) => void,
    onComplete: () => void,
  ): AbortController {
    return createSSEStream<MarketAnalysisPayload>(
      "/business-sentiment-analysis",
      {
        google_maps_url: params.google_maps_url,
        max_reviews: params.max_reviews || 200,
      },
      onData,
      onError,
      onComplete,
    );
  }

// ─── Trustpilot Sentiment Analysis ───────────────────────────────────────────

export interface TrustpilotAnalysisParams {
  trustpilot_url?: string;
  business_name?: string;
  max_reviews?: number;
}

export function runTrustpilotAnalysis(
  params: TrustpilotAnalysisParams,
  onData: (payload: TrustpilotAnalysisPayload) => void,
  onError: (err: string) => void,
  onComplete: () => void,
): AbortController {
  const body: Record<string, unknown> = {};
  if (params.trustpilot_url) body.trustpilot_url = params.trustpilot_url;
  if (params.business_name) body.business_name = params.business_name;
  body.max_reviews = params.max_reviews || 200;

  return createSSEStream<TrustpilotAnalysisPayload>(
    "/trustpilot-sentiment-analysis",
    body,
    onData,
    onError,
    onComplete,
  );
}