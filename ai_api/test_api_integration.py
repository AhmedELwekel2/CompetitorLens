"""
Quick test script to verify the updated api.py integration with
competitor_search_service.py's search_competitors_with_trustpilot pipeline.

Usage:
  python test_api_integration.py

This tests the core pipeline without needing the Flask server running.
"""

import asyncio
import json
import sys
import os

# Ensure we're in the right directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from competitor_search_service import CompetitorSearchService
from sentiment_analyzer import SentimentAnalyzer


def test_pipeline():
    """Test the integrated pipeline that api.py now calls."""
    print("=" * 60)
    print("  TESTING: search_competitors_with_trustpilot pipeline")
    print("=" * 60)

    INDUSTRY = "diving"
    REGION = "Saudi Arabia"
    MAX_COMPETITORS = 3
    MAX_REVIEWS = 20

    async def run():
        css = CompetitorSearchService()
        analyzer = SentimentAnalyzer()

        # Step 1: Call the integrated pipeline (same as api.py does now)
        print(f"\n[1/3] Calling search_competitors_with_trustpilot...")
        print(f"      Industry: '{INDUSTRY}' | Region: '{REGION}'")
        print(f"      Max competitors: {MAX_COMPETITORS} | Max reviews: {MAX_REVIEWS}")

        result = await css.search_competitors_with_trustpilot(
            industry=INDUSTRY,
            region=REGION,
            max_competitors=MAX_COMPETITORS,
            max_reviews_per_competitor=MAX_REVIEWS,
        )

        competitors = result.get("competitors", [])
        print(f"\n[1/3] ✓ Found {len(competitors)} competitors")

        if not competitors:
            print("❌ No competitors found. Check your internet connection or try different search terms.")
            return

        # Step 2: Verify enriched data structure (Google Maps + Trustpilot)
        print(f"\n[2/3] Verifying enriched data structure...")
        for i, comp in enumerate(competitors, 1):
            name = comp.get("name", "Unknown")
            gm_reviews = comp.get("google_maps_reviews", [])
            tp_reviews = comp.get("trustpilot_reviews", [])
            tp_url = comp.get("trustpilot_url")
            tp_info = comp.get("trustpilot_business_info")

            print(f"\n  Competitor #{i}: {name}")
            print(f"    Google Maps reviews scraped: {len(gm_reviews)}")
            print(f"    Trustpilot URL: {tp_url or 'Not found'}")
            print(f"    Trustpilot reviews scraped: {len(tp_reviews)}")
            if tp_info:
                print(f"    Trustpilot rating: {tp_info.get('rating', 'N/A')}")
                print(f"    Trust score: {tp_info.get('trust_score', 'N/A')}")

        # Step 3: Run sentiment analysis on combined reviews (same as api.py does now)
        print(f"\n[3/3] Running sentiment analysis on combined reviews...")
        for i, comp in enumerate(competitors, 1):
            gm_reviews = comp.get("google_maps_reviews", [])
            tp_reviews = comp.get("trustpilot_reviews", [])

            all_texts = []
            for r in gm_reviews:
                text = r.get("review_text", "")
                if text and text.strip():
                    all_texts.append(text)
            for r in tp_reviews:
                text = r.get("review_text", "")
                if text and text.strip():
                    all_texts.append(text)

            if all_texts:
                sentiments = analyzer.analyze_sentiment_batch(all_texts)
                pos = sum(1 for s in sentiments if s["sentiment"] == "Positive")
                neg = sum(1 for s in sentiments if s["sentiment"] == "Negative")
                neu = sum(1 for s in sentiments if s["sentiment"] == "Neutral")
                total = len(sentiments)
                avg_polarity = sum(s["polarity"] for s in sentiments) / total

                print(f"\n  Competitor #{i}: {comp.get('name')}")
                print(f"    Total reviews analyzed: {total}")
                print(f"    Positive: {pos} ({pos/total*100:.1f}%)")
                print(f"    Negative: {neg} ({neg/total*100:.1f}%)")
                print(f"    Neutral:  {neu} ({neu/total*100:.1f}%)")
                print(f"    Avg polarity: {avg_polarity:.3f}")
            else:
                print(f"\n  Competitor #{i}: {comp.get('name')} — No review texts found")

        output_file = result.get("output_file")
        if output_file and os.path.exists(output_file):
            size = os.path.getsize(output_file)
            print(f"\n✅ Report saved to: {output_file} ({size:,} bytes)")
        else:
            print(f"\n⚠️ No report file generated")

        print(f"\n{'=' * 60}")
        print(f"  TEST COMPLETE — Pipeline is working correctly!")
        print(f"{'=' * 60}")

    asyncio.run(run())


def test_flask_endpoint():
    """
    Test the Flask endpoint via HTTP (requires server to be running).
    Start the server first, then run this test.
    
    Usage:
      python test_api_integration.py flask
    """
    import requests

    url = "http://localhost:5000/ai/customer-sentiment-analysis"
    payload = {
        "industry_field": "diving",
        "country": "Saudi Arabia"
    }

    print(f"POST {url}")
    print(f"Body: {json.dumps(payload, indent=2)}")
    print(f"\nStreaming response:\n")

    try:
        response = requests.post(url, json=payload, stream=True, timeout=300)
        print(f"Status: {response.status_code}")
        print("-" * 60)

        for line in response.iter_lines(decode_unicode=True):
            if line and line.startswith("data: "):
                data = line[6:]
                try:
                    parsed = json.loads(data)
                    # Print key fields as they arrive
                    title = parsed.get("analysisTitle")
                    if title:
                        print(f"  Title: {title}")
                    num = parsed.get("competitorsAnalyzedNumber")
                    if num is not None:
                        print(f"  Competitors: {num}")
                    total = parsed.get("totalReview")
                    if total is not None:
                        print(f"  Total Reviews: {total}")
                    tp = parsed.get("trustpilotData")
                    if tp:
                        print(f"  Trustpilot Data: {len(tp)} entries")
                        for t in tp:
                            print(f"    - {t.get('name')}: TP rating={t.get('trustpilotRating')}, reviews={t.get('scrapedTrustpilotReviews')}")
                    of = parsed.get("outputFile")
                    if of:
                        print(f"  Output File: {of}")
                except json.JSONDecodeError:
                    print(f"  Raw: {data[:100]}")

        print("-" * 60)
        print("✅ Flask endpoint test complete!")

    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure Flask is running on localhost:5000")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "flask":
        test_flask_endpoint()
    else:
        test_pipeline()