"""
Analysis service that wraps the existing AI API modules.

This service acts as a bridge between the FastAPI routers and the
original Flask-based AI services (SentimentAnalyzer, GPTInsightsService, etc.).
In production, import and call the real modules; here we provide the interface
with mock fallbacks so the API is fully functional even without the AI dependencies.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to import real AI modules from the ai_api folder
AI_API_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ai_api")
sys.path.insert(0, AI_API_PATH)

_HAS_AI_MODULES = False
try:
    from sentiment_analyzer import SentimentAnalyzer
    from gpt_insights_service import GPTInsightsService
    from competitor_search_service import CompetitorSearchService
    _HAS_AI_MODULES = True
    logger.info("AI modules loaded successfully from ai_api/")
except ImportError as e:
    logger.warning(f"AI modules not available ({e}). Using mock analysis.")


class AnalysisService:
    """Orchestrates market and business sentiment analysis."""

    def __init__(self):
        if _HAS_AI_MODULES:
            self.analyzer = SentimentAnalyzer()
            self.gpt_service = GPTInsightsService()
            self.competitor_search = CompetitorSearchService()
        else:
            self.analyzer = None
            self.gpt_service = None
            self.competitor_search = None

    # ─── Market Analysis (SSE stream) ─────────────────────────────────────

    async def run_market_analysis(
        self,
        industry: str,
        country: str,
        max_competitors: int = 5,
        reviews_per_competitor: int = 100,
    ) -> AsyncGenerator[str, None]:
        """
        Yields SSE 'data: {...}\\n\\n' chunks as the analysis progresses.
        Mirrors the Flask streaming response from api.py.
        """
        payload = _empty_payload()

        # Step 0: initial empty frame
        yield _sse(payload)

        if self.analyzer and _HAS_AI_MODULES:
            # Run real analysis in a thread to avoid blocking
            result = await asyncio.to_thread(
                self._sync_market_analysis, industry, country, max_competitors, reviews_per_competitor
            )
            # Stream each populated field
            for frame in self._build_market_frames(payload, result, industry, country):
                yield _sse(frame)
        else:
            # Mock analysis for development/testing
            for frame in self._mock_market_frames(payload, industry, country):
                yield _sse(frame)
                await asyncio.sleep(0.15)  # simulate streaming delay

    def _sync_market_analysis(self, industry, country, max_comp, reviews_per) -> Dict:
        """Synchronous wrapper around the async competitor analysis."""
        loop = asyncio.new_event_loop()
        try:
            css = self.competitor_search or self.analyzer.competitor_search
            result = loop.run_until_complete(
                css.search_competitors_with_trustpilot(
                    industry=industry,
                    region=country,
                    max_competitors=max_comp,
                    max_reviews_per_competitor=reviews_per,
                )
            )
            competitors = result.get("competitors", [])
            if not competitors:
                return {"competitor_results": [], "combined_analysis": {}}

            competitor_results = []
            all_sentiments = []
            total_tokens = 0

            for comp in competitors:
                texts = []
                for r in comp.get("google_maps_reviews", []):
                    t = r.get("review_text", "").strip()
                    if t:
                        texts.append(t)
                for r in comp.get("trustpilot_reviews", []):
                    t = r.get("review_text", "").strip()
                    if t:
                        texts.append(t)

                if not texts:
                    competitor_results.append({
                        "competitor_info": comp,
                        "sentiment_summary": {"total_reviews": 0, "sentiment_percentages": {}, "average_polarity": 0},
                        "total_reviews_analyzed": 0,
                        "ai_insights": {"insights": {"summary": "", "full_analysis": ""}},
                    })
                    continue

                sentiments = self.analyzer.analyze_sentiment_batch(texts)
                total = len(sentiments)
                pos = sum(1 for s in sentiments if s["sentiment"] == "Positive")
                neg = sum(1 for s in sentiments if s["sentiment"] == "Negative")
                neu = total - pos - neg

                summary = {
                    "total_reviews": total,
                    "sentiment_percentages": {
                        "Positive": (pos / total) * 100,
                        "Negative": (neg / total) * 100,
                        "Neutral": (neu / total) * 100,
                    },
                    "average_polarity": sum(s["polarity"] for s in sentiments) / total,
                }
                all_sentiments.extend(sentiments)

                # Generate AI insights per competitor using GPT
                ai_insights = {"insights": {"summary": "", "full_analysis": ""}}
                try:
                    competitor_ai_input = {
                        "summary": {
                            "total_reviews": total,
                            "sentiment_percentages": summary["sentiment_percentages"],
                            "average_polarity": summary["average_polarity"],
                        },
                        "sample_reviews": [
                            {"Review Text": t, "Sentiment": s["sentiment"], "Star Rating": 0}
                            for t, s in zip(texts[:15], sentiments[:15])
                        ],
                        "competitor": {
                            "name": comp.get("name", "Unknown"),
                            "rating": comp.get("rating", 0),
                            "review_count": comp.get("review_count", 0),
                        },
                    }
                    gpt = self.gpt_service or self.analyzer.gpt_service
                    ai_insights = loop.run_until_complete(
                        gpt.generate_sentiment_insights(competitor_ai_input)
                    )
                    # Track tokens
                    if isinstance(ai_insights, dict):
                        tu = ai_insights.get("token_usage") or ai_insights.get("insights", {}).get("token_usage") or {}
                        total_tokens += tu.get("total_tokens", 0)
                except Exception as e:
                    logger.warning(f"AI insights failed for {comp.get('name')}: {e}")
                    ai_insights = {"insights": {"summary": "AI insights unavailable.", "full_analysis": ""}}

                competitor_results.append({
                    "competitor_info": comp,
                    "sentiment_summary": summary,
                    "total_reviews_analyzed": total,
                    "ai_insights": ai_insights,
                })

            total_all = len(all_sentiments)
            combined = {}
            if total_all:
                pa = sum(1 for s in all_sentiments if s["sentiment"] == "Positive")
                na = sum(1 for s in all_sentiments if s["sentiment"] == "Negative")
                nua = total_all - pa - na
                combined = {
                    "total_reviews": total_all,
                    "sentiment_percentages": {
                        "Positive": (pa / total_all) * 100,
                        "Negative": (na / total_all) * 100,
                        "Neutral": (nua / total_all) * 100,
                    },
                    "average_polarity": sum(s["polarity"] for s in all_sentiments) / total_all,
                }

            return {
                "competitor_results": competitor_results,
                "combined_analysis": {
                    "combined_summary": combined,
                    "total_competitors_analyzed": len(competitor_results),
                    "total_reviews_analyzed": total_all,
                },
                "total_tokens": total_tokens,
            }
        finally:
            loop.close()

    def _build_market_frames(self, payload, result, industry, country):
        comp_results = result.get("competitor_results", [])
        combined = result.get("combined_analysis", {})
        combined_summary = combined.get("combined_summary", {})
        total_tokens = result.get("total_tokens", 0)

        payload["analysisTitle"] = f"{industry.title()} Industry Analysis - {country} (Google Maps + Trustpilot)"
        yield dict(payload)

        total_comp = combined.get("total_competitors_analyzed", len(comp_results))
        total_rev = combined.get("total_reviews_analyzed", 0)
        ratings = [r.get("competitor_info", {}).get("rating", 0) or 0 for r in comp_results]
        avg_rating = round(sum(ratings) / max(len(ratings), 1), 2)

        payload["competitorsAnalyzedNumber"] = total_comp
        payload["totalReview"] = total_rev
        payload["avgGoogleRating"] = avg_rating
        yield dict(payload)

        analyzed_list = []
        for r in comp_results:
            c = r.get("competitor_info", {})
            s = r.get("sentiment_summary", {})
            pct = s.get("sentiment_percentages", {})
            gm_count = len(c.get("google_maps_reviews", []))
            tp_count = len(c.get("trustpilot_reviews", []))
            analyzed_list.append({
                "name": c.get("name", ""),
                "googleRating": c.get("rating", 0),
                "reviewsAnalyzed": r.get("total_reviews_analyzed", 0),
                "positivePercentage": pct.get("Positive", 0),
                "negativePercentage": pct.get("Negative", 0),
                "avgSentiment": s.get("average_polarity", 0),
                "googleMapsReviewsCount": gm_count,
                "trustpilotReviewsCount": tp_count,
            })
        payload["competitorsAnalyzed"] = analyzed_list
        yield dict(payload)

        sp = combined_summary.get("sentiment_percentages", {})
        payload["pieChart"] = {
            "title": f"{industry.title()} sentiment distribution in {country} (Google Maps + Trustpilot)",
            "positive": sp.get("Positive", 0),
            "negative": sp.get("Negative", 0),
            "neutral": sp.get("Neutral", 0),
        }
        yield dict(payload)

        payload["competitorSentimentComparisonChart"] = [
            {
                "name": r.get("competitor_info", {}).get("name", ""),
                "positive": r.get("sentiment_summary", {}).get("sentiment_percentages", {}).get("Positive", 0),
                "negative": r.get("sentiment_summary", {}).get("sentiment_percentages", {}).get("Negative", 0),
                "neutral": r.get("sentiment_summary", {}).get("sentiment_percentages", {}).get("Neutral", 0),
            }
            for r in comp_results
        ]
        yield dict(payload)

        payload["competitorRating_averageSentiment_chart"] = [
            {
                "googleRating": r.get("competitor_info", {}).get("rating", 0),
                "averageSentiment": r.get("sentiment_summary", {}).get("average_polarity", 0),
                "competitorName": r.get("competitor_info", {}).get("name", ""),
            }
            for r in comp_results
        ]
        yield dict(payload)

        reviews_per_comp_list = []
        for r in comp_results:
            c = r.get("competitor_info", {})
            gm_count = len(c.get("google_maps_reviews", []))
            tp_count = len(c.get("trustpilot_reviews", []))
            reviews_per_comp_list.append({
                "name": c.get("name", ""),
                "reviews": r.get("total_reviews_analyzed", 0),
                "googleMapsReviews": gm_count,
                "trustpilotReviews": tp_count,
            })
        payload["reviewsAnalyzedPerCompetitor"] = reviews_per_comp_list
        yield dict(payload)

        competitors_details = []
        trustpilot_data = []
        for r in comp_results:
            c = r.get("competitor_info", {})
            ai_insights_raw = r.get("ai_insights", {}) or {}
            insights_obj = ai_insights_raw.get("insights", {}) if isinstance(ai_insights_raw, dict) else {}
            ai_full = insights_obj.get("full_analysis", "") or ""
            ai_summary = insights_obj.get("summary", "") or ""
            ai_text = ai_full or ai_summary or ""

            tp_info = c.get("trustpilot_business_info")
            tp_url = c.get("trustpilot_url")

            # Track tokens from AI insights
            if isinstance(ai_insights_raw, dict):
                tu = ai_insights_raw.get("token_usage") or insights_obj.get("token_usage") or {}
                total_tokens += tu.get("total_tokens", 0)

            competitors_details.append({
                "address": c.get("address", "") or "",
                "googleMaps": c.get("google_maps_url", "") or "",
                "aiInsights": ai_text,
                "trustpilotUrl": tp_url or "",
                "trustpilotRating": tp_info.get("rating", "") if tp_info else "",
                "trustScore": tp_info.get("trust_score", "") if tp_info else "",
                "trustpilotReviewsCount": tp_info.get("review_count", 0) if tp_info else 0,
            })

            trustpilot_data.append({
                "name": c.get("name", ""),
                "trustpilotUrl": tp_url,
                "trustpilotRating": tp_info.get("rating") if tp_info else None,
                "trustScore": tp_info.get("trust_score") if tp_info else None,
                "totalTrustpilotReviews": tp_info.get("review_count") if tp_info else None,
                "verified": tp_info.get("verified") if tp_info else None,
                "categories": tp_info.get("categories") if tp_info else None,
                "scrapedTrustpilotReviews": len(c.get("trustpilot_reviews", [])),
            })

        payload["competitorsDetails"] = competitors_details
        payload["trustpilotData"] = trustpilot_data
        payload["allTokensUsed"] = total_tokens
        yield dict(payload)

    def _mock_market_frames(self, payload, industry, country):
        """Generate realistic mock data for development."""
        payload["analysisTitle"] = f"{industry.title()} Industry Analysis - {country}"
        yield dict(payload)

        mock_names = ["TechVenture Corp", "InnoStar Solutions", "QuantumEdge Ltd", "NexaPrime Digital", "Meridian Analytics"]
        payload["competitorsAnalyzedNumber"] = 5
        payload["totalReview"] = 487
        payload["avgGoogleRating"] = 4.3
        yield dict(payload)

        analyzed = []
        for i, name in enumerate(mock_names):
            pos = 55 + i * 5
            neg = 20 - i * 2
            analyzed.append({
                "name": name,
                "googleRating": round(3.8 + i * 0.15, 1),
                "reviewsAnalyzed": 80 + i * 15,
                "positivePercentage": pos,
                "negativePercentage": neg,
                "avgSentiment": round(0.3 + i * 0.08, 2),
            })
        payload["competitorsAnalyzed"] = analyzed
        yield dict(payload)

        payload["pieChart"] = {
            "title": f"{industry.title()} sentiment in {country}",
            "positive": 62.4,
            "negative": 18.1,
            "neutral": 19.5,
        }
        yield dict(payload)

        payload["competitorSentimentComparisonChart"] = [
            {"name": a["name"], "positive": a["positivePercentage"], "negative": a["negativePercentage"], "neutral": 100 - a["positivePercentage"] - a["negativePercentage"]}
            for a in analyzed
        ]
        yield dict(payload)

        payload["competitorRating_averageSentiment_chart"] = [
            {"googleRating": a["googleRating"], "averageSentiment": a["avgSentiment"], "competitorName": a["name"]}
            for a in analyzed
        ]
        yield dict(payload)

        payload["reviewsAnalyzedPerCompetitor"] = [
            {"name": a["name"], "reviews": a["reviewsAnalyzed"], "googleMapsReviews": a["reviewsAnalyzed"] - 10, "trustpilotReviews": 10}
            for a in analyzed
        ]
        yield dict(payload)

        payload["competitorsDetails"] = [
            {
                "address": f"{100 + i} Market Street, {country}",
                "googleMaps": f"https://maps.google.com/?q={a['name'].replace(' ', '+')}",
                "aiInsights": f"Strong presence in {industry} with notable customer satisfaction trends. Key differentiator: innovative product strategy and responsive customer service.",
                "trustpilotUrl": f"https://www.trustpilot.com/review/{a['name'].lower().replace(' ', '-')}" if i % 2 == 0 else "",
                "trustpilotRating": f"{4.0 + i * 0.2:.1f}/5" if i % 2 == 0 else "",
                "trustScore": f"{3.5 + i * 0.3:.1f}/5" if i % 2 == 0 else "",
                "trustpilotReviewsCount": 20 + i * 5 if i % 2 == 0 else 0,
            }
            for i, a in enumerate(analyzed)
        ]
        payload["trustpilotData"] = [
            {
                "name": a["name"],
                "trustpilotUrl": f"https://www.trustpilot.com/review/{a['name'].lower().replace(' ', '-')}" if i % 2 == 0 else None,
                "trustpilotRating": f"{4.0 + i * 0.2:.1f}/5" if i % 2 == 0 else None,
                "trustScore": f"{3.5 + i * 0.3:.1f}/5" if i % 2 == 0 else None,
                "totalTrustpilotReviews": 20 + i * 5 if i % 2 == 0 else None,
                "verified": i % 2 == 0,
                "scrapedTrustpilotReviews": 10 if i % 2 == 0 else 0,
            }
            for i, a in enumerate(analyzed)
        ]
        yield dict(payload)

    # ─── Business Analysis (SSE stream) ───────────────────────────────────

    async def run_business_analysis(
        self,
        google_maps_url: str,
        max_reviews: int = 100,
        analysis_depth: str = "standard",
    ) -> AsyncGenerator[str, None]:
        payload = _empty_payload()
        yield _sse(payload)

        if self.analyzer and _HAS_AI_MODULES:
            result = await asyncio.to_thread(
                self._sync_business_analysis, google_maps_url, max_reviews
            )
            if result.get("error"):
                payload["error"] = result["error"]
                yield _sse(payload)
                return
            for frame in self._build_business_frames(payload, result, google_maps_url):
                yield _sse(frame)
        else:
            for frame in self._mock_business_frames(payload, google_maps_url):
                yield _sse(frame)
                await asyncio.sleep(0.15)

    def _sync_business_analysis(self, url, max_reviews) -> Dict:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                self.analyzer.analyze_business_sentiment(
                    google_maps_url=url, max_reviews=max_reviews
                )
            )
        finally:
            loop.close()

    def _build_business_frames(self, payload, result, url):
        biz = result.get("business_info", {})
        summary = result.get("sentiment_summary", {})
        total = result.get("total_reviews_analyzed", 0)
        name = biz.get("name", "Unknown Business")
        rating = biz.get("rating", 0) or 0
        pct = summary.get("sentiment_percentages", {})

        payload["analysisTitle"] = f"{name} - Sentiment Analysis"
        yield dict(payload)

        payload["competitorsAnalyzedNumber"] = 1
        payload["totalReview"] = total
        payload["avgGoogleRating"] = float(rating)
        yield dict(payload)

        payload["competitorsAnalyzed"] = [{
            "name": name, "googleRating": float(rating), "reviewsAnalyzed": total,
            "positivePercentage": pct.get("Positive", 0), "negativePercentage": pct.get("Negative", 0),
            "avgSentiment": summary.get("average_polarity", 0),
        }]
        yield dict(payload)

        payload["pieChart"] = {
            "title": f"{name} - Sentiment Distribution",
            "positive": pct.get("Positive", 0), "negative": pct.get("Negative", 0), "neutral": pct.get("Neutral", 0),
        }
        yield dict(payload)

    def _mock_business_frames(self, payload, url):
        name = "The Roasting Hub"
        payload["analysisTitle"] = f"{name} - Sentiment Analysis"
        yield dict(payload)

        payload["competitorsAnalyzedNumber"] = 1
        payload["totalReview"] = 156
        payload["avgGoogleRating"] = 4.6
        yield dict(payload)

        payload["competitorsAnalyzed"] = [{
            "name": name, "googleRating": 4.6, "reviewsAnalyzed": 156,
            "positivePercentage": 72.4, "negativePercentage": 12.8, "avgSentiment": 0.62,
        }]
        yield dict(payload)

        payload["pieChart"] = {
            "title": f"{name} - Sentiment Distribution",
            "positive": 72.4, "negative": 12.8, "neutral": 14.8,
        }
        yield dict(payload)

        payload["competitorSentimentComparisonChart"] = [{
            "name": name, "positive": 72.4, "negative": 12.8, "neutral": 14.8,
        }]
        yield dict(payload)

        payload["competitorsDetails"] = [{
            "address": "45 Brew Lane, Downtown",
            "googleMaps": url,
            "aiInsights": "Strong customer loyalty with excellent coffee quality ratings. Opportunities exist to improve wait times during peak morning hours. Staff friendliness is a consistent positive theme across reviews.",
        }]
        yield dict(payload)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _empty_payload() -> dict:
    return {
        "analysisTitle": None,
        "competitorsAnalyzedNumber": None,
        "totalReview": None,
        "avgGoogleRating": None,
        "competitorsAnalyzed": None,
        "pieChart": {"title": None, "positive": None, "negative": None, "neutral": None},
        "competitorSentimentComparisonChart": None,
        "competitorRating_averageSentiment_chart": None,
        "reviewsAnalyzedPerCompetitor": None,
        "competitorsDetails": None,
        "trustpilotData": None,
        "outputFile": None,
        "allTokensUsed": 0,
    }


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"
