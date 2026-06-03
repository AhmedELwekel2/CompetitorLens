"""
Competitor Search Service

Searches Google Maps for competitors in a given industry/region,
scrapes their reviews, and optionally enriches data with Trustpilot reviews.
"""

import asyncio
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
)
from webdriver_manager.chrome import ChromeDriverManager

from trustpilot_scraper import TrustpilotScraper

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class CompetitorSearchService:
    """Searches for competitors on Google Maps and enriches with Trustpilot data."""

    def __init__(self):
        self.trustpilot_scraper = TrustpilotScraper()

    # ------------------------------------------------------------------ #
    #  Browser setup (same pattern as SentimentAnalyzer)                  #
    # ------------------------------------------------------------------ #
    def _setup_browser(self):
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-sync")
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--lang=en-US")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        )
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option("useAutomationExtension", False)
        prefs = {
            "profile.default_content_setting_values": {"notifications": 2, "geolocation": 2},
            "profile.managed_default_content_settings": {"images": 1},
        }
        options.add_experimental_option("prefs", prefs)

        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            driver.set_page_load_timeout(60)
            return driver
        except Exception as e:
            logging.warning(f"Chrome driver install failed: {e}, trying system driver...")
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(60)
            return driver

    # ------------------------------------------------------------------ #
    #  Search Google Maps for competitors                                  #
    # ------------------------------------------------------------------ #
    def _search_google_maps(self, driver, industry: str, region: str, max_competitors: int) -> List[Dict[str, Any]]:
        """Search Google Maps and return a list of competitor basic info."""
        query = f"{industry} in {region}"
        search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}/?hl=en"
        logging.info(f"Searching Google Maps: {search_url}")

        driver.get(search_url)
        time.sleep(5)

        # Dismiss cookie consent if present
        for selector in ["[aria-label='Accept all']", "[aria-label*='Accept']"]:
            try:
                btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(2)
                break
            except (TimeoutException, NoSuchElementException):
                continue

        # Wait for results to load
        results_selectors = [
            'div[role="feed"] a[href*="/maps/place/"]',
            'div.m6QErb.XiKgde a[href*="/maps/place/"]',
            'a[href*="/maps/place/"]',
        ]

        result_links = []
        for selector in results_selectors:
            try:
                result_links = WebDriverWait(driver, 15).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                )
                if result_links:
                    break
            except TimeoutException:
                continue

        if not result_links:
            logging.warning("No Google Maps results found")
            return []

        competitors = []
        seen_names = set()

        for link_el in result_links[:max_competitors * 2]:  # grab extra in case some fail
            if len(competitors) >= max_competitors:
                break
            try:
                href = link_el.get_attribute("href") or ""
                if "/maps/place/" not in href:
                    continue

                # Try to extract name from the link's aria-label or text
                name = link_el.get_attribute("aria-label") or ""
                if not name:
                    name_el = link_el.find_elements(By.CSS_SELECTOR, 
                        'div.fontHeadlineSmall, span.fontHeadlineSmall, div[class*="fontHeadline"]')
                    name = name_el[0].text.strip() if name_el else ""

                if not name or name in seen_names:
                    continue
                seen_names.add(name)

                # Extract rating and review count from the result card
                rating = 0.0
                review_count = 0
                try:
                    rating_el = link_el.find_elements(By.CSS_SELECTOR, 'span[role="img"]')
                    if rating_el:
                        aria = rating_el[0].get_attribute("aria-label") or ""
                        rating_match = re.search(r"(\d+\.?\d*)", aria)
                        if rating_match:
                            rating = float(rating_match.group(1))
                        review_match = re.search(r"(\d[\d,]*)\s*review", aria, re.IGNORECASE)
                        if review_match:
                            review_count = int(review_match.group(1).replace(",", ""))
                except Exception:
                    pass

                # Extract address
                address = ""
                try:
                    addr_parts = link_el.find_elements(By.CSS_SELECTOR, 
                        'div[class*="fontBodyMedium"] span:not([role="img"])')
                    for part in addr_parts:
                        txt = part.text.strip()
                        if txt and txt != name and "star" not in txt.lower():
                            address = txt
                            break
                except Exception:
                    pass

                competitors.append({
                    "name": name,
                    "rating": rating,
                    "review_count": review_count,
                    "address": address,
                    "google_maps_url": href,
                    "reviews_url": href,
                })
            except (StaleElementReferenceException, Exception) as e:
                logging.warning(f"Error parsing result: {e}")
                continue

        return competitors

    # ------------------------------------------------------------------ #
    #  Scrape reviews for a single competitor from Google Maps             #
    # ------------------------------------------------------------------ #
    def _scrape_competitor_reviews(self, driver, competitor: Dict, max_reviews: int) -> List[Dict[str, str]]:
        """Click into a competitor's page and scrape reviews."""
        url = competitor.get("reviews_url", "")
        if not url:
            return []

        # Ensure reviews tab
        if "#reviews" not in url:
            url = url.split("?")[0].split("#")[0] + "?hl=en#reviews"

        logging.info(f"Scraping reviews for {competitor['name']} from {url}")
        try:
            driver.get(url)
            time.sleep(5)
        except Exception as e:
            logging.error(f"Failed to navigate to {url}: {e}")
            return []

        # Try clicking reviews tab if we're not on it
        if "#reviews" not in driver.current_url:
            for sel in ['button[aria-label*="Reviews"]', 'button[data-value="Reviews"]', 'button[jsaction*="reviews"]']:
                try:
                    tab = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                    )
                    driver.execute_script("arguments[0].click();", tab)
                    time.sleep(3)
                    break
                except (TimeoutException, NoSuchElementException):
                    continue

        # Find review elements
        review_selectors = [
            'div.jftiEf.fontBodyMedium',
            'div[data-review-id]',
            'div.jftiEf',
            'div[role="article"]',
        ]

        reviews_els = []
        for sel in review_selectors:
            try:
                reviews_els = driver.find_elements(By.CSS_SELECTOR, sel)
                if reviews_els:
                    break
            except Exception:
                continue

        if not reviews_els:
            logging.warning(f"No reviews found for {competitor['name']}")
            return []

        # Scroll to load more reviews
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.common.actions.wheel_input import ScrollOrigin

        action = ActionChains(driver)
        scroll_attempts = 0
        while len(reviews_els) < max_reviews and scroll_attempts < 15:
            last = reviews_els[-1] if reviews_els else None
            if last:
                try:
                    scroll_origin = ScrollOrigin.from_element(last)
                    action.scroll_from_origin(scroll_origin, 0, 1000).perform()
                except Exception:
                    driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(1.5)

            for sel in review_selectors:
                try:
                    new_els = driver.find_elements(By.CSS_SELECTOR, sel)
                    if new_els:
                        reviews_els = new_els
                        break
                except Exception:
                    continue

            if len(reviews_els) == len(reviews_els):
                scroll_attempts += 1
            else:
                scroll_attempts = 0

        # Extract review text
        reviews = []
        for el in reviews_els[:max_reviews]:
            try:
                # Expand review if truncated
                for btn_sel in ['button.w8nwRe.kyuRq[aria-expanded="false"]', 'button[aria-label*="More"]']:
                    try:
                        btn = el.find_element(By.CSS_SELECTOR, btn_sel)
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(0.3)
                        break
                    except (NoSuchElementException, Exception):
                        continue

                text_selectors = ['span.wiI7pd', 'div.MyEned', 'div.review-text']
                review_text = ""
                for ts in text_selectors:
                    try:
                        text_el = el.find_element(By.CSS_SELECTOR, ts)
                        review_text = text_el.text.strip()
                        if review_text:
                            break
                    except NoSuchElementException:
                        continue

                if review_text:
                    reviews.append({"review_text": review_text})
            except Exception:
                continue

        logging.info(f"Scraped {len(reviews)} reviews for {competitor['name']}")
        return reviews

    # ------------------------------------------------------------------ #
    #  Main pipeline: search_competitors_with_trustpilot                   #
    # ------------------------------------------------------------------ #
    async def search_competitors_with_trustpilot(
        self,
        industry: str,
        region: str,
        max_competitors: int = 5,
        max_reviews_per_competitor: int = 100,
    ) -> Dict[str, Any]:
        """
        Full pipeline:
        1. Search Google Maps for competitors
        2. Scrape Google Maps reviews for each
        3. Search & scrape Trustpilot for each
        4. Return combined data
        """
        result = await asyncio.to_thread(
            self._sync_search_pipeline,
            industry, region, max_competitors, max_reviews_per_competitor,
        )
        return result

    def _sync_search_pipeline(
        self, industry, region, max_competitors, max_reviews_per_competitor,
        progress_callback=None,
    ) -> Dict[str, Any]:
        driver = None
        try:
            driver = self._setup_browser()

            # Step 1: Search Google Maps
            if progress_callback:
                progress_callback("searching_google_maps", "Searching Google Maps for competitors...")
            competitors = self._search_google_maps(driver, industry, region, max_competitors)

            if not competitors:
                if progress_callback:
                    progress_callback("no_competitors", "No competitors found on Google Maps")
                return {"competitors": [], "output_file": None}

            if progress_callback:
                progress_callback("found_competitors", f"Found {len(competitors)} competitors", {"count": len(competitors)})

            # Step 2: Scrape Google Maps reviews for each competitor
            for i, comp in enumerate(competitors):
                if progress_callback:
                    progress_callback(
                        "scraping_google_maps",
                        f"Scraping Google Maps reviews for {comp['name']} ({i+1}/{len(competitors)})",
                        {"current": i+1, "total": len(competitors), "name": comp["name"]},
                    )
                try:
                    gm_reviews = self._scrape_competitor_reviews(
                        driver, comp, max_reviews_per_competitor
                    )
                    comp["google_maps_reviews"] = gm_reviews
                    # Update review count if we got reviews
                    if gm_reviews:
                        comp["review_count"] = comp.get("review_count") or len(gm_reviews)
                except Exception as e:
                    logging.warning(f"Error scraping reviews for {comp['name']}: {e}")
                    comp["google_maps_reviews"] = []

            # Step 3: Try Trustpilot enrichment for each competitor
            for i, comp in enumerate(competitors):
                if progress_callback:
                    progress_callback(
                        "searching_trustpilot",
                        f"Searching Trustpilot for {comp['name']} ({i+1}/{len(competitors)})",
                        {"current": i+1, "total": len(competitors), "name": comp["name"]},
                    )
                try:
                    tp_url = self.trustpilot_scraper.search_business_url(comp["name"])
                    comp["trustpilot_url"] = tp_url

                    if tp_url:
                        if progress_callback:
                            progress_callback(
                                "scraping_trustpilot",
                                f"Scraping Trustpilot reviews for {comp['name']} ({i+1}/{len(competitors)})",
                                {"current": i+1, "total": len(competitors), "name": comp["name"]},
                            )
                        tp_result = self.trustpilot_scraper.scrape_trustpilot_reviews(
                            tp_url, max_reviews=max_reviews_per_competitor
                        )
                        comp["trustpilot_business_info"] = tp_result.get("business_info", {})
                        comp["trustpilot_reviews"] = [
                            {"review_text": r.get("review_text", "")}
                            for r in tp_result.get("reviews", [])
                            if r.get("review_text")
                        ]
                    else:
                        comp["trustpilot_business_info"] = None
                        comp["trustpilot_reviews"] = []
                except Exception as e:
                    logging.warning(f"Trustpilot enrichment failed for {comp['name']}: {e}")
                    comp["trustpilot_url"] = None
                    comp["trustpilot_business_info"] = None
                    comp["trustpilot_reviews"] = []

            if progress_callback:
                progress_callback("scraping_complete", f"Data collection complete for {len(competitors)} competitors", {"count": len(competitors)})

            return {"competitors": competitors, "output_file": None}

        except Exception as e:
            logging.error(f"Competitor search pipeline error: {e}")
            import traceback
            logging.error(traceback.format_exc())
            return {"competitors": [], "output_file": None}
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

    # ------------------------------------------------------------------ #
    #  Alternative entry: search_and_get_reviews_urls                      #
    # ------------------------------------------------------------------ #
    async def search_and_get_reviews_urls(
        self, industry: str, region: str, max_competitors: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for competitors and return their info with reviews URLs."""
        result = await self.search_competitors_with_trustpilot(
            industry=industry,
            region=region,
            max_competitors=max_competitors,
            max_reviews_per_competitor=50,
        )
        competitors = result.get("competitors", [])
        # Ensure each competitor has a reviews_url
        for comp in competitors:
            if "reviews_url" not in comp:
                url = comp.get("google_maps_url", "")
                if url:
                    comp["reviews_url"] = url.split("?")[0].split("#")[0] + "?hl=en#reviews"
                else:
                    comp["reviews_url"] = ""
        return competitors