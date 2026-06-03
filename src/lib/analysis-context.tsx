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
  MarketAnalysisPayload,
  MarketAnalysisParams,
  BusinessAnalysisParams,
  AnalysisProgressEvent,
} from "./ai-api";
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

export function AnalysisProvider({ children }: { children: ReactNode }) {
  const [market, setMarket] = useState<ActiveAnalysis>({
    ...defaultAnalysis,
    type: "MARKET",
  });
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

      const controller = runAiMarketAnalysis(
        params,
        (payload) => {
          marketDataRef.current = payload;
          setMarket((prev) => ({ ...prev, data: payload }));
        },
        (err) => {
          marketHadErrorRef.current = true;
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
        (progressEvent) => {
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