"""
Trustpilot Scraper Service

Scrapes business reviews from Trustpilot using Selenium (headless browser),
following the same architecture pattern as the existing Google Maps scrapers.

Trustpilot URL format: https://www.trustpilot.com/review/<business-slug>
Example: https://www.trustpilot.com/review/www.amazon.com
"""

import asyncio
import json
import logging
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
)
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class TrustpilotScraper:
    """Scrapes business information and reviews from Trustpilot."""

    # ------------------------------------------------------------------ #
    #  Browser setup (mirrors SentimentAnalyzer / CompetitorSearchService) #
    # ------------------------------------------------------------------ #
    def setup_browser(self):
        try:
            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-software-rasterizer")
            options.add_argument("--window-size=1920,1080")
            options.add_argument(
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
            )
            # Memory / crash prevention
            for flag in [
                "--disable-extensions",
                "--disable-plugins",
                "--disable-background-networking",
                "--disable-sync",
                "--disable-default-apps",
                "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding",
                "--disable-backgrounding-occluded-windows",
                "--disable-features=TranslateUI",
                "--disable-ipc-flooding-protection",
                "--disable-crash-reporter",
                "--disable-logging",
                "--log-level=3",
            ]:
                options.add_argument(flag)
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option(
                "excludeSwitches", ["enable-automation", "enable-logging"]
            )
            options.add_experimental_option("useAutomationExtension", False)
            prefs = {
                "profile.default_content_setting_values": {
                    "notifications": 2,
                    "geolocation": 2,
                },
                "profile.managed_default_content_settings": {"images": 1},
            }
            options.add_experimental_option("prefs", prefs)

            # Try system chromedriver first (avoids version mismatch from webdriver_manager)
            for attempt in ("system", "managed"):
                try:
                    if attempt == "system":
                        driver = webdriver.Chrome(options=options)
                    else:
                        logging.info("System chromedriver not found, downloading via webdriver_manager…")
                        service = Service(ChromeDriverManager().install())
                        driver = webdriver.Chrome(service=service, options=options)
                    driver.execute_script(
                        "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
                    )
                    driver.set_page_load_timeout(60)
                    driver.implicitly_wait(3)
                    logging.info("TrustpilotScraper: Chrome WebDriver initialized")
                    return driver
                except Exception as e:
                    logging.warning(f"Chrome ({attempt}) failed: {e}, trying next…")

            raise Exception("All Chrome driver attempts failed")

        except Exception as exc:
            logging.error(f"Browser setup failed: {exc}")
            raise Exception(f"WebDriver setup failed: {exc}")

    def _setup_edge_fallback(self):
        from selenium.webdriver.edge.options import Options as EdgeOptions

        opts = EdgeOptions()
        for flag in [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--window-size=1920,1080",
        ]:
            opts.add_argument(flag)
        opts.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
        )
        driver = webdriver.Edge(options=opts)
        driver.implicitly_wait(10)
        return driver

    # --------------------------------------------------- #
    #  Helper: safe text extraction from a single element  #
    # --------------------------------------------------- #
    @staticmethod
    def _safe_text(parent, selector: str) -> str:
        try:
            el = parent.find_element(By.CSS_SELECTOR, selector)
            return el.text.strip()
        except (NoSuchElementException, StaleElementReferenceException):
            return ""

    @staticmethod
    def _safe_attr(parent, selector: str, attr: str) -> str:
        try:
            el = parent.find_element(By.CSS_SELECTOR, selector)
            return (el.get_attribute(attr) or "").strip()
        except (NoSuchElementException, StaleElementReferenceException):
            return ""

    # --------------------------------------------------------- #
    #  Parse JSON-LD structured data embedded in the page <head> #
    # --------------------------------------------------------- #
    @staticmethod
    def _extract_json_ld(driver) -> List[Dict[str, Any]]:
        scripts = driver.find_elements(
            By.CSS_SELECTOR, 'script[type="application/ld+json"]'
        )
        data: List[Dict[str, Any]] = []
        for s in scripts:
            try:
                parsed = json.loads(s.get_attribute("innerHTML") or "{}")
                if isinstance(parsed, list):
                    data.extend(parsed)
                elif isinstance(parsed, dict):
                    data.append(parsed)
            except Exception:
                continue
        return data

    # ------------------------------------------------------------------ #
    #  Extract high-level business info from the Trustpilot company page  #
    # ------------------------------------------------------------------ #
    def _extract_business_info(self, driver) -> Dict[str, Any]:
        info: Dict[str, Any] = {
            "name": "",
            "trustpilot_url": driver.current_url,
            "trust_score": 0.0,
            "rating": 0.0,
            "review_count": 0,
            "description": "",
            "categories": [],
            "verified": False,
            "location": "",
        }

        # ---- Try JSON-LD first (most reliable) ----
        json_ld_list = self._extract_json_ld(driver)
        for ld in json_ld_list:
            ld_type = ld.get("@type", "")
            if ld_type in ("LocalBusiness", "Organization", "Product", "Store"):
                info["name"] = ld.get("name", info["name"])
                info["description"] = ld.get("description", info["description"])
                agg = ld.get("aggregateRating") or {}
                if agg:
                    info["rating"] = float(agg.get("ratingValue", 0) or 0)
                    info["review_count"] = int(agg.get("reviewCount", 0) or 0)
                address = ld.get("address") or {}
                if isinstance(address, dict):
                    info["location"] = ", ".join(
                        filter(None, [address.get("addressLocality", ""), address.get("addressCountry", "")])
                    )
                break  # use first matching schema

        # ---- Fallback: scrape visible DOM elements ----
        if not info["name"]:
            h1_raw = self._safe_text(driver, "h1")
            if h1_raw:
                # Trustpilot h1 often includes "Reviews X,XXX" on a new line
                info["name"] = h1_raw.split("\n")[0].strip()
                # Try to extract review count from the "Reviews X,XXX" part
                if info["review_count"] == 0:
                    rc_match = re.search(r"Reviews?\s*([\d,]+)", h1_raw, re.IGNORECASE)
                    if rc_match:
                        info["review_count"] = int(rc_match.group(1).replace(",", ""))

        # Trust score (e.g. "3.9 / 5")
        if info["trust_score"] == 0.0:
            ts_text = self._safe_text(
                driver,
                'span.typography_heading-m__T_Tf3, '
                'p.typography_heading-m__T_Tf3',
            )
            if ts_text:
                m = re.search(r"(\d+\.?\d*)", ts_text)
                if m:
                    info["trust_score"] = float(m.group(1))

        # Star rating
        if info["rating"] == 0.0:
            star_els = driver.find_elements(
                By.CSS_SELECTOR,
                'img[alt*="stars"], '
                'img[alt*="Rated"], '
                'div.star-rating img, '
                'div.styles_starRating__sdbkn',
            )
            for el in star_els:
                alt = (el.get_attribute("alt") or el.get_attribute("title") or "").strip()
                m = re.search(r"(\d+\.?\d*)", alt)
                if m:
                    info["rating"] = float(m.group(1))
                    break

        # Review count
        if info["review_count"] == 0:
            rc_text = self._safe_text(
                driver,
                'span.typography_heading-m__T_Tf3, '
                'p.typography_heading-m__T_Tf3, '
                'span[class*="reviewCount"], '
                'label[for*="reviews"]',
            )
            if rc_text:
                m = re.search(r"([\d,]+)", rc_text.replace(",", ""))
                if m:
                    info["review_count"] = int(m.group(1).replace(",", ""))

        # Verified badge
        try:
            driver.find_element(
                By.CSS_SELECTOR,
                'svg[class*="verified"], '
                'span[class*="verified"], '
                'img[alt*="Verified"]',
            )
            info["verified"] = True
        except NoSuchElementException:
            pass

        # Categories / tags
        tag_els = driver.find_elements(
            By.CSS_SELECTOR,
            'a[class*="category"], '
            'span[class*="tag"], '
            'nav[aria-label*="Category"] a',
        )
        info["categories"] = list({t.text.strip() for t in tag_els if t.text.strip()})[:10]

        return info

    # --------------------------------------------------- #
    #  Extract individual review data from a review card  #
    # --------------------------------------------------- #
    def _extract_single_review(self, review_el) -> Optional[Dict[str, Any]]:
        try:
            # Reviewer name
            name = self._safe_text(review_el, 'span[class*="typography_heading-xs"], '
                                               'a[class*="consumer_name"], '
                                               'span[class*="name"]')
            if not name:
                name = self._safe_text(review_el, '[data-consumer-name-typography]')
            if not name:
                name = "Anonymous"

            # Star rating from aria-label / alt / img src
            stars = 0
            star_selectors = [
                'img[alt*="star"]',
                'img[alt*="Star"]',
                'div[class*="star-rating"] img',
                'section[class*="review"] img',
                'div[data-service-review-rating] img',
                'img[src*="stars"]',
            ]
            for sel in star_selectors:
                try:
                    img = review_el.find_element(By.CSS_SELECTOR, sel)
                    src = img.get_attribute("src") or ""
                    alt = img.get_attribute("alt") or ""
                    for text in [alt, src]:
                        m = re.search(r"(\d)", text)
                        if m:
                            stars = int(m.group(1))
                            break
                    if stars:
                        break
                except NoSuchElementException:
                    continue

            # Fallback: count filled-star SVGs
            if stars == 0:
                try:
                    filled = review_el.find_elements(
                        By.CSS_SELECTOR,
                        'svg[class*="star"] path[fill], '
                        'div[class*="star"] svg',
                    )
                    stars = min(len(filled), 5)
                except Exception:
                    pass

            # Review headline / title
            title = self._safe_text(
                review_el,
                'h2[class*="typography_heading"], '
                'a[class*="review-title"], '
                'h2',
            )

            # Review body text
            body = self._safe_text(
                review_el,
                'p[class*="typography_body"], '
                'p[class*="review-text"], '
                'div[class*="review-content"] p, '
                'p[data-service-review-text-typography], '
                'p',
            )
            # Combine title + body for full review text
            review_text = f"{title}. {body}" if title and body else body or title or ""

            # Review date
            date_text = ""
            date_els = review_el.find_elements(By.CSS_SELECTOR, "time")
            for d in date_els:
                dt = d.get_attribute("datetime") or d.text.strip()
                if dt:
                    date_text = dt
                    break

            # Reviewer location
            location = self._safe_text(
                review_el,
                'span[class*="typography_body-sm"] span, '
                'div[class*="consumer"] span',
            )

            return {
                "name": name,
                "stars": stars,
                "title": title,
                "review_text": review_text.strip(),
                "date": date_text,
                "location": location,
            }

        except Exception as exc:
            logging.warning(f"Error extracting Trustpilot review: {exc}")
            return None

    # ------------------------------------------------------------------ #
    #  Main scraping method – returns a pandas DataFrame                 #
    # ------------------------------------------------------------------ #
    def scrape_trustpilot_reviews(
        self,
        trustpilot_url: str,
        max_reviews: int = 200,
        driver=None,
    ) -> Dict[str, Any]:
        """
        Scrape reviews from a Trustpilot business page.

        Args:
            trustpilot_url: Full Trustpilot URL
                           (e.g. https://www.trustpilot.com/review/www.amazon.com)
            max_reviews:    Maximum number of reviews to scrape.
            driver:         Optional existing WebDriver to reuse (caller is responsible for quitting it).

        Returns:
            Dict with keys:
                business_info  – company metadata
                reviews        – list of review dicts
                dataframe      – pandas DataFrame (Name, Stars, Review Text, Date, Source URL)
        """
        _owned_driver = driver is None
        try:
            if _owned_driver:
                driver = self.setup_browser()

            # Normalize URL
            url = trustpilot_url.strip()
            if not url.startswith("http"):
                url = "https://" + url

            logging.info(f"TrustpilotScraper: navigating to {url}")
            driver.get(url)

            # Wait for review cards to appear instead of sleeping blindly
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR,
                        '[data-service-review-card], article, div[class*="paper_paper"]'))
                )
            except TimeoutException:
                time.sleep(2)

            # Handle cookie / GDPR banners
            self._dismiss_cookie_banner(driver)

            # Extract business-level information
            business_info = self._extract_business_info(driver)
            logging.info(
                f"TrustpilotScraper: business = {business_info.get('name')}, "
                f"rating = {business_info.get('rating')}, "
                f"reviews = {business_info.get('review_count')}"
            )

            # ---- Locate review cards ----
            review_card_selectors = [
                '[data-service-review-card]',
                'div[class*="paper_paper"]',
                'article',
                'section[class*="review"]',
                'div.styles_reviewCard__ccAVN',
                'div[class*="review-card"]',
            ]

            reviews: List[Dict[str, Any]] = []
            scroll_attempts = 0
            max_scroll_attempts = 15
            last_count = 0
            stale_streak = 0

            while len(reviews) < max_reviews and scroll_attempts < max_scroll_attempts:
                # Try each selector until one yields elements
                card_elements = []
                for sel in review_card_selectors:
                    try:
                        card_elements = driver.find_elements(By.CSS_SELECTOR, sel)
                        if card_elements:
                            break
                    except Exception:
                        continue

                if not card_elements:
                    # Maybe reviews are behind a "Show reviews" button
                    self._click_show_reviews(driver)
                    time.sleep(2)
                    scroll_attempts += 1
                    if scroll_attempts > 5:
                        break
                    continue

                # Extract new reviews (avoid duplicates)
                for card in card_elements[len(reviews):]:
                    review_data = self._extract_single_review(card)
                    if review_data and review_data["review_text"]:
                        reviews.append(review_data)
                    if len(reviews) >= max_reviews:
                        break

                if len(reviews) == last_count:
                    stale_streak += 1
                else:
                    stale_streak = 0
                last_count = len(reviews)

                # If we haven't collected enough, scroll / paginate
                if len(reviews) < max_reviews:
                    # Try "Load more" button first
                    clicked = self._click_load_more(driver)
                    if clicked:
                        time.sleep(1)
                    else:
                        # Scroll to bottom of page
                        driver.execute_script(
                            "window.scrollTo(0, document.body.scrollHeight);"
                        )
                        time.sleep(0.8)

                scroll_attempts += 1

                if stale_streak >= 5:
                    logging.info(
                        "TrustpilotScraper: no new reviews after 5 consecutive attempts"
                    )
                    break

            # Build DataFrame compatible with SentimentAnalyzer pipeline
            records = []
            for r in reviews:
                records.append(
                    (
                        r["name"],
                        str(r["stars"]),
                        str(r["stars"]),
                        r["review_text"],
                        url,
                        r["date"],
                    )
                )

            df = pd.DataFrame(
                records,
                columns=[
                    "Name",
                    "Reviews Count",
                    "Stars",
                    "Review Text",
                    "Source URL",
                    "Date",
                ],
            )

            logging.info(
                f"TrustpilotScraper: scraped {len(df)} reviews from {url}"
            )

            return {
                "business_info": business_info,
                "reviews": reviews,
                "dataframe": df,
            }

        except Exception as exc:
            logging.error(f"TrustpilotScraper error: {exc}")
            import traceback
            logging.error(traceback.format_exc())
            return {
                "business_info": {"trustpilot_url": trustpilot_url},
                "reviews": [],
                "dataframe": pd.DataFrame(
                    columns=[
                        "Name",
                        "Reviews Count",
                        "Stars",
                        "Review Text",
                        "Source URL",
                        "Date",
                    ]
                ),
            }
        finally:
            if _owned_driver and driver is not None:
                try:
                    driver.quit()
                except Exception:
                    try:
                        driver.close()
                    except Exception:
                        pass

    # ------------------------------------------------- #
    #  Attempt to dismiss cookie / consent banner        #
    # ------------------------------------------------- #
    def _dismiss_cookie_banner(self, driver):
        selectors = [
            "button#onetrust-accept-btn-handler",
            "button[aria-label*='Accept']",
            "button[id*='accept']",
        ]
        for sel in selectors:
            try:
                btn = WebDriverWait(driver, 1).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                )
                driver.execute_script("arguments[0].click();", btn)
                logging.info(f"Dismissed cookie banner via: {sel}")
                time.sleep(0.5)
                return
            except (TimeoutException, NoSuchElementException):
                continue

    # -------------------------------------------------- #
    #  Click "Load more reviews" / pagination buttons     #
    # -------------------------------------------------- #
    def _click_load_more(self, driver) -> bool:
        # Standard CSS selectors (no jQuery :contains)
        css_selectors = [
            "button[data-pagination-button]",
            "button[class*='load-more']",
            "button[class*='pagination']",
            "a[class*='pagination']",
            "a[rel='next']",
        ]
        for sel in css_selectors:
            try:
                btn = driver.find_element(By.CSS_SELECTOR, sel)
                if btn.is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", btn)
                    logging.info(f"Clicked load-more via: {sel}")
                    return True
            except Exception:
                continue

        # Fallback: find buttons by visible text using XPath
        xpath_texts = ["Load more", "Show more", "See more", "Next page"]
        for text in xpath_texts:
            try:
                btn = driver.find_element(
                    By.XPATH,
                    f"//button[contains(normalize-space(.), '{text}')]"
                )
                if btn.is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", btn)
                    logging.info(f"Clicked load-more via text: {text}")
                    return True
            except Exception:
                continue
        return False

    # -------------------------------------------------- #
    #  Click "Show all reviews" link if present           #
    # -------------------------------------------------- #
    def _click_show_reviews(self, driver) -> bool:
        # Standard CSS selectors only (no jQuery :contains)
        css_selectors = [
            "button[aria-label*='reviews']",
            "button[aria-label*='Reviews']",
        ]
        for sel in css_selectors:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                if el.is_displayed():
                    driver.execute_script("arguments[0].click();", el)
                    logging.info(f"Clicked show-reviews via: {sel}")
                    return True
            except Exception:
                continue

        # Fallback: find links/buttons by visible text using XPath
        xpath_texts = ["See all reviews", "View reviews", "Show reviews"]
        for text in xpath_texts:
            try:
                el = driver.find_element(
                    By.XPATH,
                    f"//a[contains(normalize-space(.), '{text}')] | "
                    f"//button[contains(normalize-space(.), '{text}')]"
                )
                if el.is_displayed():
                    driver.execute_script("arguments[0].click();", el)
                    logging.info(f"Clicked show-reviews via text: {text}")
                    return True
            except Exception:
                continue
        return False

    # ------------------------------------------------------------------ #
    #  Convenience: search Trustpilot for a business name and return URL  #
    # ------------------------------------------------------------------ #
    def search_business_url(self, business_name: str, driver=None) -> Optional[str]:
        """
        Search Trustpilot for a business and return the first result's URL.
        Useful when the user doesn't know the exact Trustpilot slug.

        Args:
            driver: Optional existing WebDriver to reuse (caller is responsible for quitting it).
        """
        _owned_driver = driver is None
        try:
            if _owned_driver:
                driver = self.setup_browser()
            search_url = f"https://www.trustpilot.com/search?query={business_name.replace(' ', '%20')}"
            logging.info(f"TrustpilotScraper: searching for '{business_name}' at {search_url}")
            driver.get(search_url)

            self._dismiss_cookie_banner(driver)

            # Wait for search results to load
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/review/"]'))
                )
            except TimeoutException:
                logging.warning("TrustpilotScraper: timed out waiting for search results to appear")

            # Find first search result link pointing to a review page
            result_selectors = [
                'a[href*="/review/"]',
                'div[class*="search-result"] a',
                'a[class*="business-card"]',
                'a[class*="searchResult"]',
                'article a[href*="/review/"]',
            ]
            for sel in result_selectors:
                try:
                    result_links = driver.find_elements(By.CSS_SELECTOR, sel)
                    for link in result_links:
                        href = link.get_attribute("href") or ""
                        if "/review/" in href:
                            logging.info(f"TrustpilotScraper: found business URL = {href}")
                            return href
                except Exception:
                    continue

            logging.warning(f"TrustpilotScraper: no result found for '{business_name}'")
            return None

        except Exception as exc:
            logging.error(f"TrustpilotScraper search error: {exc}")
            return None
        finally:
            if _owned_driver and driver is not None:
                try:
                    driver.quit()
                except Exception:
                    try:
                        driver.close()
                    except Exception:
                        pass


# ------------------------------------------------------------------ #
#  Standalone: scrape reviews and save to .txt                        #
# ------------------------------------------------------------------ #
if __name__ == "__main__":
    import os
    import sys

    scraper = TrustpilotScraper()

    # --- Configuration ---
    # Option 1: Set a business name to search (e.g. "Netflix", "Nike")
    # Option 2: Set a full Trustpilot URL directly
    # Option 3: Pass name/URL as command-line argument:
    #     python trustpilot_scraper.py Netflix
    #     python trustpilot_scraper.py https://www.trustpilot.com/review/www.amazon.com
    BUSINESS_NAME_OR_URL = "Netflix"
    MAX_REVIEWS = 50
    OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

    # Determine if input is a URL or a business name
    user_input = sys.argv[1] if len(sys.argv) > 1 else BUSINESS_NAME_OR_URL
    trustpilot_url = None

    if user_input.startswith("http") or user_input.startswith("www.trustpilot.com"):
        # Direct URL provided
        trustpilot_url = user_input
        print(f"=== Using direct URL: {trustpilot_url} ===")
    else:
        # Business name provided — search Trustpilot first
        print(f"=== Searching Trustpilot for: {user_input} ===")
        trustpilot_url = scraper.search_business_url(user_input)

        if not trustpilot_url:
            print(f"❌ Could not find '{user_input}' on Trustpilot. Try a different name or provide the URL directly.")
            sys.exit(1)

        print(f"✅ Found: {trustpilot_url}")

    print(f"Max reviews to scrape: {MAX_REVIEWS}")
    print()

    # Scrape reviews
    result = scraper.scrape_trustpilot_reviews(trustpilot_url, max_reviews=MAX_REVIEWS)

    business_info = result["business_info"]
    reviews = result["reviews"]

    # Print summary
    print(f"Business: {business_info.get('name', 'Unknown')}")
    print(f"Rating: {business_info.get('rating', 'N/A')}")
    print(f"Trust Score: {business_info.get('trust_score', 'N/A')}")
    print(f"Total Reviews on Trustpilot: {business_info.get('review_count', 'N/A')}")
    print(f"Reviews scraped: {len(reviews)}")
    print()

    if not reviews:
        print("No reviews found. Exiting.")
    else:
        # Build output filename from business name
        safe_name = re.sub(r'[^\w\s-]', '', business_info.get("name", "business")).strip().replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(OUTPUT_DIR, f"{safe_name}_reviews_{timestamp}.txt")

        # Write reviews to .txt file
        with open(output_file, "w", encoding="utf-8") as f:
            # Header
            f.write(f"{'=' * 80}\n")
            f.write(f"TRUSTPILOT REVIEWS — {business_info.get('name', 'Unknown')}\n")
            f.write(f"{'=' * 80}\n\n")

            f.write(f"URL:            {business_info.get('trustpilot_url', trustpilot_url)}\n")
            f.write(f"Rating:         {business_info.get('rating', 'N/A')} / 5\n")
            f.write(f"Trust Score:    {business_info.get('trust_score', 'N/A')}\n")
            f.write(f"Total Reviews:  {business_info.get('review_count', 'N/A')}\n")
            f.write(f"Verified:       {'Yes' if business_info.get('verified') else 'No'}\n")
            f.write(f"Location:       {business_info.get('location', 'N/A')}\n")

            categories = business_info.get("categories", [])
            if categories:
                f.write(f"Categories:     {', '.join(categories)}\n")

            f.write(f"\nReviews scraped: {len(reviews)}\n")
            f.write(f"Scraped on:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"\n{'-' * 80}\n\n")

            # Each review
            for i, r in enumerate(reviews, 1):
                f.write(f"--- Review #{i} ---\n")
                f.write(f"Name:     {r['name']}\n")
                f.write(f"Stars:    {'★' * r['stars']}{'☆' * (5 - r['stars'])}  ({r['stars']}/5)\n")
                if r.get("title"):
                    f.write(f"Title:    {r['title']}\n")
                f.write(f"Date:     {r.get('date', 'N/A')}\n")
                if r.get("location"):
                    f.write(f"Location: {r['location']}\n")
                f.write(f"\n{r['review_text']}\n\n")

        print(f"✅ Reviews saved to: {output_file}")
        print(f"   File size: {os.path.getsize(output_file):,} bytes")
        print()
        print("Preview (first 3 reviews):")
        for r in reviews[:3]:
            print(f"  - {r['name']}: {'★' * r['stars']} → {r['review_text'][:80]}...")
