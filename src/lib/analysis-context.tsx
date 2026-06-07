"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useRef,
  useEffect,
  ReactNode,
} from "react";
import {
  runAiMarketAnalysis,
  runAiBusinessAnalysis,
  reconnectToMarketJob,
  MarketAnalysisPayload,
  MarketAnalysisParams,
  BusinessAnalysisParams,
  AnalysisProgressEvent,
} from "./ai-api";

// ─── Job persistence keys ────────────────────────────────────────────────────
const MARKET_JOB_KEY = "cl_market_job";
const JOB_TTL_MS = 7200_000; // 2 hours — matches backend TTL
import { saveAnalysis } from "./api";

// ─── Types ────────────────────────────────────────────────────────────────────

export type AnalysisType = "MARKET" | "BUSINESS";

export interface AnalysisNotification {
  id: string;
  type: AnalysisType;
  title: string;
  success: boolean;
  error?: string;
  timestamp: number;
}

interface ActiveAnalysis {
  type: AnalysisType;
  loading: boolean;
  data: MarketAnalysisPayload | null;
  error: string | null;
  completed: boolean;
  controller: AbortController | null;
  /** Params used to start the analysis */
  params: MarketAnalysisParams | BusinessAnalysisParams | null;
  /** Extra metadata for re-saving on completion */
  meta: Record<string, unknown> | null;
  /** Current progress message from the backend (keeps connection alive) */
  progressMessage: string | null;
  /** Current progress stage */
  progressStage: string | null;
}

interface AnalysisCtx {
  /** Active market analysis state (persists across navigation) */
  market: ActiveAnalysis;
  /** Active business analysis state (persists across navigation) */
  business: ActiveAnalysis;
  /** Start a market analysis */
  startMarketAnalysis: (
    params: MarketAnalysisParams,
    meta?: Record<string, unknown>
  ) => void;
  /** Start a business analysis */
  startBusinessAnalysis: (
    params: BusinessAnalysisParams,
    meta?: Record<string, unknown>
  ) => void;
  /** Cancel the active analysis of the given type */
  cancelAnalysis: (type: AnalysisType) => void;
  /** Reset an analysis (clear data) */
  resetAnalysis: (type: AnalysisType) => void;
  /** Notifications */
  notifications: AnalysisNotification[];
  /** Dismiss a notification */
  dismissNotification: (id: string) => void;
  /** Clear all notifications */
  clearNotifications: () => void;
}

// ─── Default ──────────────────────────────────────────────────────────────────

const defaultAnalysis: ActiveAnalysis = {
  type: "MARKET",
  loading: false,
  data: null,
  error: null,
  completed: false,
  controller: null,
  params: null,
  meta: null,
  progressMessage: null,
  progressStage: null,
};

const AnalysisContext = createContext<AnalysisCtx>({
  market: { ...defaultAnalysis, type: "MARKET" },
  business: { ...defaultAnalysis, type: "BUSINESS" },
  startMarketAnalysis: () => {},
  startBusinessAnalysis: () => {},
  cancelAnalysis: () => {},
  resetAnalysis: () => {},
  notifications: [],
  dismissNotification: () => {},
  clearNotifications: () => {},
});

// ─── Provider ─────────────────────────────────────────────────────────────────

function _readStoredJob(): ActiveAnalysis {
  // Runs synchronously during render (useState lazy init).
  // typeof window guard prevents server-side crash (localStorage is client-only).
  if (typeof window === "undefined") return { ...defaultAnalysis, type: "MARKET" };
  try {
    const raw = localStorage.getItem(MARKET_JOB_KEY);
    if (!raw) return { ...defaultAnalysis, type: "MARKET" };
    const { jobId, params, meta, startedAt } = JSON.parse(raw) as {
      jobId: string;
      params: MarketAnalysisParams;
      meta: Record<string, unknown> | null;
      startedAt: number;
    };
    if (!jobId || Date.now() - startedAt > JOB_TTL_MS) {
      localStorage.removeItem(MARKET_JOB_KEY);
      return { ...defaultAnalysis, type: "MARKET" };
    }
    // Return loading=true immediately so the spinner shows on first paint
    return {
      type: "MARKET",
      loading: true,
      data: null,
      error: null,
      completed: false,
      controller: null, // useEffect wires up the real controller
      params,
      meta: meta || null,
      progressMessage: "Reconnecting to analysis...",
      progressStage: "reconnecting",
    };
  } catch {
    return { ...defaultAnalysis, type: "MARKET" };
  }
}

export function AnalysisProvider({ children }: { children: ReactNode }) {
  // Lazy initializer reads localStorage synchronously — spinner visible on first paint,
  // no flash of the empty state before useEffect fires.
  const [market, setMarket] = useState<ActiveAnalysis>(_readStoredJob);
  const [business, setBusiness] = useState<ActiveAnalysis>({
    ...defaultAnalysis,
    type: "BUSINESS",
  });
  const [notifications, setNotifications] = useState<AnalysisNotification[]>(
    []
  );

  // Use refs to avoid stale closures in SSE callbacks
  const marketDataRef = useRef<MarketAnalysisPayload | null>(null);
  const marketHadErrorRef = useRef(false);
  const businessDataRef = useRef<MarketAnalysisPayload | null>(null);
  const businessHadErrorRef = useRef(false);

  const addNotification = useCallback(
    (n: Omit<AnalysisNotification, "id" | "timestamp">) => {
      const notification: AnalysisNotification = {
        ...n,
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        timestamp: Date.now(),
      };
      setNotifications((prev) => [notification, ...prev]);
    },
    []
  );

  const dismissNotification = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const clearNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  // Auto-dismiss notifications after 15 seconds
  useEffect(() => {
    if (notifications.length === 0) return;
    const timers = notifications.map((n) =>
      setTimeout(() => {
        setNotifications((prev) => prev.filter((x) => x.id !== n.id));
      }, 15000)
    );
    return () => timers.forEach(clearTimeout);
  }, [notifications]);

  // ─── Market Analysis ──────────────────────────────────────────────────────

  const startMarketAnalysis = useCallback(
    (params: MarketAnalysisParams, meta?: Record<string, unknown>) => {
      marketDataRef.current = null;
      marketHadErrorRef.current = false;

      const countryLabel = (meta as { countryLabel?: string } | undefined)?.countryLabel || params.country || "Global";

      // Generate job ID and persist it BEFORE the request starts.
      // This guarantees localStorage is populated even if the user refreshes
      // immediately, without depending on receiving an event from the backend.
      const jobId = `cl-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 9)}`;
      try {
        localStorage.setItem(MARKET_JOB_KEY, JSON.stringify({
          jobId,
          params,
          meta: meta || null,
          startedAt: Date.now(),
        }));
      } catch { /* storage may be unavailable in some environments */ }

      const controller = runAiMarketAnalysis(
        { ...params, job_id: jobId },
        (payload) => {
          marketDataRef.current = payload;
          setMarket((prev) => ({ ...prev, data: payload }));
        },
        (err) => {
          marketHadErrorRef.current = true;
          try { localStorage.removeItem(MARKET_JOB_KEY); } catch { /* */ }
          setMarket((prev) => ({ ...prev, error: err, loading: false }));
          addNotification({
            type: "MARKET",
            title: `Market Analysis — ${params.industry}`,
            success: false,
            error: err,
          });
        },
        () => {
          const payload = marketDataRef.current;
          try { localStorage.removeItem(MARKET_JOB_KEY); } catch { /* */ }
          setMarket((prev) => ({
            ...prev,
            loading: false,
            completed: true,
            data: payload,
            progressMessage: null,
            progressStage: null,
          }));
          if (!marketHadErrorRef.current && payload) {
            addNotification({
              type: "MARKET",
              title: payload?.analysisTitle || `Market Analysis — ${params.industry}`,
              success: true,
            });
            // Save once on completion (inside context, never re-fires)
            void saveAnalysis({
              analysis_type: "MARKET",
              title: payload.analysisTitle || `${params.industry} Industry Analysis - ${countryLabel}`,
              subtitle: "Market Sentiment Overview",
              industry: params.industry,
              country: countryLabel,
              payload: payload as unknown as Record<string, unknown>,
            }).catch(() => {});
          }
        },
        (progressEvent: AnalysisProgressEvent) => {
          setMarket((prev) => ({
            ...prev,
            progressMessage: progressEvent.message,
            progressStage: progressEvent.stage,
          }));
        }
      );

      setMarket({
        type: "MARKET",
        loading: true,
        data: null,
        error: null,
        completed: false,
        controller,
        params,
        meta: meta || null,
        progressMessage: "Starting analysis...",
        progressStage: "starting",
      });
    },
    [addNotification]
  );

  // ─── Reconnect on mount (survives refresh / logout) ───────────────────────
  useEffect(() => {
    let stored: string | null = null;
    try { stored = localStorage.getItem(MARKET_JOB_KEY); } catch { /* */ }
    if (!stored) return;

    let jobId: string;
    let params: MarketAnalysisParams;
    let meta: Record<string, unknown> | null;
    let startedAt: number;
    try {
      ({ jobId, params, meta, startedAt } = JSON.parse(stored) as {
        jobId: string;
        params: MarketAnalysisParams;
        meta: Record<string, unknown> | null;
        startedAt: number;
      });
    } catch {
      try { localStorage.removeItem(MARKET_JOB_KEY); } catch { /* */ }
      return;
    }

    if (!jobId || Date.now() - startedAt > JOB_TTL_MS) {
      try { localStorage.removeItem(MARKET_JOB_KEY); } catch { /* */ }
      return;
    }

    marketDataRef.current = null;
    marketHadErrorRef.current = false;

    const countryLabel =
      (meta as { countryLabel?: string } | null)?.countryLabel ||
      params.country ||
      "Global";

    // ── retry state ────────────────────────────────────────────────────────
    const MAX_RETRIES = 5;
    let attempt = 0;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let mounted = true;
    let activeController: AbortController | null = null;

    const attempt_reconnect = () => {
      if (!mounted) return;

      activeController = reconnectToMarketJob(
        jobId,
        // onData
        (payload) => {
          if (!mounted) return;
          marketDataRef.current = payload;
          setMarket((prev) => ({ ...prev, data: payload }));
        },
        // onError
        (err) => {
          if (!mounted) return;
          if (err === "job_not_found" && attempt < MAX_RETRIES) {
            // Server may still be starting up — keep the spinner and retry
            attempt += 1;
            setMarket((prev) => ({
              ...prev,
              progressMessage: `Analysis running on server — reconnecting… (${attempt}/${MAX_RETRIES})`,
            }));
            retryTimer = setTimeout(attempt_reconnect, 6000);
          } else {
            // Exhausted retries — let the user decide; keep loading so Cancel is visible
            try { localStorage.removeItem(MARKET_JOB_KEY); } catch { /* */ }
            setMarket((prev) => ({
              ...prev,
              progressMessage: "Could not reach the server. Your analysis may still be running. Click Cancel to dismiss.",
            }));
          }
        },
        // onComplete
        () => {
          if (!mounted) return;
          const payload = marketDataRef.current;

          // Treat as incomplete if we didn't receive a final payload with
          // competitor data. This covers: no data at all (null), partial data
          // from an early SSE event, or a premature stream close (nginx timeout).
          const isComplete =
            payload &&
            payload.competitorsAnalyzed &&
            payload.competitorsAnalyzed.length > 0;

          if (!isComplete && attempt < MAX_RETRIES) {
            attempt += 1;
            setMarket((prev) => ({
              ...prev,
              progressMessage: `Reconnecting to analysis… (${attempt}/${MAX_RETRIES})`,
            }));
            retryTimer = setTimeout(attempt_reconnect, 3000);
            return;
          }

          try { localStorage.removeItem(MARKET_JOB_KEY); } catch { /* */ }
          setMarket((prev) => ({
            ...prev,
            loading: false,
            completed: true,
            data: payload,
            progressMessage: null,
            progressStage: null,
          }));
          if (!marketHadErrorRef.current && payload) {
            addNotification({
              type: "MARKET",
              title: payload?.analysisTitle || `Market Analysis — ${params.industry}`,
              success: true,
            });
            void saveAnalysis({
              analysis_type: "MARKET",
              title: payload.analysisTitle || `${params.industry} Industry Analysis - ${countryLabel}`,
              subtitle: "Market Sentiment Overview",
              industry: params.industry,
              country: countryLabel,
              payload: payload as unknown as Record<string, unknown>,
            }).catch(() => {});
          }
        },
        // onProgress
        (progressEvent: AnalysisProgressEvent) => {
          if (!mounted) return;
          setMarket((prev) => ({
            ...prev,
            progressMessage: progressEvent.message,
            progressStage: progressEvent.stage,
          }));
        },
      );

      // Store the live controller so the Cancel button can abort it
      setMarket((prev) => ({ ...prev, controller: activeController }));
    };

    // Show spinner immediately, then start first attempt
    setMarket({
      type: "MARKET",
      loading: true,
      data: null,
      error: null,
      completed: false,
      controller: null,
      params,
      meta: meta || null,
      progressMessage: "Reconnecting to analysis…",
      progressStage: "reconnecting",
    });

    attempt_reconnect();

    return () => {
      mounted = false;
      if (retryTimer) clearTimeout(retryTimer);
      activeController?.abort();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // intentionally runs only on mount

  // ─── Business Analysis ────────────────────────────────────────────────────

  const startBusinessAnalysis = useCallback(
    (params: BusinessAnalysisParams, meta?: Record<string, unknown>) => {
      businessDataRef.current = null;
      businessHadErrorRef.current = false;

      const metaObj = meta as { url?: string; maxReviews?: number; depth?: string } | undefined;

      const controller = runAiBusinessAnalysis(
        params,
        (payload) => {
          businessDataRef.current = payload;
          setBusiness((prev) => ({ ...prev, data: payload }));
        },
        (err) => {
          businessHadErrorRef.current = true;
          setBusiness((prev) => ({ ...prev, error: err, loading: false }));
          addNotification({
            type: "BUSINESS",
            title: `Business Analysis`,
            success: false,
            error: err,
          });
        },
        () => {
          const payload = businessDataRef.current;
          setBusiness((prev) => ({
            ...prev,
            loading: false,
            completed: true,
            data: payload,
            progressMessage: null,
            progressStage: null,
          }));
          if (!businessHadErrorRef.current && payload) {
            addNotification({
              type: "BUSINESS",
              title: payload?.analysisTitle || "Business Analysis",
              success: true,
            });
            // Save once on completion (inside context, never re-fires)
            void saveAnalysis({
              analysis_type: "SINGLE",
              title: payload.analysisTitle || "Business Sentiment Analysis",
              subtitle: "Single Entity Deep-Dive",
              google_maps_url: metaObj?.url || params.google_maps_url || "",
              max_reviews: metaObj?.maxReviews || params.max_reviews || 200,
              analysis_depth: (metaObj?.depth as "standard" | "sentiment") || "standard",
              payload: payload as unknown as Record<string, unknown>,
            }).catch(() => {});
          }
        },
        (progressEvent) => {
          setBusiness((prev) => ({
            ...prev,
            progressMessage: progressEvent.message,
            progressStage: progressEvent.stage,
          }));
        }
      );

      setBusiness({
        type: "BUSINESS",
        loading: true,
        data: null,
        error: null,
        completed: false,
        controller,
        params,
        meta: meta || null,
        progressMessage: "Starting analysis...",
        progressStage: "starting",
      });
    },
    [addNotification]
  );

  // ─── Cancel ───────────────────────────────────────────────────────────────

  const cancelAnalysis = useCallback((type: AnalysisType) => {
    if (type === "MARKET") {
      try { localStorage.removeItem(MARKET_JOB_KEY); } catch { /* */ }
      setMarket((prev) => {
        prev.controller?.abort();
        return { ...defaultAnalysis, type: "MARKET" };
      });
    } else {
      setBusiness((prev) => {
        prev.controller?.abort();
        return { ...defaultAnalysis, type: "BUSINESS" };
      });
    }
  }, []);

  // ─── Reset ────────────────────────────────────────────────────────────────

  const resetAnalysis = useCallback((type: AnalysisType) => {
    if (type === "MARKET") {
      try { localStorage.removeItem(MARKET_JOB_KEY); } catch { /* */ }
      setMarket((prev) => {
        prev.controller?.abort();
        return { ...defaultAnalysis, type: "MARKET" };
      });
    } else {
      setBusiness((prev) => {
        prev.controller?.abort();
        return { ...defaultAnalysis, type: "BUSINESS" };
      });
    }
  }, []);

  return (
    <AnalysisContext.Provider
      value={{
        market,
        business,
        startMarketAnalysis,
        startBusinessAnalysis,
        cancelAnalysis,
        resetAnalysis,
        notifications,
        dismissNotification,
        clearNotifications,
      }}
    >
      {children}
    </AnalysisContext.Provider>
  );
}

export function useAnalysis() {
  return useContext(AnalysisContext);
}