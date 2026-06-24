import type { Metadata } from "next";
import Link from "next/link";
import {
  Sparkles,
  TrendingUp,
  Building2,
  MessageSquareText,
  Search,
  BarChart3,
  Clock,
  Zap,
  ShieldCheck,
  Check,
} from "lucide-react";
import { AuthCta } from "./auth-cta";

export const metadata: Metadata = {
  title: "sx — AI Competitive Intelligence & Market Sentiment",
  description:
    "sx turns thousands of competitor reviews into advisor-grade competitive intelligence and market sentiment analysis — in minutes, not weeks.",
};

const LOGO_GRADIENT =
  "linear-gradient(135deg, #8B5CF6 0%, #6D28D9 50%, #2DD4A8 130%)";

const features = [
  {
    icon: TrendingUp,
    title: "Market Analysis",
    body: "Benchmark your position against up to 5 competitors across the dimensions that actually move markets.",
  },
  {
    icon: Building2,
    title: "Business Analysis",
    body: "Deep-dive a single company's strengths, gaps, and strategic posture with a structured AI teardown.",
  },
  {
    icon: MessageSquareText,
    title: "Sentiment Engine",
    body: "Transformer-powered sentiment scoring across ~100 reviews per competitor, distilled into signal.",
  },
  {
    icon: Search,
    title: "Competitor Discovery",
    body: "Surface rivals you didn't know you had with AI-driven competitor search across the open web.",
  },
  {
    icon: BarChart3,
    title: "Insight Reports",
    body: "Advisor-grade narratives and visualizations your exec team will actually read — not raw data dumps.",
  },
  {
    icon: Clock,
    title: "History & Recall",
    body: "Every analysis saved and searchable, so competitive insight compounds over time instead of evaporating.",
  },
];

const steps = [
  {
    icon: Building2,
    title: "Name your competitors",
    body: "Drop in your company and the rivals you want to watch. No setup, no integrations.",
  },
  {
    icon: Zap,
    title: "AI gathers & analyzes",
    body: "sx collects reviews and runs sentiment plus competitive analysis in real time.",
  },
  {
    icon: ShieldCheck,
    title: "Act on the insight",
    body: "Get a clear narrative, a sentiment breakdown, and the moves that matter next.",
  },
];

const differentiators = [
  {
    title: "A point of view, not a dashboard",
    body: "Every run ends in a clear narrative and the moves that matter next — not another chart to decode.",
  },
  {
    title: "Sentiment you can defend",
    body: "Transformer-based scoring over real reviews, so the numbers hold up in the boardroom.",
  },
  {
    title: "Insight that compounds",
    body: "Saved, searchable history means each analysis builds on the one before it.",
  },
  {
    title: "Fast enough to actually use",
    body: "Competitive reads in minutes, so research keeps pace with the decisions that depend on it.",
  },
];

const outcomes = [
  { value: "10×", label: "faster than manual competitive research" },
  { value: "Minutes", label: "from competitors named to insight delivered" },
  { value: "Zero", label: "setup, integrations, or dashboards to configure" },
  { value: "100%", label: "of findings traced back to real reviews" },
];

const GRADIENT_TEXT = {
  background: "linear-gradient(90deg, #6D28D9 0%, #22D3EE 100%)",
  WebkitBackgroundClip: "text",
  WebkitTextFillColor: "transparent",
  backgroundClip: "text",
} as const;

const metrics = [
  "Up to 5 competitors per run",
  "~100 reviews analyzed each",
  "Real-time sentiment",
  "Minutes, not weeks",
];

function Wordmark({ subtle = false }: { subtle?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <div
        className="w-9 h-9 rounded-xl flex items-center justify-center shadow-lg"
        style={{
          background: LOGO_GRADIENT,
          boxShadow: "0 6px 16px -4px rgba(139,92,246,0.45)",
        }}
      >
        <Sparkles size={18} className="text-white" strokeWidth={2.2} aria-hidden />
      </div>
      <div className="leading-none">
        <span
          className={`font-display font-bold text-[18px] tracking-tight ${
            subtle ? "text-white" : "text-text-heading"
          }`}
        >
          sx
        </span>
        <span
          className={`block text-[9px] font-semibold uppercase tracking-[0.18em] mt-0.5 ${
            subtle ? "text-white/45" : "text-text-muted"
          }`}
        >
          Trusted Advisor
        </span>
      </div>
    </div>
  );
}

export default function WelcomePage() {
  return (
    <div className="min-h-screen text-text-primary">
      {/* ─── Navbar ─────────────────────────────────────────────── */}
      <header className="sticky top-0 z-30 px-4 pt-4">
        <nav className="mx-auto max-w-6xl flex items-center justify-between rounded-2xl border border-border bg-bg-card/80 backdrop-blur-md px-4 sm:px-5 py-3 shadow-soft">
          <Link href="/welcome" aria-label="sx home">
            <Wordmark />
          </Link>
          <div className="hidden md:flex items-center gap-7 text-[13.5px] font-medium text-text-secondary">
            <a href="#features" className="hover:text-text-heading transition-colors">
              Features
            </a>
            <a href="#how" className="hover:text-text-heading transition-colors">
              How it works
            </a>
            <a href="#proof" className="hover:text-text-heading transition-colors">
              Why sx
            </a>
          </div>
          <div className="flex items-center gap-2">
            <AuthCta variant="nav" />
          </div>
        </nav>
      </header>

      {/* ─── Hero ───────────────────────────────────────────────── */}
      <section className="px-4 pt-16 pb-20 sm:pt-24 sm:pb-28">
        <div className="mx-auto max-w-6xl grid lg:grid-cols-2 gap-14 items-center">
          {/* Copy */}
          <div className="animate-fade-in-up">
            <span className="inline-flex items-center gap-2 rounded-full border border-border bg-bg-card px-3.5 py-1.5 text-[12px] font-semibold text-primary shadow-soft">
              <Sparkles size={13} strokeWidth={2.4} aria-hidden />
              AI-Powered Competitive Intelligence
            </span>
            <h1 className="mt-6 font-display text-[2.6rem] sm:text-[3.4rem] leading-[1.05] text-text-heading">
              Competitive intelligence
              <br className="hidden sm:block" />{" "}
              <span
                style={{
                  background: "linear-gradient(90deg, #6D28D9 0%, #22D3EE 100%)",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  backgroundClip: "text",
                }}
              >
                you can actually trust.
              </span>
            </h1>
            <p className="mt-5 text-[16px] sm:text-[17px] leading-[1.7] text-text-secondary max-w-xl">
              sx analyzes your competitors and the market&apos;s sentiment in
              minutes — turning thousands of reviews into advisor-grade insight
              your team can act on with confidence.
            </p>
            <div className="mt-8 flex flex-col sm:flex-row gap-3">
              <AuthCta variant="hero" />
            </div>
            <div className="mt-7 flex items-center gap-2 text-[13px] text-text-muted">
              <Check size={15} className="text-accent-green" aria-hidden />
              No credit card · Analyze your first competitor set in minutes
            </div>
          </div>

          {/* Product preview mock */}
          <div className="animate-fade-in-up reveal-2 lg:justify-self-end w-full max-w-md">
            <div className="animate-float rounded-2xl border border-border bg-bg-card shadow-pop p-5">
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-2">
                  <TrendingUp size={16} className="text-primary" aria-hidden />
                  <span className="font-display font-semibold text-[14px] text-text-heading">
                    Market Analysis
                  </span>
                </div>
                <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-accent-green bg-accent-green/10 px-2 py-1 rounded-md">
                  Live
                </span>
              </div>
              <div className="space-y-3.5">
                {[
                  { name: "Your company", score: 86, tone: "bg-accent-green" },
                  { name: "Competitor A", score: 72, tone: "bg-primary" },
                  { name: "Competitor B", score: 64, tone: "bg-accent-teal" },
                  { name: "Competitor C", score: 41, tone: "bg-neutral" },
                ].map((row) => (
                  <div key={row.name}>
                    <div className="flex justify-between text-[12px] mb-1.5">
                      <span className="text-text-secondary font-medium">
                        {row.name}
                      </span>
                      <span className="text-text-heading font-semibold">
                        {row.score}
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-bg-main overflow-hidden">
                      <div
                        className={`h-full rounded-full ${row.tone} animate-progress`}
                        style={{ width: `${row.score}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-5 pt-4 border-t border-border grid grid-cols-3 gap-3 text-center">
                {[
                  { k: "Reviews", v: "412" },
                  { k: "Sentiment", v: "+38%" },
                  { k: "Rivals", v: "4" },
                ].map((s) => (
                  <div key={s.k}>
                    <p className="font-display font-bold text-[18px] text-text-heading">
                      {s.v}
                    </p>
                    <p className="text-[10px] uppercase tracking-[0.1em] text-text-muted mt-0.5">
                      {s.k}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── Trust strip ────────────────────────────────────────── */}
      <section className="px-4 pb-6">
        <div className="mx-auto max-w-6xl flex flex-wrap items-center justify-center gap-x-8 gap-y-3">
          {metrics.map((m) => (
            <div
              key={m}
              className="flex items-center gap-2 text-[13px] font-medium text-text-secondary"
            >
              <Check size={15} className="text-accent-green" aria-hidden />
              {m}
            </div>
          ))}
        </div>
      </section>

      {/* ─── Features ───────────────────────────────────────────── */}
      <section id="features" className="px-4 py-20 sm:py-28 scroll-mt-24">
        <div className="mx-auto max-w-6xl">
          <div className="max-w-2xl mb-14">
            <h2 className="font-display text-[2rem] sm:text-[2.5rem] leading-tight text-text-heading">
              Everything you need to read the market
            </h2>
            <p className="mt-4 text-[16px] leading-[1.7] text-text-secondary">
              One workspace for competitive analysis, sentiment, and the
              reporting that turns raw signal into a decision.
            </p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {features.map((f) => {
              const Icon = f.icon;
              return (
                <div
                  key={f.title}
                  className="group rounded-2xl border border-border bg-bg-card p-6 shadow-card hover:shadow-pop hover:border-primary/30 transition-all duration-200"
                >
                  <div className="w-11 h-11 rounded-xl bg-primary/10 flex items-center justify-center mb-4 group-hover:bg-primary/15 transition-colors">
                    <Icon size={20} className="text-primary" strokeWidth={2} aria-hidden />
                  </div>
                  <h3 className="font-display font-semibold text-[16.5px] text-text-heading mb-2">
                    {f.title}
                  </h3>
                  <p className="text-[14px] leading-[1.65] text-text-secondary">
                    {f.body}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ─── How it works ───────────────────────────────────────── */}
      <section id="how" className="px-4 py-20 sm:py-24 scroll-mt-24">
        <div className="mx-auto max-w-6xl">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="font-display text-[2rem] sm:text-[2.5rem] leading-tight text-text-heading">
              From competitors to clarity in three steps
            </h2>
            <p className="mt-4 text-[16px] leading-[1.7] text-text-secondary">
              No dashboards to configure. No data pipelines to babysit.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-6 md:gap-5 relative">
            {steps.map((s, i) => {
              const Icon = s.icon;
              return (
                <div key={s.title} className="relative text-center px-2">
                  <div className="mx-auto w-14 h-14 rounded-2xl bg-bg-card border border-border shadow-card flex items-center justify-center mb-5">
                    <Icon size={22} className="text-primary" strokeWidth={2} aria-hidden />
                  </div>
                  <span className="inline-block text-[11px] font-bold uppercase tracking-[0.16em] text-primary mb-2">
                    Step {i + 1}
                  </span>
                  <h3 className="font-display font-semibold text-[17px] text-text-heading mb-2">
                    {s.title}
                  </h3>
                  <p className="text-[14px] leading-[1.65] text-text-secondary max-w-xs mx-auto">
                    {s.body}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ─── Why sx ─────────────────────────────────────────────── */}
      <section
        id="proof"
        className="px-4 py-20 sm:py-24 scroll-mt-24"
        style={{
          background:
            "linear-gradient(180deg, transparent, rgba(109,40,217,0.04) 40%, transparent)",
        }}
      >
        <div className="mx-auto max-w-6xl grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          {/* Differentiators */}
          <div>
            <h2 className="font-display text-[2rem] sm:text-[2.5rem] leading-tight text-text-heading">
              Built to be the advisor in the room
            </h2>
            <p className="mt-4 text-[16px] leading-[1.7] text-text-secondary">
              sx doesn&apos;t just collect data — it forms a point of view, so
              your team walks into every decision already briefed.
            </p>
            <ul className="mt-8 space-y-5">
              {differentiators.map((d) => (
                <li key={d.title} className="flex gap-3.5">
                  <span className="mt-0.5 w-6 h-6 rounded-full bg-accent-green/15 flex items-center justify-center shrink-0">
                    <Check
                      size={14}
                      className="text-accent-green"
                      strokeWidth={2.6}
                      aria-hidden
                    />
                  </span>
                  <div>
                    <p className="font-display font-semibold text-[15.5px] text-text-heading">
                      {d.title}
                    </p>
                    <p className="text-[14px] leading-[1.6] text-text-secondary mt-0.5">
                      {d.body}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          {/* Outcome stats */}
          <div className="grid grid-cols-2 gap-4">
            {outcomes.map((o, i) => (
              <div
                key={o.label}
                className={`rounded-2xl border border-border bg-bg-card p-6 shadow-card ${
                  i % 2 ? "sm:mt-8" : ""
                }`}
              >
                <p
                  className="font-display font-bold text-[2.4rem] leading-none"
                  style={GRADIENT_TEXT}
                >
                  {o.value}
                </p>
                <p className="text-[13px] text-text-secondary mt-2.5 leading-snug">
                  {o.label}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Final CTA ──────────────────────────────────────────── */}
      <section className="px-4 py-16">
        <div
          className="mx-auto max-w-5xl rounded-3xl px-8 py-16 sm:px-14 sm:py-20 text-center relative overflow-hidden"
          style={{
            background:
              "radial-gradient(50rem 30rem at 80% -20%, rgba(45,212,168,0.16), transparent 60%), radial-gradient(40rem 30rem at 0% 120%, rgba(139,92,246,0.22), transparent 55%), #1E1B4B",
            boxShadow: "0 30px 60px -20px rgba(30,27,75,0.5)",
          }}
        >
          <h2 className="font-display text-[2rem] sm:text-[2.75rem] leading-tight text-white">
            See your market clearly today
          </h2>
          <p className="mt-4 text-[16px] leading-[1.7] text-white/65 max-w-xl mx-auto">
            Run your first competitive analysis in minutes. Turn reviews into
            advisor-grade intelligence — free to start.
          </p>
          <div className="mt-8 flex flex-col sm:flex-row gap-3 justify-center">
            <AuthCta variant="band" />
          </div>
        </div>
      </section>

      {/* ─── Footer ─────────────────────────────────────────────── */}
      <footer className="px-4 py-12 border-t border-border mt-8">
        <div className="mx-auto max-w-6xl flex flex-col sm:flex-row items-center justify-between gap-5">
          <Wordmark />
          <div className="flex items-center gap-7 text-[13px] text-text-secondary">
            <a href="#features" className="hover:text-text-heading transition-colors">
              Features
            </a>
            <a href="#how" className="hover:text-text-heading transition-colors">
              How it works
            </a>
            <AuthCta variant="link" />
          </div>
          <p className="text-[12px] text-text-muted">
            © {new Date().getFullYear()} sx — Trusted Advisor Intelligence
          </p>
        </div>
      </footer>
    </div>
  );
}
