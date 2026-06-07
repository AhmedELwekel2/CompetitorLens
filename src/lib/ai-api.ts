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

// ─── Progress event type ─────────────────────────────────────────────────────

export interface AnalysisProgressEvent {
  _progress: true;
  stage: string;
  message: string;
  timestamp: number;
  data?: Record<string, unknown>;
}

// ─── Generic SSE Streamer ────────────────────────────────────────────────────

function createSSEStream<T>(
  endpoint: string,
  body: Record<string, unknown>,
  onData: (payload: T) => void,
  onError: (err: string) => void,
  onComplete: () => void,
  onProgress?: (event: AnalysisProgressEvent) => void,
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
          // SSE comment lines (keepalive) start with ": " — skip them
          if (line.startsWith(": ")) continue;

          if (line.startsWith("data: ")) {
            try {
              const payload = JSON.parse(line.slice(6));
              // Check if this is a progress event (keep-alive / status update)
              if (payload && payload._progress === true) {
                if (onProgress) onProgress(payload as AnalysisProgressEvent);
                continue; // don't pass progress events to onData
              }
              if (payload && typeof payload === "object" && "error" in payload && (payload as { error?: string | null }).error) {
                onError((payload as { error: string }).error);
              } else {
                onData(payload as T);
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
  company_name?: string;
  business_description?: string;
  main_goal?: string;
  target_audience_country?: string;
  additional_context?: string;
  /** Client-generated job ID for persistence across refreshes */
  job_id?: string;
}

  export function runAiMarketAnalysis(
    params: MarketAnalysisParams,
    onData: (payload: MarketAnalysisPayload) => void,
    onError: (err: string) => void,
    onComplete: () => void,
    onProgress?: (event: AnalysisProgressEvent) => void,
  ): AbortController {
    return createSSEStream<MarketAnalysisPayload>(
      "/customer-sentiment-analysis",
      {
        industry_field: params.industry,
        country: params.country || "Global",
        max_competitors: params.max_competitors,
        reviews_per_competitor: params.reviews_per_competitor,
        company_name: params.company_name,
        business_description: params.business_description,
        main_goal: params.main_goal,
        target_audience_country: params.target_audience_country,
        additional_context: params.additional_context,
        job_id: params.job_id,
      },
      onData,
      onError,
      onComplete,
      onProgress,
    );
  }

// ─── Job Reconnect ───────────────────────────────────────────────────────────

/**
 * Reconnect to an in-progress or completed market analysis job.
 * Replays all stored SSE events so the UI restores its state after a refresh or logout.
 */
export function reconnectToMarketJob(
  jobId: string,
  onData: (payload: MarketAnalysisPayload) => void,
  onError: (err: string) => void,
  onComplete: () => void,
  onProgress?: (event: AnalysisProgressEvent) => void,
): AbortController {
  const controller = new AbortController();

  fetch(`${AI_API_BASE}/job/${jobId}/stream`, {
    method: "GET",
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        onError("job_not_found");
        return;
      }
      const reader = res.body?.getReader();
      if (!reader) { onError("No response body"); return; }

      const decoder = new TextDecoder();
      let buffer = "";
      let hadError = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith(": ")) continue;
          if (line.startsWith("data: ")) {
            try {
              const payload = JSON.parse(line.slice(6));
              if (payload?._progress === true) {
                if (onProgress) onProgress(payload as AnalysisProgressEvent);
                continue;
              }
              if (payload?.error) { hadError = true; onError(payload.error); } else { onData(payload as MarketAnalysisPayload); }
            } catch { /* skip malformed */ }
          }
        }
      }
      // Only signal completion if no error SSE was received — an error payload
      // ends the stream but should not be treated as a successful completion.
      if (!hadError) onComplete();
    })
    .catch((err) => {
      if (err.name !== "AbortError") onError(err.message || "Reconnection failed");
    });

  return controller;
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
    onProgress?: (event: AnalysisProgressEvent) => void,
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
      onProgress,
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