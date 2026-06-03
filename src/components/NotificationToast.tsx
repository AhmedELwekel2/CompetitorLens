"use client";

import { useAnalysis, AnalysisNotification } from "@/lib/analysis-context";
import {
  CheckCircle2,
  XCircle,
  X,
  Loader2,
  TrendingUp,
  Building2,
} from "lucide-react";

function ToastItem({
  notification,
  onDismiss,
}: {
  notification: AnalysisNotification;
  onDismiss: (id: string) => void;
}) {
  const Icon = notification.type === "MARKET" ? TrendingUp : Building2;

  return (
    <div
      className={`
        flex items-start gap-3 p-4 rounded-xl border shadow-lg backdrop-blur-sm
        max-w-sm w-full transition-all duration-300 animate-slide-in
        ${
          notification.success
            ? "bg-accent-green/10 border-accent-green/30 text-accent-green"
            : "bg-negative/10 border-negative/30 text-negative"
        }
      `}
    >
      <div className="flex-shrink-0 mt-0.5">
        {notification.success ? (
          <CheckCircle2 size={18} />
        ) : (
          <XCircle size={18} />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <Icon size={13} className="opacity-60" />
          <span className="text-[10px] font-semibold uppercase tracking-wider opacity-60">
            {notification.type === "MARKET" ? "Market" : "Business"} Analysis
          </span>
        </div>
        <p className="text-sm font-semibold leading-tight truncate">
          {notification.title}
        </p>
        {notification.error && (
          <p className="text-xs mt-1 opacity-80 line-clamp-2">
            {notification.error}
          </p>
        )}
      </div>
      <button
        onClick={() => onDismiss(notification.id)}
        className="flex-shrink-0 p-1 rounded-md hover:bg-black/10 transition-colors"
      >
        <X size={14} />
      </button>
    </div>
  );
}

/** Loading indicator shown in the top-right when analysis is running */
function AnalysisLoadingIndicator() {
  const { market, business } = useAnalysis();

  const activeAnalysis = market.loading ? market : business.loading ? business : null;

  if (!activeAnalysis) return null;

  const label =
    activeAnalysis.type === "MARKET"
      ? "Market Analysis"
      : "Business Analysis";

  return (
    <div className="fixed top-4 right-4 z-[60] flex items-center gap-2 px-4 py-2.5 rounded-xl bg-sidebar text-white shadow-lg border border-white/10 animate-slide-in">
      <Loader2 size={16} className="animate-spin text-accent-green" />
      <span className="text-xs font-semibold">{label} running...</span>
    </div>
  );
}

export default function NotificationToast() {
  const { notifications, dismissNotification, market, business } =
    useAnalysis();

  // Only show completed/error notifications in the toast area (not loading state)
  const visibleNotifications = notifications;

  return (
    <>
      {/* Global loading indicator */}
      <AnalysisLoadingIndicator />

      {/* Notification toasts */}
      {visibleNotifications.length > 0 && (
        <div className="fixed top-4 right-4 z-[70] flex flex-col gap-2 pointer-events-none">
          {/* Offset down if there's a loading indicator */}
          <div
            style={{
              marginTop:
                market.loading || business.loading ? "48px" : "0",
            }}
            className="flex flex-col gap-2"
          >
            {visibleNotifications.slice(0, 5).map((n) => (
              <div key={n.id} className="pointer-events-auto">
                <ToastItem
                  notification={n}
                  onDismiss={dismissNotification}
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}