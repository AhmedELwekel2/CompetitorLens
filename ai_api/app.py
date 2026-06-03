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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def validate_url(url):
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    return url


def is_valid_url(url):
    return url.startswith("http://") or url.startswith("https://")


# ── POST /ai/customer-sentiment-analysis ──────────────────────────────────────

@app.post("/ai/customer-sentiment-analysis")
def customer_sentiment_analysis():
    try:
        body = request.get_json(force=True, silent=True) or {}

        industry = (body.get("industry_field") or "").strip()
        country = (body.get("country") or "").strip()

        if not industry or not country:
            return jsonify({"error": "industry_field and country are required"}), 400

        MAX_COMPETITORS = 3
        REVIEWS_PER_COMPETITOR = 10

        def stream_response():
            css = CompetitorSearchService()
            analyzer = SentimentAnalyzer()
            total_tokens = 0
            total_input_tokens = 0
            total_output_tokens = 0
            total_cost = 0.0

            async def run_competitor_analysis() -> Dict[str, Any]:
                # Step 1: Use the integrated pipeline (Google Maps + Trustpilot)
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

                # Step 2: Run sentiment analysis on collected reviews (GM + Trustpilot)
                competitor_results = []
                all_sentiments = []

                for comp in competitors:
                    gm_reviews = comp.get("google_maps_reviews", [])
                    tp_reviews = comp.get("trustpilot_reviews", [])

                    # Collect all review texts from both sources
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

                    # Run sentiment analysis on all review texts
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

                    # Generate AI insights per competitor
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

                # Combined analysis across all competitors
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

            # Extract token usage from all competitor results
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
                "pieChart": {
                    "title": None,
                    "positive": None,
                    "negative": None,
                    "neutral": None,
                },
                "competitorSentimentComparisonChart": None,
                "competitorRating_averageSentiment_chart": None,
                "reviewsAnalyzedPerCompetitor": None,
                "competitorsDetails": None,
                "trustpilotData": None,
                "outputFile": output_file,
                "allTokensUsed": 0
            }

            yield "data: " + json.dumps(payload) + '\n\n'

            payload["analysisTitle"] = f"{industry.title()} Industry Analysis - {country} (Google Maps + Trustpilot)"
            yield "data: " + json.dumps(payload) + '\n\n'

            total_competitors = combined.get("total_competitors_analyzed", len(competitor_results)) or 0
            total_reviews = combined.get("total_reviews_analyzed", 0) or 0
            avg_rating = round(
                sum([(r.get("competitor_info", {}).get("rating", 0) or 0) for r in competitor_results]) / max(len(competitor_results), 1), 2
            ) if competitor_results else 0

            payload["competitorsAnalyzedNumber"] = total_competitors
            payload["totalReview"] = total_reviews
            payload["avgGoogleRating"] = avg_rating
            yield "data: " + json.dumps(payload) + '\n\n'

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
            yield "data: " + json.dumps(payload) + '\n\n'

            payload["pieChart"]["title"] = f"{industry.title()} sentiment distribution in {country} (Google Maps + Trustpilot)"
            payload["pieChart"]["positive"] = combined_summary.get("sentiment_percentages", {}).get("Positive", 0) or 0
            payload["pieChart"]["negative"] = combined_summary.get("sentiment_percentages", {}).get("Negative", 0) or 0
            payload["pieChart"]["neutral"] = combined_summary.get("sentiment_percentages", {}).get("Neutral", 0) or 0
            yield "data: " + json.dumps(payload) + '\n\n'

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
            yield "data: " + json.dumps(payload) + '\n\n'

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
            yield "data: " + json.dumps(payload) + '\n\n'

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
            yield "data: " + json.dumps(payload) + '\n\n'

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

            # Update token usage in payload
            payload["allTokensUsed"] = total_tokens
            yield "data: " + json.dumps(payload) + '\n\n'

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


# ── POST /ai/business-sentiment-analysis ──────────────────────────────────────

@app.post("/ai/business-sentiment-analysis")
def business_sentiment_analysis():
    """
    Analyze sentiment for a user's own business using Google Maps URL
    """
    try:
        body = request.get_json(force=True, silent=True) or {}

        if not body:
            return jsonify({"error": "Request body is required", "received": str(body)}), 400

        google_maps_url = (body.get("google_maps_url") or "").strip()

        # Validate and limit max_reviews
        try:
            max_reviews = int(body.get("max_reviews", 200))
            max_reviews = max(1, min(max_reviews, 500))  # Between 1 and 500
        except (ValueError, TypeError):
            max_reviews = 200  # Default to 200 reviews

        if not google_maps_url:
            return jsonify({"error": "google_maps_url is required", "received_body": body}), 400

        # Validate and normalize URL
        google_maps_url = validate_url(google_maps_url)

        # Validate URL format
        if not is_valid_url(google_maps_url):
            return jsonify({"error": "Invalid URL format. Please provide a valid URL.", "url": google_maps_url}), 400

        # Check if it's a Google Maps URL (more flexible check)
        url_lower = google_maps_url.lower()
        if "maps.google.com" not in url_lower and "google.com/maps" not in url_lower:
            return jsonify({"error": "Invalid Google Maps URL. Please provide a valid Google Maps business URL.", "url": google_maps_url}), 400

        def stream_response():
            analyzer = SentimentAnalyzer()
            total_tokens = 0
            total_input_tokens = 0
            total_output_tokens = 0
            total_cost = 0.0

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

            # Check for errors
            if analysis_results.get("error"):
                error_payload = {
                    "error": analysis_results.get("error"),
                    "analysisTitle": None,
                    "competitorsAnalyzedNumber": None,
                    "totalReview": None,
                    "avgGoogleRating": None,
                    "competitorsAnalyzed": None,
                    "pieChart": None,
                    "competitorSentimentComparisonChart": None,
                    "competitorRating_averageSentiment_chart": None,
                    "reviewsAnalyzedPerCompetitor": None,
                    "competitorsDetails": None,
                    "allTokensUsed": 0
                }
                yield "data: " + json.dumps(error_payload) + '\n\n'
                return

            business_info = analysis_results.get("business_info", {})
            sentiment_summary = analysis_results.get("sentiment_summary", {})
            ai_insights = analysis_results.get("ai_insights", {})
            total_reviews = analysis_results.get("total_reviews_analyzed", 0)

            # Extract token usage from ai_insights
            if isinstance(ai_insights, dict):
                insights_obj = ai_insights.get("insights", {}) or {}
                token_usage_data = insights_obj.get("token_usage") or ai_insights.get("token_usage") or {}
                if token_usage_data:
                    total_input_tokens = token_usage_data.get("input_tokens", 0)
                    total_output_tokens = token_usage_data.get("output_tokens", 0)
                    total_tokens = token_usage_data.get("total_tokens", 0)
                    total_cost = token_usage_data.get("total_cost", 0.0)

            # Initialize payload structure to match competitors analysis format
            payload = {
                "analysisTitle": None,
                "competitorsAnalyzedNumber": None,
                "totalReview": None,
                "avgGoogleRating": None,
                "competitorsAnalyzed": None,
                "pieChart": {
                    "title": None,
                    "positive": None,
                    "negative": None,
                    "neutral": None,
                },
                "competitorSentimentComparisonChart": None,
                "competitorRating_averageSentiment_chart": None,
                "reviewsAnalyzedPerCompetitor": None,
                "competitorsDetails": None,
                "allTokensUsed": 0
            }

            yield "data: " + json.dumps(payload) + '\n\n'

            # Set analysis title
            business_name = business_info.get("name", "Unknown Business")
            payload["analysisTitle"] = f"{business_name} - Sentiment Analysis"
            yield "data: " + json.dumps(payload) + '\n\n'

            # Set basic metrics (mapped to competitors format)
            business_rating = business_info.get("rating", 0) or 0
            payload["competitorsAnalyzedNumber"] = 1
            payload["totalReview"] = total_reviews or 0
            payload["avgGoogleRating"] = float(business_rating)
            yield "data: " + json.dumps(payload) + '\n\n'

            # Map to competitorsAnalyzed array (single entry)
            sentiment_percentages = sentiment_summary.get("sentiment_percentages", {})
            payload["competitorsAnalyzed"] = [{
                "name": business_name,
                "googleRating": float(business_rating),
                "reviewsAnalyzed": total_reviews or 0,
                "positivePercentage": sentiment_percentages.get("Positive", 0) or 0,
                "negativePercentage": sentiment_percentages.get("Negative", 0) or 0,
                "avgSentiment": sentiment_summary.get("average_polarity", 0) or 0,
            }]
            yield "data: " + json.dumps(payload) + '\n\n'

            # Set pie chart data
            payload["pieChart"]["title"] = f"{business_name} - Sentiment Distribution"
            payload["pieChart"]["positive"] = sentiment_percentages.get("Positive", 0) or 0
            payload["pieChart"]["negative"] = sentiment_percentages.get("Negative", 0) or 0
            payload["pieChart"]["neutral"] = sentiment_percentages.get("Neutral", 0) or 0
            yield "data: " + json.dumps(payload) + '\n\n'

            # Map to competitorSentimentComparisonChart (single entry)
            payload["competitorSentimentComparisonChart"] = [{
                "name": business_name,
                "negative": sentiment_percentages.get("Negative", 0) or 0,
                "positive": sentiment_percentages.get("Positive", 0) or 0,
                "neutral": sentiment_percentages.get("Neutral", 0) or 0,
            }]
            yield "data: " + json.dumps(payload) + '\n\n'

            # Map to competitorRating_averageSentiment_chart (single entry)
            payload["competitorRating_averageSentiment_chart"] = [{
                "googleRating": float(business_rating),
                "averageSentiment": sentiment_summary.get("average_polarity", 0) or 0,
                "competitorName": business_name,
            }]
            yield "data: " + json.dumps(payload) + '\n\n'

            # Map to reviewsAnalyzedPerCompetitor (single entry)
            payload["reviewsAnalyzedPerCompetitor"] = [{
                "name": business_name,
                "reviews": total_reviews or 0,
            }]
            yield "data: " + json.dumps(payload) + '\n\n'

            # Map to competitorsDetails (single entry with AI insights)
            insights_obj = ai_insights.get("insights", {}) or {}
            ai_full = insights_obj.get("full_analysis") or ai_insights.get("full_analysis") or ""
            ai_summary = insights_obj.get("summary") or ai_insights.get("summary", "") or ""
            ai_text = ai_full or ai_summary or ""

            payload["competitorsDetails"] = [{
                "address": business_info.get("address", "") or "",
                "googleMaps": business_info.get("google_maps_url", google_maps_url) or "",
                "aiInsights": ai_text,
            }]

            # Update token usage in payload
            payload["allTokensUsed"] = total_tokens
            yield "data: " + json.dumps(payload) + '\n\n'

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


# ── Health check ───────────────────────────────────────────────────────────────

@app.route("/ai/health")
def health():
    return jsonify({"status": "ok", "service": "CompetitorLens AI API"})


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  CompetitorLens AI API Server")
    print("  Running on http://localhost:5000")
    print("=" * 60)

    routes = [rule.rule for rule in app.url_map.iter_rules() if "ai" in rule.rule]
    print(f"\n  AI routes: {routes}\n")

    app.run(host="0.0.0.0", port=5000, debug=True)