"""
Standalone Flask app to test the sentiment analysis API endpoints.
Directly includes the route handlers from api.py.

Run: python test_flask_app.py
Then open http://localhost:5555 in your browser.
"""

import asyncio
import json
import logging
from typing import Any, Dict
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from sentiment_analyzer import SentimentAnalyzer
from competitor_search_service import CompetitorSearchService

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ── Helpers (stubs for what app.py's helpers module provides) ────────────────

def validate_url(url):
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    return url

def is_valid_url(url):
    return url.startswith("http://") or url.startswith("https://")

# ── POST /ai/customer-sentiment-analysis ─────────────────────────────────────

@app.post("/ai/customer-sentiment-analysis")
def customer_sentiment_analysis():
    try:
        body = request.get_json(force=True, silent=True) or {}

        industry = (body.get("industry_field") or "").strip()
        country = (body.get("country") or "").strip()

        if not industry or not country:
            return jsonify({"error": "industry_field and country are required"}), 400

        MAX_COMPETITORS = 5
        REVIEWS_PER_COMPETITOR = 100

        def stream_response():
            css = CompetitorSearchService()
            analyzer = SentimentAnalyzer()
            total_tokens = 0
            total_input_tokens = 0
            total_output_tokens = 0
            total_cost = 0.0

            async def run_competitor_analysis() -> Dict[str, Any]:
                result = await css.search_competitors_with_trustpilot(
                    industry=industry,
                    region=country,
                    max_competitors=MAX_COMPETITORS,
                    max_reviews_per_competitor=REVIEWS_PER_COMPETITOR,
                )

                competitors = result.get("competitors", [])
                if not competitors:
                    return {
                        "competitor_results": [],
                        "combined_analysis": {},
                        "output_file": result.get("output_file"),
                    }

                competitor_results = []
                all_sentiments = []

                for comp in competitors:
                    gm_reviews = comp.get("google_maps_reviews", [])
                    tp_reviews = comp.get("trustpilot_reviews", [])
                    all_review_texts = []
                    for r in gm_reviews:
                        text = r.get("review_text", "")
                        if text and text.strip():
                            all_review_texts.append(text)
                    for r in tp_reviews:
                        text = r.get("review_text", "")
                        if text and text.strip():
                            all_review_texts.append(text)

                    if not all_review_texts:
                        competitor_results.append({
                            "competitor_info": comp,
                            "sentiment_summary": {
                                "total_reviews": 0,
                                "sentiment_percentages": {"Positive": 0, "Negative": 0, "Neutral": 0},
                                "average_polarity": 0,
                            },
                            "total_reviews_analyzed": 0,
                            "ai_insights": {"insights": {"summary": "", "full_analysis": ""}},
                        })
                        continue

                    sentiment_results = analyzer.analyze_sentiment_batch(all_review_texts)
                    total = len(sentiment_results)
                    positive = sum(1 for r in sentiment_results if r["sentiment"] == "Positive")
                    negative = sum(1 for r in sentiment_results if r["sentiment"] == "Negative")
                    neutral = sum(1 for r in sentiment_results if r["sentiment"] == "Neutral")
                    sentiment_percentages = {
                        "Positive": (positive / total) * 100 if total else 0,
                        "Negative": (negative / total) * 100 if total else 0,
                        "Neutral": (neutral / total) * 100 if total else 0,
                    }
                    avg_polarity = sum(r["polarity"] for r in sentiment_results) / total if total else 0
                    summary = {
                        "total_reviews": total,
                        "sentiment_counts": {"Positive": positive, "Negative": negative, "Neutral": neutral},
                        "sentiment_percentages": sentiment_percentages,
                        "average_polarity": avg_polarity,
                    }
                    all_sentiments.extend(sentiment_results)

                    try:
                        competitor_ai_input = {
                            "summary": {
                                "total_reviews": total,
                                "sentiment_percentages": sentiment_percentages,
                                "average_polarity": avg_polarity,
                            },
                            "sample_reviews": [
                                {"Review Text": t, "Sentiment": s["sentiment"], "Star Rating": 0}
                                for t, s in zip(all_review_texts[:15], sentiment_results[:15])
                            ],
                            "competitor": {
                                "name": comp.get("name", "Unknown"),
                                "rating": comp.get("rating", 0),
                                "review_count": comp.get("review_count", 0),
                            },
                        }
                        ai_insights = await analyzer.gpt_service.generate_sentiment_insights(competitor_ai_input)
                    except Exception:
                        ai_insights = {"insights": {"summary": "AI insights unavailable.", "full_analysis": ""}}

                    competitor_results.append({
                        "competitor_info": comp,
                        "sentiment_summary": summary,
                        "total_reviews_analyzed": total,
                        "ai_insights": ai_insights,
                    })

                total_all = len(all_sentiments)
                if total_all > 0:
                    pos_all = sum(1 for r in all_sentiments if r["sentiment"] == "Positive")
                    neg_all = sum(1 for r in all_sentiments if r["sentiment"] == "Negative")
                    neu_all = sum(1 for r in all_sentiments if r["sentiment"] == "Neutral")
                    combined_summary = {
                        "total_reviews": total_all,
                        "sentiment_percentages": {
                            "Positive": (pos_all / total_all) * 100,
                            "Negative": (neg_all / total_all) * 100,
                            "Neutral": (neu_all / total_all) * 100,
                        },
                        "average_polarity": sum(r["polarity"] for r in all_sentiments) / total_all,
                    }
                else:
                    combined_summary = {}

                return {
                    "competitor_results": competitor_results,
                    "combined_analysis": {
                        "combined_summary": combined_summary,
                        "total_competitors_analyzed": len(competitor_results),
                        "total_reviews_analyzed": total_all,
                    },
                    "output_file": result.get("output_file"),
                }

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                analysis_results = loop.run_until_complete(run_competitor_analysis())
            finally:
                loop.close()

            competitor_results = analysis_results.get("competitor_results", [])
            combined = analysis_results.get("combined_analysis", {})
            combined_summary = combined.get("combined_summary", {})
            output_file = analysis_results.get("output_file")

            for result in competitor_results:
                ai_insights = result.get("ai_insights", {}) or {}
                if isinstance(ai_insights, dict):
                    insights_obj = ai_insights.get("insights", {}) or {}
                    token_usage_data = insights_obj.get("token_usage") or ai_insights.get("token_usage") or {}
                    if token_usage_data:
                        total_input_tokens += token_usage_data.get("input_tokens", 0)
                        total_output_tokens += token_usage_data.get("output_tokens", 0)
                        total_tokens += token_usage_data.get("total_tokens", 0)
                        total_cost += token_usage_data.get("total_cost", 0.0)

            payload = {
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
                "outputFile": output_file,
                "allTokensUsed": 0,
            }

            yield "data: " + json.dumps(payload) + "\n\n"

            payload["analysisTitle"] = f"{industry.title()} Industry Analysis - {country} (Google Maps + Trustpilot)"
            yield "data: " + json.dumps(payload) + "\n\n"

            total_competitors = combined.get("total_competitors_analyzed", len(competitor_results)) or 0
            total_reviews = combined.get("total_reviews_analyzed", 0) or 0
            avg_rating = round(
                sum([(r.get("competitor_info", {}).get("rating", 0) or 0) for r in competitor_results]) / max(len(competitor_results), 1), 2
            ) if competitor_results else 0

            payload["competitorsAnalyzedNumber"] = total_competitors
            payload["totalReview"] = total_reviews
            payload["avgGoogleRating"] = avg_rating
            yield "data: " + json.dumps(payload) + "\n\n"

            competitors_analyzed_list = []
            for result in competitor_results:
                comp = result.get("competitor_info", {})
                summary = result.get("sentiment_summary", {})
                pct = summary.get("sentiment_percentages", {})
                gm_count = len(comp.get("google_maps_reviews", []))
                tp_count = len(comp.get("trustpilot_reviews", []))
                competitors_analyzed_list.append({
                    "name": comp.get("name", ""),
                    "googleRating": comp.get("rating", 0) or 0,
                    "reviewsAnalyzed": result.get("total_reviews_analyzed", 0) or 0,
                    "googleMapsReviewsCount": gm_count,
                    "trustpilotReviewsCount": tp_count,
                    "positivePercentage": pct.get("Positive", 0) or 0,
                    "negativePercentage": pct.get("Negative", 0) or 0,
                    "avgSentiment": summary.get("average_polarity", 0) or 0,
                })

            payload["competitorsAnalyzed"] = competitors_analyzed_list
            yield "data: " + json.dumps(payload) + "\n\n"

            payload["pieChart"]["title"] = f"{industry.title()} sentiment distribution in {country} (Google Maps + Trustpilot)"
            payload["pieChart"]["positive"] = combined_summary.get("sentiment_percentages", {}).get("Positive", 0) or 0
            payload["pieChart"]["negative"] = combined_summary.get("sentiment_percentages", {}).get("Negative", 0) or 0
            payload["pieChart"]["neutral"] = combined_summary.get("sentiment_percentages", {}).get("Neutral", 0) or 0
            yield "data: " + json.dumps(payload) + "\n\n"

            sentiment_chart = []
            for result in competitor_results:
                comp = result.get("competitor_info", {})
                summary = result.get("sentiment_summary", {})
                pct = summary.get("sentiment_percentages", {})
                sentiment_chart.append({
                    "name": comp.get("name", ""),
                    "negative": pct.get("Negative", 0) or 0,
                    "positive": pct.get("Positive", 0) or 0,
                    "neutral": pct.get("Neutral", 0) or 0,
                })
            payload["competitorSentimentComparisonChart"] = sentiment_chart
            yield "data: " + json.dumps(payload) + "\n\n"

            rating_vs_sentiment = []
            for result in competitor_results:
                comp = result.get("competitor_info", {})
                summary = result.get("sentiment_summary", {})
                rating_vs_sentiment.append({
                    "googleRating": comp.get("rating", 0) or 0,
                    "averageSentiment": summary.get("average_polarity", 0) or 0,
                    "competitorName": comp.get("name", ""),
                })
            payload["competitorRating_averageSentiment_chart"] = rating_vs_sentiment
            yield "data: " + json.dumps(payload) + "\n\n"

            reviews_per_comp_list = []
            for result in competitor_results:
                comp = result.get("competitor_info", {})
                gm_count = len(comp.get("google_maps_reviews", []))
                tp_count = len(comp.get("trustpilot_reviews", []))
                reviews_per_comp_list.append({
                    "name": comp.get("name", ""),
                    "reviews": result.get("total_reviews_analyzed", 0) or 0,
                    "googleMapsReviews": gm_count,
                    "trustpilotReviews": tp_count,
                })
            payload["reviewsAnalyzedPerCompetitor"] = reviews_per_comp_list
            yield "data: " + json.dumps(payload) + "\n\n"

            competitors_details = []
            trustpilot_data = []
            for result in competitor_results:
                comp = result.get("competitor_info", {})
                ai_insights = result.get("ai_insights", {}) or {}
                insights_obj = ai_insights.get("insights", {}) or {}
                ai_full = insights_obj.get("full_analysis") or ai_insights.get("full_analysis") or ""
                ai_summary = insights_obj.get("summary") or ai_insights.get("summary", "") or ""
                ai_text = ai_full or ai_summary or ""
                tp_info = comp.get("trustpilot_business_info")
                tp_url = comp.get("trustpilot_url")
                competitors_details.append({
                    "address": comp.get("address", "") or "",
                    "googleMaps": comp.get("google_maps_url", "") or "",
                    "aiInsights": ai_text,
                    "trustpilotUrl": tp_url or "",
                    "trustpilotRating": tp_info.get("rating", "") if tp_info else "",
                    "trustScore": tp_info.get("trust_score", "") if tp_info else "",
                    "trustpilotReviewsCount": tp_info.get("review_count", 0) if tp_info else 0,
                })
                trustpilot_data.append({
                    "name": comp.get("name", ""),
                    "trustpilotUrl": tp_url,
                    "trustpilotRating": tp_info.get("rating") if tp_info else None,
                    "trustScore": tp_info.get("trust_score") if tp_info else None,
                    "totalTrustpilotReviews": tp_info.get("review_count") if tp_info else None,
                    "verified": tp_info.get("verified") if tp_info else None,
                    "categories": tp_info.get("categories") if tp_info else None,
                    "scrapedTrustpilotReviews": len(comp.get("trustpilot_reviews", [])),
                })

            payload["competitorsDetails"] = competitors_details
            payload["trustpilotData"] = trustpilot_data
            payload["allTokensUsed"] = total_tokens
            yield "data: " + json.dumps(payload) + "\n\n"

        response = Response(
            stream_with_context(stream_response()),
            mimetype="text/event-stream",
        )
        response.headers["Cache-Control"] = "no-cache, no-transform"
        response.headers["X-Accel-Buffering"] = "no"
        response.headers["Connection"] = "keep-alive"
        response.headers["Transfer-Encoding"] = "chunked"
        return response

    except Exception as e:
        return jsonify({"error": f"Failed to process request: {str(e)}"}), 500


# ── POST /ai/business-sentiment-analysis ─────────────────────────────────────

@app.post("/ai/business-sentiment-analysis")
def business_sentiment_analysis():
    try:
        body = request.get_json(force=True, silent=True) or {}
        if not body:
            return jsonify({"error": "Request body is required", "received": str(body)}), 400

        google_maps_url = (body.get("google_maps_url") or "").strip()
        try:
            max_reviews = int(body.get("max_reviews", 200))
            max_reviews = max(1, min(max_reviews, 500))
        except (ValueError, TypeError):
            max_reviews = 200

        if not google_maps_url:
            return jsonify({"error": "google_maps_url is required", "received_body": body}), 400

        google_maps_url = validate_url(google_maps_url)
        if not is_valid_url(google_maps_url):
            return jsonify({"error": "Invalid URL format.", "url": google_maps_url}), 400

        url_lower = google_maps_url.lower()
        if "maps.google.com" not in url_lower and "google.com/maps" not in url_lower:
            return jsonify({"error": "Invalid Google Maps URL.", "url": google_maps_url}), 400

        def stream_response():
            analyzer = SentimentAnalyzer()
            total_tokens = 0

            async def run_business_analysis() -> Dict[str, Any]:
                return await analyzer.analyze_business_sentiment(
                    google_maps_url=google_maps_url,
                    max_reviews=max_reviews
                )

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                analysis_results = loop.run_until_complete(run_business_analysis())
            finally:
                loop.close()

            if analysis_results.get("error"):
                error_payload = {
                    "error": analysis_results.get("error"),
                    "analysisTitle": None, "competitorsAnalyzedNumber": None,
                    "totalReview": None, "avgGoogleRating": None,
                    "competitorsAnalyzed": None, "pieChart": None,
                    "competitorSentimentComparisonChart": None,
                    "competitorRating_averageSentiment_chart": None,
                    "reviewsAnalyzedPerCompetitor": None,
                    "competitorsDetails": None, "allTokensUsed": 0,
                }
                yield "data: " + json.dumps(error_payload) + "\n\n"
                return

            business_info = analysis_results.get("business_info", {})
            sentiment_summary = analysis_results.get("sentiment_summary", {})
            ai_insights = analysis_results.get("ai_insights", {})
            total_reviews = analysis_results.get("total_reviews_analyzed", 0)

            if isinstance(ai_insights, dict):
                insights_obj = ai_insights.get("insights", {}) or {}
                token_usage_data = insights_obj.get("token_usage") or ai_insights.get("token_usage") or {}
                if token_usage_data:
                    total_tokens = token_usage_data.get("total_tokens", 0)

            payload = {
                "analysisTitle": None, "competitorsAnalyzedNumber": None,
                "totalReview": None, "avgGoogleRating": None,
                "competitorsAnalyzed": None,
                "pieChart": {"title": None, "positive": None, "negative": None, "neutral": None},
                "competitorSentimentComparisonChart": None,
                "competitorRating_averageSentiment_chart": None,
                "reviewsAnalyzedPerCompetitor": None,
                "competitorsDetails": None, "allTokensUsed": 0,
            }
            yield "data: " + json.dumps(payload) + "\n\n"

            business_name = business_info.get("name", "Unknown Business")
            payload["analysisTitle"] = f"{business_name} - Sentiment Analysis"
            yield "data: " + json.dumps(payload) + "\n\n"

            business_rating = business_info.get("rating", 0) or 0
            payload["competitorsAnalyzedNumber"] = 1
            payload["totalReview"] = total_reviews or 0
            payload["avgGoogleRating"] = float(business_rating)
            yield "data: " + json.dumps(payload) + "\n\n"

            sentiment_percentages = sentiment_summary.get("sentiment_percentages", {})
            payload["competitorsAnalyzed"] = [{
                "name": business_name,
                "googleRating": float(business_rating),
                "reviewsAnalyzed": total_reviews or 0,
                "positivePercentage": sentiment_percentages.get("Positive", 0) or 0,
                "negativePercentage": sentiment_percentages.get("Negative", 0) or 0,
                "avgSentiment": sentiment_summary.get("average_polarity", 0) or 0,
            }]
            yield "data: " + json.dumps(payload) + "\n\n"

            payload["pieChart"]["title"] = f"{business_name} - Sentiment Distribution"
            payload["pieChart"]["positive"] = sentiment_percentages.get("Positive", 0) or 0
            payload["pieChart"]["negative"] = sentiment_percentages.get("Negative", 0) or 0
            payload["pieChart"]["neutral"] = sentiment_percentages.get("Neutral", 0) or 0
            yield "data: " + json.dumps(payload) + "\n\n"

            payload["competitorSentimentComparisonChart"] = [{
                "name": business_name,
                "negative": sentiment_percentages.get("Negative", 0) or 0,
                "positive": sentiment_percentages.get("Positive", 0) or 0,
                "neutral": sentiment_percentages.get("Neutral", 0) or 0,
            }]
            yield "data: " + json.dumps(payload) + "\n\n"

            payload["competitorRating_averageSentiment_chart"] = [{
                "googleRating": float(business_rating),
                "averageSentiment": sentiment_summary.get("average_polarity", 0) or 0,
                "competitorName": business_name,
            }]
            yield "data: " + json.dumps(payload) + "\n\n"

            payload["reviewsAnalyzedPerCompetitor"] = [{
                "name": business_name, "reviews": total_reviews or 0,
            }]
            yield "data: " + json.dumps(payload) + "\n\n"

            insights_obj = ai_insights.get("insights", {}) or {}
            ai_full = insights_obj.get("full_analysis") or ai_insights.get("full_analysis") or ""
            ai_summary = insights_obj.get("summary") or ai_insights.get("summary", "") or ""
            ai_text = ai_full or ai_summary or ""
            payload["competitorsDetails"] = [{
                "address": business_info.get("address", "") or "",
                "googleMaps": business_info.get("google_maps_url", google_maps_url) or "",
                "aiInsights": ai_text,
            }]
            payload["allTokensUsed"] = total_tokens
            yield "data: " + json.dumps(payload) + "\n\n"

        response = Response(
            stream_with_context(stream_response()),
            mimetype="text/event-stream",
        )
        response.headers["Cache-Control"] = "no-cache, no-transform"
        response.headers["X-Accel-Buffering"] = "no"
        response.headers["Connection"] = "keep-alive"
        response.headers["Transfer-Encoding"] = "chunked"
        return response

    except Exception as e:
        return jsonify({"error": f"Failed to process request: {str(e)}"}), 500


# ── Test UI ──────────────────────────────────────────────────────────────────

HTML_PAGE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sentiment Analysis API Tester</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        h1 { text-align: center; margin: 20px 0; font-size: 2rem; background: linear-gradient(135deg, #60a5fa, #a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        .tab { padding: 12px 24px; background: #1e293b; border: 1px solid #334155; border-radius: 8px; cursor: pointer; font-size: 1rem; color: #94a3b8; transition: all 0.3s; }
        .tab.active { background: #3b82f6; color: white; border-color: #3b82f6; }
        .tab:hover { border-color: #60a5fa; }
        .panel { display: none; }
        .panel.active { display: block; }
        .form-group { margin-bottom: 16px; }
        .form-group label { display: block; margin-bottom: 6px; font-weight: 600; color: #94a3b8; font-size: 0.9rem; }
        .form-group input { width: 100%; padding: 12px; background: #1e293b; border: 1px solid #334155; border-radius: 8px; color: #e2e8f0; font-size: 1rem; }
        .form-group input:focus { outline: none; border-color: #3b82f6; }
        .btn { padding: 14px 32px; background: linear-gradient(135deg, #3b82f6, #8b5cf6); color: white; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; font-weight: 600; }
        .btn:hover { opacity: 0.9; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .output-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; margin-top: 24px; }
        .status { padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: 600; }
        .status.idle { background: #334155; color: #94a3b8; }
        .status.running { background: #fbbf2433; color: #fbbf24; }
        .status.done { background: #22c55e33; color: #22c55e; }
        .status.error { background: #ef444433; color: #ef4444; }
        .output-box { background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 16px; min-height: 300px; max-height: 600px; overflow-y: auto; font-family: 'Consolas', monospace; font-size: 0.85rem; white-space: pre-wrap; word-break: break-all; line-height: 1.6; }
        .card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 24px; }
        .card h2 { margin-bottom: 20px; color: #e2e8f0; font-size: 1.2rem; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-top: 16px; }
        .stat { background: #0f172a; padding: 12px; border-radius: 8px; text-align: center; }
        .stat .label { font-size: 0.75rem; color: #64748b; text-transform: uppercase; }
        .stat .value { font-size: 1.1rem; font-weight: 700; color: #60a5fa; margin-top: 4px; }
        .note { background: #22c55e22; border: 1px solid #22c55e44; color: #22c55e; padding: 10px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 0.85rem; }
    </style>
</head>
<body>
    <div class="container">
        <h1>&#128269; Sentiment Analysis API Tester</h1>
        <div class="note">&#10003; Standalone server — all sentiment routes loaded directly. No proxy needed.</div>
        <div class="tabs">
            <div class="tab active" onclick="switchTab('competitor')">Competitor Sentiment</div>
            <div class="tab" onclick="switchTab('business')">Business Sentiment</div>
            <div class="tab" onclick="switchTab('raw')">Raw Event Log</div>
        </div>
        <div id="panel-competitor" class="panel active">
            <div class="card">
                <h2>POST /ai/customer-sentiment-analysis</h2>
                <p style="color:#64748b; margin-bottom:16px; font-size:0.9rem;">Analyzes competitors by scraping Google Maps + Trustpilot reviews with AI insights.</p>
                <div class="form-group"><label>Industry *</label><input type="text" id="industry" value="diving" /></div>
                <div class="form-group"><label>Country *</label><input type="text" id="country" value="Saudi Arabia" /></div>
                <button class="btn" id="btn-competitor" onclick="runCompetitor()">&#9654; Run Competitor Analysis</button>
            </div>
        </div>
        <div id="panel-business" class="panel">
            <div class="card">
                <h2>POST /ai/business-sentiment-analysis</h2>
                <p style="color:#64748b; margin-bottom:16px; font-size:0.9rem;">Analyzes sentiment for a single business via Google Maps URL.</p>
                <div class="form-group"><label>Google Maps URL *</label><input type="text" id="gmUrl" placeholder="https://www.google.com/maps/place/..." /></div>
                <div class="form-group"><label>Max Reviews (1-500)</label><input type="number" id="maxReviews" value="50" min="1" max="500" /></div>
                <button class="btn" id="btn-business" onclick="runBusiness()">&#9654; Run Business Analysis</button>
            </div>
        </div>
        <div id="panel-raw" class="panel">
            <div class="card">
                <h2>Raw SSE Event Log</h2>
                <button class="btn" style="margin-bottom:12px; background:#334155;" onclick="document.getElementById('rawLog').textContent=''">Clear</button>
                <div class="output-box" id="rawLog" style="min-height:400px;"></div>
            </div>
        </div>
        <div class="output-header">
            <h2 style="color:#e2e8f0;">Response</h2>
            <span id="status" class="status idle">Idle</span>
        </div>
        <div class="stats" id="stats" style="display:none;">
            <div class="stat"><div class="label">Competitors</div><div class="value" id="stat-competitors">-</div></div>
            <div class="stat"><div class="label">Total Reviews</div><div class="value" id="stat-reviews">-</div></div>
            <div class="stat"><div class="label">Avg Rating</div><div class="value" id="stat-rating">-</div></div>
            <div class="stat"><div class="label">Positive</div><div class="value" id="stat-positive" style="color:#22c55e;">-</div></div>
            <div class="stat"><div class="label">Negative</div><div class="value" id="stat-negative" style="color:#ef4444;">-</div></div>
            <div class="stat"><div class="label">Tokens</div><div class="value" id="stat-tokens">-</div></div>
        </div>
        <div class="output-box" id="output">Waiting for request...</div>
    </div>
    <script>
        function switchTab(name) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('panel-' + name).classList.add('active');
        }
        function setStatus(t, c) { const s = document.getElementById('status'); s.textContent = t; s.className = 'status ' + c; }
        function appendOutput(t) { const el = document.getElementById('output'); if (el.textContent === 'Waiting for request...') el.textContent = ''; el.textContent += t + '\n'; el.scrollTop = el.scrollHeight; }
        function appendRaw(t) { const el = document.getElementById('rawLog'); el.textContent += t + '\n'; el.scrollTop = el.scrollHeight; }
        function updateStats(p) {
            document.getElementById('stats').style.display = 'grid';
            document.getElementById('stat-competitors').textContent = p.competitorsAnalyzedNumber ?? '-';
            document.getElementById('stat-reviews').textContent = p.totalReview ?? '-';
            document.getElementById('stat-rating').textContent = p.avgGoogleRating ?? '-';
            document.getElementById('stat-tokens').textContent = p.allTokensUsed ?? '-';
            const pie = p.pieChart || {};
            document.getElementById('stat-positive').textContent = pie.positive ?? '-';
            document.getElementById('stat-negative').textContent = pie.negative ?? '-';
        }
        async function handleSSE(resp) {
            const reader = resp.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();
                for (const line of lines) {
                    if (!line.trim()) continue;
                    appendRaw(line);
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.substring(6));
                            appendOutput('[SSE] ' + new Date().toLocaleTimeString());
                            appendOutput(JSON.stringify(data, null, 2));
                            appendOutput('---');
                            updateStats(data);
                        } catch(e) {}
                    }
                }
            }
        }
        async function runCompetitor() {
            const btn = document.getElementById('btn-competitor'); btn.disabled = true;
            setStatus('Running...', 'running');
            document.getElementById('output').textContent = '';
            document.getElementById('rawLog').textContent = '';
            try {
                const resp = await fetch('/ai/customer-sentiment-analysis', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ industry_field: document.getElementById('industry').value, country: document.getElementById('country').value })
                });
                if (!resp.ok) { appendOutput('ERROR ' + resp.status + ': ' + await resp.text()); setStatus('Error', 'error'); return; }
                await handleSSE(resp); setStatus('Complete', 'done');
            } catch(e) { appendOutput('FETCH ERROR: ' + e.message); setStatus('Error', 'error');
            } finally { btn.disabled = false; }
        }
        async function runBusiness() {
            const btn = document.getElementById('btn-business'); btn.disabled = true;
            setStatus('Running...', 'running');
            document.getElementById('output').textContent = '';
            document.getElementById('rawLog').textContent = '';
            try {
                const resp = await fetch('/ai/business-sentiment-analysis', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ google_maps_url: document.getElementById('gmUrl').value, max_reviews: parseInt(document.getElementById('maxReviews').value) || 200 })
                });
                if (!resp.ok) { appendOutput('ERROR ' + resp.status + ': ' + await resp.text()); setStatus('Error', 'error'); return; }
                await handleSSE(resp); setStatus('Complete', 'done');
            } catch(e) { appendOutput('FETCH ERROR: ' + e.message); setStatus('Error', 'error');
            } finally { btn.disabled = false; }
        }
    </script>
</body>
</html>
"""


@app.route("/")
def test_index():
    return HTML_PAGE


@app.route("/test-health")
def test_health():
    routes = [rule.rule for rule in app.url_map.iter_rules()]
    sentiment_routes = [r for r in routes if "sentiment" in r]
    return jsonify({
        "status": "ok",
        "sentiment_routes": sentiment_routes,
    })


if __name__ == "__main__":
    print("=" * 60)
    print("  Sentiment Analysis API Tester (Standalone)")
    print("  Routes loaded directly from api.py code")
    print("  Open http://localhost:5555 in your browser")
    print("=" * 60)

    routes = [rule.rule for rule in app.url_map.iter_rules() if "sentiment" in rule.rule]
    print(f"\n  Sentiment routes: {routes}")

    app.run(host="0.0.0.0", port=5555, debug=True)