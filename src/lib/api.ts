/**
 * CompetitorLens API Client
 * Connects the Next.js frontend to the FastAPI backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// ─── Token management ────────────────────────────────────────────────────────

let _token: string | null = null;

export function setToken(token: string | null) {
  _token = token;
  if (token) {
    if (typeof window !== "undefined") localStorage.setItem("cl_token", token);
  } else {
    if (typeof window !== "undefined") localStorage.removeItem("cl_token");
  }
}

export function getToken(): string | null {
  if (_token) return _token;
  if (typeof window !== "undefined") {
    _token = localStorage.getItem("cl_token");
  }
  return _token;
}

// ─── Base fetch wrapper ──────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    setToken(null);
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || err.error || "API error");
  }

  return res.json();
}

// ─── Auth ────────────────────────────────────────────────────────────────────

export interface User {
  id: string;
  full_name: string;
  email: string;
  professional_title: string;
  avatar_initials: string;
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export async function register(data: {
  full_name: string;
  email: string;
  password: string;
  professional_title?: string;
}): Promise<AuthResponse> {
  const res = await apiFetch<AuthResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
  setToken(res.access_token);
  return res;
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const res = await apiFetch<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setToken(res.access_token);
  return res;
}

export async function getMe(): Promise<User> {
  return apiFetch<User>("/auth/me");
}

export async function updateProfile(data: {
  full_name?: string;
  professional_title?: string;
  email?: string;
}): Promise<User> {
  return apiFetch<User>("/auth/me", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function logout() {
  setToken(null);
}

// ─── Settings ────────────────────────────────────────────────────────────────

export interface Settings {
  google_maps_api_key_masked: string;
  analysis_bearer_token_masked: string;
  email_summary_enabled: boolean;
  volatility_alerts_enabled: boolean;
  api_status_alerts_enabled: boolean;
  updated_at: string | null;
}

export async function getSettings(): Promise<Settings> {
  return apiFetch<Settings>("/settings");
}

export async function updateSettings(data: {
  google_maps_api_key?: string;
  analysis_bearer_token?: string;
  email_summary_enabled?: boolean;
  volatility_alerts_enabled?: boolean;
  api_status_alerts_enabled?: boolean;
}): Promise<Settings> {
  return apiFetch<Settings>("/settings", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function testConnection(): Promise<{ status: string; message: string }> {
  return apiFetch("/settings/test-connection", { method: "POST" });
}

// ─── Usage Stats ──────────────────────────────────────────────────────────────

export interface UsageStats {
  total_tokens: number;
  tokens_this_month: number;
  total_analyses: number;
  analyses_this_month: number;
  estimated_cost: number;
  cost_this_month: number;
  monthly_token_limit: number;
  monthly_analysis_limit: number;
  avg_tokens_per_analysis: number;
  recent_usage: Array<{
    id: string;
    title: string;
    type: string;
    tokens: number;
    cost: number;
    created_at: string;
  }>;
}

export async function getUsageStats(): Promise<UsageStats> {
  return apiFetch<UsageStats>("/settings/usage");
}

// ─── Market Analysis (SSE) ───────────────────────────────────────────────────

export interface AnalysisPayload {
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

/**
 * Opens an SSE connection to the market analysis endpoint.
 * Calls `onData` each time a new payload arrives.
 */
export function runMarketAnalysis(
  data: { industry: string; country: string; max_competitors?: number; reviews_per_competitor?: number },
  onData: (payload: AnalysisPayload) => void,
  onError: (err: string) => void,
  onComplete: () => void,
): AbortController {
  const controller = new AbortController();
  const token = getToken();

  fetch(`${API_BASE}/market-analysis/run`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(data),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Analysis failed" }));
        onError(err.detail || err.error || "Analysis failed");
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

        // Parse SSE lines
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const payload = JSON.parse(line.slice(6)) as AnalysisPayload;
              if (payload.error) {
                onError(payload.error);
              } else {
                onData(payload);
              }
            } catch {
              // skip malformed lines
            }
          }
        }
      }
      onComplete();
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onError(err.message);
      }
    });

  return controller;
}

/**
 * Opens an SSE connection to the business analysis endpoint.
 */
export function runBusinessAnalysis(
  data: { google_maps_url: string; max_reviews?: number; analysis_depth?: string },
  onData: (payload: AnalysisPayload) => void,
  onError: (err: string) => void,
  onComplete: () => void,
): AbortController {
  const controller = new AbortController();
  const token = getToken();

  fetch(`${API_BASE}/business-analysis/run`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(data),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Analysis failed" }));
        onError(err.detail || err.error || "Analysis failed");
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
              const payload = JSON.parse(line.slice(6)) as AnalysisPayload;
              if (payload.error) {
                onError(payload.error);
              } else {
                onData(payload);
              }
            } catch {
              // skip
            }
          }
        }
      }
      onComplete();
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onError(err.message);
      }
    });

  return controller;
}

// ─── History ─────────────────────────────────────────────────────────────────

export interface AnalysisRecord {
  id: string;
  title: string;
  subtitle: string;
  analysis_type: "MARKET" | "SINGLE";
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
  industry: string;
  country: string;
  google_maps_url: string;
  max_reviews: number;
  analysis_depth: string;
  result_data: Record<string, unknown>;
  token_usage: Record<string, unknown>;
  created_at: string;
  completed_at: string | null;
}

export interface AnalysisList {
  items: AnalysisRecord[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface HistoryStats {
  total_reports: number;
  total_this_month: number;
  growth_pct: number;
  total_competitors_analyzed: number;
  active_monitoring: number;
}

export interface AnalysisSaveRequest {
  analysis_type: "MARKET" | "SINGLE";
  title: string;
  subtitle?: string;
  industry?: string;
  country?: string;
  google_maps_url?: string;
  max_reviews?: number;
  analysis_depth?: string;
  payload: Record<string, unknown>;
}

export async function getHistory(params?: {
  page?: number;
  per_page?: number;
  analysis_type?: string;
  search?: string;
  date_from?: string;
  date_to?: string;
}): Promise<AnalysisList> {
  const qs = new URLSearchParams();
  if (params?.page) qs.set("page", String(params.page));
  if (params?.per_page) qs.set("per_page", String(params.per_page));
  if (params?.analysis_type) qs.set("analysis_type", params.analysis_type);
  if (params?.search) qs.set("search", params.search);
  if (params?.date_from) qs.set("date_from", params.date_from);
  if (params?.date_to) qs.set("date_to", params.date_to);
  return apiFetch<AnalysisList>(`/history?${qs.toString()}`);
}

export async function getHistoryStats(): Promise<HistoryStats> {
  return apiFetch<HistoryStats>("/history/stats");
}

export async function saveAnalysis(body: AnalysisSaveRequest): Promise<AnalysisRecord> {
  return apiFetch<AnalysisRecord>("/history/save", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getAnalysis(id: string): Promise<AnalysisRecord & { competitors: unknown[] }> {
  return apiFetch(`/history/${id}`);
}

export async function deleteAnalysis(id: string): Promise<void> {
  await apiFetch(`/history/${id}`, { method: "DELETE" });
}
