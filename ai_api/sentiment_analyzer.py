import time
import logging
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from typing import Dict, List, Optional, Any, Union
import os
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
import asyncio
import aiohttp
import json
import re
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gpt_insights_service import GPTInsightsService
from competitor_search_service import CompetitorSearchService

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class SentimentAnalyzer:

    
    def __init__(self):
        self.gpt_service = GPTInsightsService()
        self.competitor_search = CompetitorSearchService()
        try:
            import torch  
            model_name = 'tabularisai/multilingual-sentiment-analysis'
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSequenceClassification.from_pretrained(model_name)
            # device = 0 if hasattr(torch, 'cuda') and torch.cuda.is_available() else -1
            self.sentiment_pipeline = pipeline(
                task="text-classification",
                model=model,
                tokenizer=tokenizer,
                device=-1
            )
        except Exception as error:
            logging.error(f"Failed to initialize HF sentiment pipeline: {error}")
            self.sentiment_pipeline = None
    
    def setup_browser(self):

        edge_options = Options()

        # Basic stability options
        edge_options.add_argument("--headless=new")
        edge_options.add_argument("--disable-gpu")
        edge_options.add_argument("--no-sandbox")
        edge_options.add_argument("--disable-dev-shm-usage")
        edge_options.add_argument("--disable-software-rasterizer")
        edge_options.add_argument("--window-size=1280,720")
        edge_options.add_argument("--single-process")
        edge_options.add_argument("--no-first-run")
        # Memory and crash prevention options
        edge_options.add_argument("--disable-extensions")
        edge_options.add_argument("--disable-plugins")
        edge_options.add_argument("--disable-background-networking")
        edge_options.add_argument("--disable-sync")
        edge_options.add_argument("--disable-default-apps")
        edge_options.add_argument("--disable-background-timer-throttling")
        edge_options.add_argument("--disable-renderer-backgrounding")
        edge_options.add_argument("--disable-backgrounding-occluded-windows")
        edge_options.add_argument("--disable-features=TranslateUI")
        edge_options.add_argument("--disable-ipc-flooding-protection")
        edge_options.add_argument("--disable-component-extensions-with-background-pages")
        edge_options.add_argument("--disable-component-update")

        edge_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36")

        # Crash recovery
        edge_options.add_argument("--disable-crash-reporter")
        edge_options.add_argument("--disable-logging")
        edge_options.add_argument("--log-level=3")

        edge_options.add_argument("--disable-blink-features=AutomationControlled")
        edge_options.add_argument("--lang=en-US")
        edge_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        edge_options.add_experimental_option("useAutomationExtension", False)

        # Performance preferences
        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2,
                "geolocation": 2,
            },
            "profile.managed_default_content_settings": {
                "images": 2
            }
        }
        edge_options.add_experimental_option("prefs", prefs)

        # Use system chromedriver only - AVOID webdriver_manager version mismatch
        try:
            driver = webdriver.Chrome(options=edge_options)
            driver.set_page_load_timeout(30)
            driver.implicitly_wait(2)
            return driver
        except Exception as e:
            logging.error(f"Chrome setup failed: {e}")
            raise Exception(f"Could not initialize Chrome WebDriver. Ensure Chrome and chromedriver are installed: {e}")

    def expand_review_if_needed(self, browser, review):
        btns = review.find_elements(By.CSS_SELECTOR, 'button.w8nwRe.kyuRq[aria-expanded="false"]')
        if not btns:
            btns = review.find_elements(By.XPATH,
                './/button[contains(@aria-label,"عرض المزيد") or normalize-space(.)="المزيد" or contains(normalize-space(.),"عرض المزيد")]'
            )
        for btn in btns:
            try:
                # wait until it is interactable, then JS-click to avoid intercepted click
                WebDriverWait(browser, 2).until(EC.element_to_be_clickable(btn))
                browser.execute_script("arguments[0].click();", btn)
                WebDriverWait(browser, 2).until(
                    lambda d: btn.get_attribute("aria-expanded") == "true" or not btn.is_displayed()
                )
                break
            except Exception:
                continue

    def _scrape_single_google_reviews(self, url: str, scroll_limit: int = 1000) -> pd.DataFrame:
        print(f"[DEBUG] _scrape_single_google_reviews starting for URL: {url}")
        print(f"[DEBUG] Scroll limit set to: {scroll_limit}")
        browser = None
        try:
            browser = self.setup_browser()
            print(f"[DEBUG] Browser setup complete, navigating to URL...")
            # Ensure Google Maps is loaded in English (Egypt region)
            if "hl=" not in url:
                if "?" in url:
                    url += "&hl=en&gl=eg"
                else:
                    url += "?hl=en&gl=eg"
            print(f"[DEBUG] Final URL with language/region enforced: {url}")
            
            try:
                browser.get(url)
                print(f"[DEBUG] Page loaded, waiting 10 seconds...")
                time.sleep(10)
            except Exception as nav_error:
                logging.error(f"Error navigating to URL: {nav_error}")
                raise

            action = ActionChains(browser)
            
            print(f"[DEBUG] Current page title: {browser.title}")
            print(f"[DEBUG] Current URL after navigation: {browser.current_url}")
            
            # Try to handle cookie consent - make it optional to prevent crashes
            cookie_button_selectors = [
                "[aria-label='Accept all']",
                "[aria-label*='Accept']",
                "[id*='cookie'] button",
                "[class*='cookie'] button",
            ]
            
            cookie_clicked = False
            for selector in cookie_button_selectors:
                try:
                    accept_button = WebDriverWait(browser, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    browser.execute_script("arguments[0].click();", accept_button)
                    print(f"[DEBUG] Clicked cookie consent button using selector: {selector}")
                    cookie_clicked = True
                    time.sleep(2)  # Wait a bit after clicking
                    break
                except Exception as e:
                    continue
            
            if not cookie_clicked:
                print(f"[DEBUG] No cookie consent button found - continuing without clicking")
            
            print(f"[DEBUG] Current URL after cookie handling: {browser.current_url}")
            
            # Try to construct direct reviews URL first (more reliable in headless mode)
            current_url = browser.current_url
            reviews_url = None
            
            # Method 1: Try to construct reviews URL by modifying current URL
            if '/place/' in current_url:
                # Extract place ID or construct reviews URL
                if '?hl=' in current_url:
                    base_url = current_url.split('?')[0]
                    reviews_url = f"{base_url}?hl=en&gl=eg#reviews"
                else:
                    reviews_url = f"{current_url}#reviews"
                
                print(f"[DEBUG] Attempting to navigate directly to reviews URL: {reviews_url}")
                try:
                    browser.get(reviews_url)
                    time.sleep(5)  # Wait for reviews to load
                    print(f"[DEBUG] Navigated to reviews URL")
                except Exception as nav_error:
                    logging.warning(f"Could not navigate to reviews URL: {nav_error}")
                    reviews_url = None
            
            # Method 2: Try to find and click reviews tab (fallback if direct URL doesn't work)
            reviews_tab_clicked = False
            if not reviews_url or 'reviews' not in browser.current_url.lower():
                print(f"[DEBUG] Attempting to find and click reviews tab...")
                
                # Wait longer in headless mode for JavaScript to execute
                print(f"[DEBUG] Waiting for page to fully load (longer wait for headless mode)...")
                time.sleep(8)  # Increased wait for headless mode
                
                # Wait for page to be interactive
                try:
                    WebDriverWait(browser, 15).until(
                        lambda d: d.execute_script("return document.readyState") == "complete"
                    )
                    # Additional wait for JavaScript execution
                    time.sleep(3)
                except Exception:
                    pass
                
                # Optional: Save debug info
                try:
                    browser.save_screenshot('vps_error.png')
                    with open('vps_error.html', 'w', encoding='utf-8') as f:
                        f.write(browser.page_source[:50000])
                    logging.debug("Saved debug screenshot and HTML")
                except Exception as debug_error:
                    logging.warning(f"Could not save debug files: {debug_error}")
                
                # Try multiple strategies to find reviews tab
                tab_selectors = [
                    'button[aria-label*="Reviews"]',
                    'button[aria-label*="مراجعات"]',
                    'button[data-value="Reviews"]',
                    'button[jsaction*="reviews"]',
                    'div[role="tablist"] button:nth-child(2)',
                    'div[role="tablist"] button[aria-selected="false"]',
                ]
                
                reviews_tab = None
                for selector in tab_selectors:
                    try:
                        # Wait for element to be present and visible
                        reviews_tab = WebDriverWait(browser, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        # Check if element is visible (important for headless)
                        if reviews_tab.is_displayed():
                            print(f"[DEBUG] Reviews tab found using selector: {selector}")
                            break
                        else:
                            print(f"[DEBUG] Reviews tab found but not visible with selector: {selector}")
                            reviews_tab = None
                    except Exception as e:
                        print(f"[DEBUG] Reviews tab not found with selector '{selector}': {str(e)}")
                        continue
                
                if reviews_tab:
                    print(f"[DEBUG] Reviews tab found, attempting to click...")
                    try:
                        # Scroll into view first (important for headless)
                        browser.execute_script("arguments[0].scrollIntoView({block: 'center'});", reviews_tab)
                        time.sleep(1)
                        
                        # Try multiple click methods
                        try:
                            # Method 1: JavaScript click (most reliable)
                            browser.execute_script("arguments[0].click();", reviews_tab)
                            print(f"[DEBUG] Clicked reviews tab using JavaScript")
                        except Exception:
                            # Method 2: ActionChains click
                            ActionChains(browser).move_to_element(reviews_tab).click().perform()
                            print(f"[DEBUG] Clicked reviews tab using ActionChains")
                        
                        time.sleep(5)  # Wait for reviews to load after click
                        reviews_tab_clicked = True
                    except Exception as click_error:
                        logging.warning(f"Could not click reviews tab: {click_error}")
                        # Try to navigate to reviews URL as fallback
                        try:
                            if '/place/' in browser.current_url:
                                base_url = browser.current_url.split('?')[0].split('#')[0]
                                reviews_url_fallback = f"{base_url}?hl=en&gl=eg#reviews"
                                browser.get(reviews_url_fallback)
                                time.sleep(5)
                                print(f"[DEBUG] Navigated to reviews URL as fallback")
                        except Exception:
                            pass
                else:
                    print(f"[DEBUG] ERROR: Could not find reviews tab with any selector")
                    print(f"[DEBUG] Available buttons on page:")
                    buttons = browser.find_elements(By.TAG_NAME, "button")
                    for i, btn in enumerate(buttons[:15]): 
                        try:
                            btn_text = btn.text.strip()
                            btn_aria = btn.get_attribute("aria-label")
                            btn_role = btn.get_attribute("role")
                            is_displayed = btn.is_displayed()
                            print(f"[DEBUG] Button {i}: text='{btn_text}', aria-label='{btn_aria}', role='{btn_role}', visible={is_displayed}")
                        except:
                            pass
            
            print(f"[DEBUG] Final URL after reviews navigation: {browser.current_url}")
            
            # Wait for reviews to load - critical in headless mode
            print(f"[DEBUG] Waiting for reviews to load...")
            review_selectors = [
                'div.jftiEf.fontBodyMedium',
                'div[data-review-id]',
                'div[jsaction*="review"]',
                'div.review',
                'div[role="article"]',
                'div.jftiEf',
                'div[data-hveid]'
            ]
            
            # Wait up to 30 seconds for reviews to appear (longer for headless mode)
            reviews = []
            max_wait_time = 30
            start_time = time.time()
            
            while not reviews and (time.time() - start_time) < max_wait_time:
                for selector in review_selectors:
                    try:
                        # Try to find reviews with explicit wait
                        reviews = WebDriverWait(browser, 2).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                        )
                        if reviews:
                            print(f"[DEBUG] Found {len(reviews)} reviews using selector: {selector} after {int(time.time() - start_time)}s")
                            break
                    except TimeoutException:
                        continue
                    except Exception as e:
                        print(f"[DEBUG] Exception with selector '{selector}': {str(e)}")
                        continue
                
                if not reviews:
                    # Wait a bit and retry
                    time.sleep(2)
                    # Try to scroll to trigger lazy loading
                    try:
                        browser.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                        time.sleep(1)
                    except:
                        pass
            
            # If still no reviews, try once more with all selectors
            if not reviews:
                print(f"[DEBUG] No reviews found after waiting, trying final attempt...")
                for selector in review_selectors:
                    try:
                        reviews = browser.find_elements(By.CSS_SELECTOR, selector)
                        if reviews:
                            print(f"[DEBUG] Found {len(reviews)} reviews using selector: {selector} on final attempt")
                            break
                    except Exception as e:
                        print(f"[DEBUG] No reviews found with selector '{selector}': {str(e)}")
                        continue
            
            if not reviews:
                print(f"[DEBUG] ERROR: No reviews found with any selector after {max_wait_time}s")
                print(f"[DEBUG] Current URL: {browser.current_url}")
                print(f"[DEBUG] Page title: {browser.title}")
                print(f"[DEBUG] Checking if we're on reviews page...")
                
                # Check if URL indicates we're on reviews page
                if '#reviews' not in browser.current_url.lower() and 'reviews' not in browser.current_url.lower():
                    print(f"[DEBUG] WARNING: URL does not contain 'reviews' - we may not be on the reviews tab")
                    # Try one more time to construct and navigate to reviews URL
                    try:
                        base_url = browser.current_url.split('?')[0].split('#')[0]
                        final_reviews_url = f"{base_url}?hl=en&gl=eg#reviews"
                        print(f"[DEBUG] Attempting final navigation to: {final_reviews_url}")
                        browser.get(final_reviews_url)
                        time.sleep(10)  # Wait longer for reviews to load
                        
                        # Try to find reviews one more time
                        for selector in review_selectors:
                            try:
                                reviews = browser.find_elements(By.CSS_SELECTOR, selector)
                                if reviews:
                                    print(f"[DEBUG] Found {len(reviews)} reviews after final URL navigation")
                                    break
                            except:
                                continue
                    except Exception as nav_error:
                        logging.error(f"Failed final navigation attempt: {nav_error}")
                
                if not reviews:
                    print(f"[DEBUG] Page source snippet (first 2000 chars):")
                    try:
                        page_source = browser.page_source[:2000]
                        print(page_source)
                    except:
                        pass
                    return pd.DataFrame()
            
            print(f"[DEBUG] Initial reviews found: {len(reviews)}")

            attempts = 0
            max_scroll_attempts = 20
            print(f"[DEBUG] Starting scroll loop with {len(reviews)} initial reviews, limit: {scroll_limit}")
            
            while len(reviews) < scroll_limit:
                try:
                    # Check if browser is still responsive
                    browser.current_url
                except Exception as browser_check_error:
                    logging.error(f"Browser became unresponsive during scrolling: {browser_check_error}")
                    print(f"[DEBUG] Browser unresponsive, stopping scroll and returning current reviews")
                    break
                
                last_review = reviews[-1] if reviews else None
                if last_review:
                    try:
                        print(f"[DEBUG] Scrolling from last review element...")
                        scroll_origin = ScrollOrigin.from_element(last_review)
                        action.scroll_from_origin(scroll_origin, 0, 1000).perform()
                        time.sleep(1.5)  # Reduced wait time
                    except Exception as scroll_error:
                        logging.warning(f"Error during scroll: {scroll_error}")
                        # Try alternative scroll method
                        try:
                            browser.execute_script("window.scrollBy(0, 1000);")
                            time.sleep(1.5)
                        except Exception as js_scroll_error:
                            logging.error(f"Both scroll methods failed: {js_scroll_error}")
                            break

                new_reviews = []
                for selector in review_selectors:
                    try:
                        new_reviews = browser.find_elements(By.CSS_SELECTOR, selector)
                        if new_reviews:
                            print(f"[DEBUG] After scroll, found {len(new_reviews)} reviews using selector: {selector}")
                            break
                    except Exception as e:
                        continue
                
                if len(new_reviews) == len(reviews):
                    attempts += 1
                    print(f"[DEBUG] No new reviews found after scroll, attempt {attempts}/{max_scroll_attempts}")
                    if attempts >= max_scroll_attempts:
                        print(f"[DEBUG] Reached max scroll attempts, breaking")
                        break
                else:
                    attempts = 0
                    print(f"[DEBUG] Found {len(new_reviews)} total reviews (was {len(reviews)})")
                    reviews = new_reviews

            records = []
            print(f"[DEBUG] Processing {len(reviews)} review elements...")
            for i, review in enumerate(reviews):
                try:
                    print(f"[DEBUG] Processing review {i+1}/{len(reviews)}")
                    
                    name = "Unknown"
                    name_selectors = ['div.d4r55', 'div[data-attrid="title"]', 'div.TSUbDb', 'span.X43Kjb']
                    for selector in name_selectors:
                        try:
                            name_elem = review.find_element(By.CSS_SELECTOR, selector)
                            name = name_elem.text.strip()
                            if name:
                                break
                        except:
                            continue
                    
                    reviews_count = "N/A"
                    count_selectors = ['div.RfnDt', 'span.RfnDt', 'div[data-attrid="reviewCount"]']
                    for selector in count_selectors:
                        try:
                            count_elem = review.find_element(By.CSS_SELECTOR, selector)
                            reviews_count = count_elem.text.strip()
                            if reviews_count:
                                break
                        except:
                            continue
                    
                    stars = "No Rating"
                    star_selectors = ['span.kvMYJc', 'div[role="img"]', 'span[aria-label*="star"]']
                    for selector in star_selectors:
                        try:
                            star_elem = review.find_element(By.CSS_SELECTOR, selector)
                            stars = star_elem.get_attribute('aria-label') or star_elem.text
                            if stars:
                                break
                        except:
                            continue
                    
                    self.expand_review_if_needed(browser, review)
                    
                    review_text = "No Review Text"
                    text_selectors = ['span.wiI7pd', 'div[data-attrid="description"]', 'div.MyEned', 'div.review-text']
                    for selector in text_selectors:
                        try:
                            text_elem = review.find_element(By.CSS_SELECTOR, selector)
                            review_text = text_elem.text.strip()
                            if review_text:
                                break
                        except:
                            continue
                    
                    print(f"[DEBUG] Review {i+1} - Name: '{name}', Stars: '{stars}', Text length: {len(review_text)}")
                    
                    if review_text and review_text.strip() and review_text.lower() != "no review text":
                        records.append((name, reviews_count, stars, review_text, url))
                        print(f"[DEBUG] Added review {i+1} to records")
                    else:
                        print(f"[DEBUG] Skipped review {i+1} - no valid text content")
                        
                except Exception as e:
                    print(f"[DEBUG] Error processing review {i+1}: {str(e)}")
                    continue

            print(f"[DEBUG] Scraping completed for {url}. Total reviews scraped: {len(records)}")
            return pd.DataFrame(records, columns=['Name', 'Reviews Count', 'Stars', 'Review Text', 'Source URL'])

        except Exception as error:
            print(f"[DEBUG] Error occurred while scraping {url}: {error}")
            logging.error(f"Error scraping {url}: {error}")
            # Log the full traceback for debugging
            import traceback
            logging.error(f"Full traceback: {traceback.format_exc()}")
            return pd.DataFrame()
        finally:
            # Ensure browser is closed even if crash occurs
            if browser is not None:
                try:
                    browser.quit()
                except Exception as quit_error:
                    logging.warning(f"Error closing browser: {quit_error}")
                    try:
                        browser.close()
                    except Exception:
                        pass

    def scrape_google_reviews(self, urls: Union[str, List[str]], scroll_limit: int = 1000) -> pd.DataFrame:
        url_list: List[str] = [urls] if isinstance(urls, str) else list(urls or [])
        print(f"[DEBUG] scrape_google_reviews called with {len(url_list)} URL(s)")
        print(f"[DEBUG] URLs to process: {url_list}")
        print(f"[DEBUG] Scroll limit: {scroll_limit}")
        
        if not url_list:
            print("[DEBUG] No URLs provided, returning empty DataFrame")
            return pd.DataFrame(columns=['Name', 'Reviews Count', 'Stars', 'Review Text', 'Source URL'])

        dataframes: List[pd.DataFrame] = []
        for i, single_url in enumerate(url_list):
            if single_url and isinstance(single_url, str):
                print(f"[DEBUG] Processing URL {i+1}/{len(url_list)}: {single_url}")
                df_single = self._scrape_single_google_reviews(single_url, scroll_limit=scroll_limit)
                if not df_single.empty:
                    dataframes.append(df_single)

        if not dataframes:
            return pd.DataFrame(columns=['Name', 'Reviews Count', 'Stars', 'Review Text', 'Source URL'])

        return pd.concat(dataframes, ignore_index=True)

    def analyze_sentiment_textblob(self, text: str) -> Dict[str, Any]:

        try:
            if not text or not text.strip():
                return {
                    "sentiment": "Neutral",
                    "polarity": 0.0,
                    "subjectivity": 0.0,
                    "confidence": 0.0
                }

            if self.sentiment_pipeline is None:
                raise RuntimeError("HF sentiment pipeline is not initialized")

            result = self.sentiment_pipeline(text, truncation=True)
            if isinstance(result, list):
                result = result[0]

            label = result.get('label', '')
            score = float(result.get('score', 0.0))

            label_lower = str(label).strip().lower()
            if 'very negative' in label_lower:
                stars_value = 1
            elif label_lower == 'negative':
                stars_value = 2
            elif label_lower == 'neutral':
                stars_value = 3
            elif label_lower == 'positive':
                stars_value = 4
            elif 'very positive' in label_lower:
                stars_value = 5
            else:
                match = re.search(r"(\d)", str(label))
                stars_value = int(match.group(1)) if match else 3

            if stars_value >= 4:
                sentiment_label = "Positive"
            elif stars_value <= 2:
                sentiment_label = "Negative"
            else:
                sentiment_label = "Neutral"

            polarity = (stars_value - 3) / 2.0

            return {
                "sentiment": sentiment_label,
                "polarity": polarity,
                "subjectivity": 0.5,
                "confidence": score
            }
        except Exception as error:
            logging.error(f"Error analyzing sentiment: {error}")
            return {
                "sentiment": "Neutral",
                "polarity": 0.0,
                "subjectivity": 0.0,
                "confidence": 0.0
            }

    def analyze_sentiment_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        results = []
        for text in texts:
            if text and text.strip():
                result = self.analyze_sentiment_textblob(text)
                results.append(result)
            else:
                results.append({
                    "sentiment": "Neutral",
                    "polarity": 0.0,
                    "subjectivity": 0.0,
                    "confidence": 0.0
                })
        return results

    def extract_star_rating(self, stars_text: str) -> int:
        try:
            match = re.search(r'(\d+(?:\.\d+)?)', stars_text)
            if match:
                return int(float(match.group(1)))
            return 3
        except:
            return 3

    def process_reviews_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        
        sentiment_results = self.analyze_sentiment_batch(df['Review Text'].tolist())
        
        df['Sentiment'] = [result['sentiment'] for result in sentiment_results]
        df['Polarity'] = [result['polarity'] for result in sentiment_results]
        df['Subjectivity'] = [result['subjectivity'] for result in sentiment_results]
        df['Confidence'] = [result['confidence'] for result in sentiment_results]
        
        df['Star Rating'] = df['Stars'].apply(self.extract_star_rating)
        
        df['Analysis Date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return df

    def generate_sentiment_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        if df.empty:
            return {}
        
        total_reviews = len(df)
        sentiment_counts = df['Sentiment'].value_counts()
        
        sentiment_percentages = {}
        for sentiment in ['Positive', 'Negative', 'Neutral']:
            count = sentiment_counts.get(sentiment, 0)
            sentiment_percentages[sentiment] = (count / total_reviews) * 100
        
        avg_polarity = df['Polarity'].mean()
        avg_subjectivity = df['Subjectivity'].mean()
        avg_confidence = df['Confidence'].mean()
        avg_star_rating = df['Star Rating'].mean()
        
        return {
            "total_reviews": total_reviews,
            "sentiment_counts": sentiment_counts.to_dict(),
            "sentiment_percentages": sentiment_percentages,
            "average_polarity": avg_polarity,
            "average_subjectivity": avg_subjectivity,
            "average_confidence": avg_confidence,
            "average_star_rating": avg_star_rating,
            "analysis_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    async def generate_ai_insights(self, df: pd.DataFrame, summary: Dict[str, Any]) -> Dict[str, Any]:
        try:
            analysis_data = {
                "summary": summary,
                "sample_reviews": df.head(10)[['Review Text', 'Sentiment', 'Star Rating']].to_dict('records'),
                "sentiment_distribution": summary.get("sentiment_percentages", {}),
                "average_star_rating": summary.get("average_star_rating", 0)
            }
            
            insights = await self.gpt_service.generate_sentiment_insights(analysis_data)
            return insights
            
        except Exception as e:
            logging.error(f"Error generating AI insights: {e}")
            return {
                "error": str(e),
                "insights": "Unable to generate AI insights at this time."
            }

    def create_sentiment_visualizations(self, df: pd.DataFrame, summary: Dict[str, Any]) -> Dict[str, Any]:

        figures = {}
        
        try:
            sentiment_counts = summary.get("sentiment_counts", {})
            if sentiment_counts:
                fig_pie = px.pie(
                    values=list(sentiment_counts.values()),
                    names=list(sentiment_counts.keys()),
                    title="Sentiment Distribution",
                    color_discrete_map={
                        'Positive': '#2E8B57',
                        'Negative': '#DC143C',
                        'Neutral': '#FFA500'
                    }
                )
                figures["sentiment_distribution"] = fig_pie
            
            if not df.empty:
                fig_hist = px.histogram(
                    df,
                    x='Polarity',
                    title="Sentiment Polarity Distribution",
                    nbins=20,
                    color_discrete_sequence=['#1E88E5']
                )
                fig_hist.update_layout(xaxis_title="Polarity Score", yaxis_title="Number of Reviews")
                figures["polarity_distribution"] = fig_hist
            
            if not df.empty:
                fig_scatter = px.scatter(
                    df,
                    x='Star Rating',
                    y='Polarity',
                    color='Sentiment',
                    title="Star Rating vs Sentiment Polarity",
                    color_discrete_map={
                        'Positive': '#2E8B57',
                        'Negative': '#DC143C',
                        'Neutral': '#FFA500'
                    }
                )
                fig_scatter.update_layout(xaxis_title="Star Rating", yaxis_title="Sentiment Polarity")
                figures["rating_vs_sentiment"] = fig_scatter
            
            if not df.empty:
                fig_subjectivity = px.box(
                    df,
                    y='Subjectivity',
                    title="Review Subjectivity Distribution",
                    color_discrete_sequence=['#FF6B6B']
                )
                fig_subjectivity.update_layout(yaxis_title="Subjectivity Score")
                figures["subjectivity_distribution"] = fig_subjectivity
            
        except Exception as e:
            logging.error(f"Error creating visualizations: {e}")
            figures["error"] = str(e)
        
        return figures
    
    async def analyze_competitors_sentiment(self, industry: str, region: str, max_competitors: int = 10, reviews_per_competitor: int = 50) -> Dict[str, Any]:
        try:
            competitors = await self.competitor_search.search_and_get_reviews_urls(
                industry, region, max_competitors
            )
            
            if not competitors:
                return {
                    "error": "No competitors found",
                    "competitors": [],
                    "analysis_results": {}
                }
            
            competitor_results = []
            all_reviews = []
            
            for competitor in competitors:
                try:
                    reviews_url = competitor.get("reviews_url")
                    if reviews_url:
                        print(f"[DEBUG] Full Analysis Mode - Processing competitor: {competitor.get('name', 'Unknown')}")
                        print(f"[DEBUG] Full Analysis Mode - Reviews URL: {reviews_url}")
                        print(f"[DEBUG] Full Analysis Mode - Reviews per competitor limit: {reviews_per_competitor}")
                        df = self.scrape_google_reviews(reviews_url, reviews_per_competitor)
                        
                        if not df.empty:
                            df_processed = self.process_reviews_dataframe(df)
                            
                            summary = self.generate_sentiment_summary(df_processed)
                            
                            try:
                                competitor_ai_input = {
                                    "summary": {
                                        "total_reviews": summary.get("total_reviews", 0),
                                        "sentiment_percentages": summary.get("sentiment_percentages", {}),
                                        "average_polarity": summary.get("average_polarity", 0),
                                        "average_subjectivity": summary.get("average_subjectivity", 0),
                                        "average_star_rating": summary.get("average_star_rating", 0)
                                    },
                                    "sample_reviews": df_processed.head(15)[["Review Text", "Sentiment", "Star Rating"]].to_dict("records"),
                                    "competitor": {
                                        "name": competitor.get("name", "Unknown"),
                                        "rating": competitor.get("rating", 0),
                                        "review_count": competitor.get("review_count", 0)
                                    }
                                }
                                competitor_ai_insights = await self.gpt_service.generate_sentiment_insights(competitor_ai_input)
                            except Exception as _:
                                competitor_ai_insights = {"insights": {"summary": "AI insights unavailable.", "full_analysis": ""}}
                            
                            competitor_result = {
                                "competitor_info": competitor,
                                "reviews_data": df_processed,
                                "sentiment_summary": summary,
                                "total_reviews_analyzed": len(df_processed),
                                "ai_insights": competitor_ai_insights
                            }
                            
                            competitor_results.append(competitor_result)
                            
                            df_processed["competitor_name"] = competitor["name"]
                            df_processed["competitor_rating"] = competitor["rating"]
                            all_reviews.append(df_processed)
                            
                except Exception as e:
                    logging.warning(f"Error analyzing competitor {competitor.get('name', 'Unknown')}: {str(e)}")
                    continue
            
            combined_analysis = {}
            if all_reviews:
                combined_df = pd.concat(all_reviews, ignore_index=True)
                combined_summary = self.generate_sentiment_summary(combined_df)
                combined_analysis = {
                    "combined_summary": combined_summary,
                    "combined_data": combined_df,
                    "total_competitors_analyzed": len(competitor_results),
                    "total_reviews_analyzed": len(combined_df)
                }
            
            ai_insights = await self.generate_competitor_insights(competitor_results, combined_analysis, industry, region)
            
            return {
                "industry": industry,
                "region": region,
                "competitors": competitors,
                "competitor_results": competitor_results,
                "combined_analysis": combined_analysis,
                "ai_insights": ai_insights,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Error in competitor sentiment analysis: {str(e)}")
            return {
                "error": str(e),
                "competitors": [],
                "analysis_results": {}
            }
    
    async def generate_competitor_insights(self, competitor_results: List[Dict[str, Any]], combined_analysis: Dict[str, Any], industry: str, region: str) -> Dict[str, Any]:
        try:
            insights_data = {
                "industry": industry,
                "region": region,
                "competitor_count": len(competitor_results),
                "combined_summary": combined_analysis.get("combined_summary", {}),
                "competitor_summaries": []
            }
            
            for result in competitor_results:
                competitor_info = result["competitor_info"]
                summary = result["sentiment_summary"]
                
                insights_data["competitor_summaries"].append({
                    "name": competitor_info["name"],
                    "rating": competitor_info["rating"],
                    "review_count": competitor_info["review_count"],
                    "sentiment_percentages": summary.get("sentiment_percentages", {}),
                    "average_rating": summary.get("average_star_rating", 0),
                    "total_reviews_analyzed": result["total_reviews_analyzed"]
                })
            
            prompt = self._create_competitor_analysis_prompt(insights_data)
            
            if self.gpt_service.api_key:
                response = await self.gpt_service._call_ai_api(prompt, max_tokens=1500)
                insights = self._parse_competitor_insights(response)
            else:
                insights = self._generate_mock_competitor_insights(insights_data)
            
            return insights
            
        except Exception as e:
            logging.error(f"Error generating competitor insights: {str(e)}")
            return {"error": str(e)}
    
    def _create_competitor_analysis_prompt(self, data: Dict[str, Any]) -> str:
        
        industry = data["industry"]
        region = data["region"]
        competitor_count = data["competitor_count"]
        combined_summary = data["combined_summary"]
        
        competitor_data = ""
        for comp in data["competitor_summaries"]:
            sentiment_pct = comp["sentiment_percentages"]
            competitor_data += f"\n- {comp['name']}: {comp['rating']}/5 stars, {comp['total_reviews_analyzed']} reviews analyzed\n"
            competitor_data += f"  Sentiment: {sentiment_pct.get('Positive', 0):.1f}% positive, {sentiment_pct.get('Negative', 0):.1f}% negative, {sentiment_pct.get('Neutral', 0):.1f}% neutral\n"
        
        return f"""
        Analyze the following competitor sentiment data for the {industry} industry in {region}:

        INDUSTRY OVERVIEW:
        - Industry: {industry}
        - Region: {region}
        - Competitors Analyzed: {competitor_count}
        - Total Reviews Analyzed: {combined_summary.get('total_reviews', 0)}

        OVERALL SENTIMENT DISTRIBUTION:
        - Positive: {combined_summary.get('sentiment_percentages', {}).get('Positive', 0):.1f}%
        - Negative: {combined_summary.get('sentiment_percentages', {}).get('Negative', 0):.1f}%
        - Neutral: {combined_summary.get('sentiment_percentages', {}).get('Neutral', 0):.1f}%
        - Average Star Rating: {combined_summary.get('average_star_rating', 0):.1f}/5

        COMPETITOR BREAKDOWN:
        {competitor_data}

        Please provide:
        1. **Industry Sentiment Health Score** (1-100) for the {industry} industry in {region}
        2. **Key Insights** about customer satisfaction trends in this industry
        3. **Top 3 Competitors** with the best sentiment scores and why they're successful
        4. **Common Pain Points** identified across competitors from negative reviews
        5. **Market Opportunities** based on sentiment gaps
        6. **Strategic Recommendations** for businesses in this industry
        7. **Customer Experience Priorities** that should be addressed
        8. **Competitive Advantages** that successful companies have

        Focus on actionable insights that can help businesses improve their customer experience and competitive positioning in the {industry} industry.
        """
    
    def _parse_competitor_insights(self, response: str) -> Dict[str, Any]:
        return {
            "summary": response[:300] + "..." if len(response) > 300 else response,
            "full_analysis": response,
            "generated_at": datetime.now().isoformat()
        }
    
    def _generate_mock_competitor_insights(self, data: Dict[str, Any]) -> Dict[str, Any]:
        industry = data["industry"]
        region = data["region"]
        
        return {
            "summary": f"Mock analysis: The {industry} industry in {region} shows mixed customer sentiment with opportunities for improvement in customer experience.",
            "full_analysis": f"This is a mock competitor analysis for the {industry} industry in {region}. Connect Google AI API for detailed insights about market sentiment trends and competitive positioning.",
            "generated_at": datetime.now().isoformat()
        }
    
    def create_competitor_visualizations(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        figures = {}
        
        try:
            competitor_results = analysis_results.get("competitor_results", [])
            combined_analysis = analysis_results.get("combined_analysis", {})
            
            if not competitor_results:
                return {"error": "No competitor data available for visualization"}
            
            competitor_names = []
            positive_percentages = []
            negative_percentages = []
            neutral_percentages = []
            
            for result in competitor_results:
                competitor_names.append(result["competitor_info"]["name"])
                sentiment_pct = result["sentiment_summary"].get("sentiment_percentages", {})
                positive_percentages.append(sentiment_pct.get("Positive", 0))
                negative_percentages.append(sentiment_pct.get("Negative", 0))
                neutral_percentages.append(sentiment_pct.get("Neutral", 0))
            
            fig_comparison = go.Figure()
            fig_comparison.add_trace(go.Bar(name='Positive', x=competitor_names, y=positive_percentages, marker_color='#2E8B57'))
            fig_comparison.add_trace(go.Bar(name='Neutral', x=competitor_names, y=neutral_percentages, marker_color='#FFA500'))
            fig_comparison.add_trace(go.Bar(name='Negative', x=competitor_names, y=negative_percentages, marker_color='#DC143C'))
            
            fig_comparison.update_layout(
                title="Competitor Sentiment Comparison",
                xaxis_title="Competitors",
                yaxis_title="Percentage (%)",
                barmode='stack',
                height=500
            )
            figures["competitor_sentiment_comparison"] = fig_comparison
            
            ratings = [result["competitor_info"]["rating"] for result in competitor_results]
            avg_sentiment = [result["sentiment_summary"].get("average_polarity", 0) for result in competitor_results]
            
            fig_scatter = px.scatter(
                x=ratings,
                y=avg_sentiment,
                text=competitor_names,
                title="Competitor Rating vs Average Sentiment",
                labels={'x': 'Google Rating', 'y': 'Average Sentiment Polarity'},
                color=ratings,
                color_continuous_scale='RdYlGn'
            )
            fig_scatter.update_traces(textposition="top center")
            figures["rating_vs_sentiment"] = fig_scatter
            
            if combined_analysis.get("combined_summary"):
                combined_summary = combined_analysis["combined_summary"]
                sentiment_counts = combined_summary.get("sentiment_counts", {})
                
                if sentiment_counts:
                    fig_pie = px.pie(
                        values=list(sentiment_counts.values()),
                        names=list(sentiment_counts.keys()),
                        title=f"Overall {analysis_results.get('industry', 'Industry')} Sentiment Distribution",
                        color_discrete_map={
                            'Positive': '#2E8B57',
                            'Negative': '#DC143C',
                            'Neutral': '#FFA500'
                        }
                    )
                    figures["industry_sentiment_distribution"] = fig_pie
            
            review_counts = [result["total_reviews_analyzed"] for result in competitor_results]
            
            fig_reviews = px.bar(
                x=competitor_names,
                y=review_counts,
                title="Number of Reviews Analyzed per Competitor",
                labels={'x': 'Competitors', 'y': 'Number of Reviews'},
                color=review_counts,
                color_continuous_scale='Blues'
            )
            figures["reviews_count"] = fig_reviews
            
        except Exception as e:
            logging.error(f"Error creating competitor visualizations: {e}")
            figures["error"] = str(e)
        
        return figures
    
    async def analyze_business_sentiment(self, google_maps_url: str, max_reviews: int = 200) -> Dict[str, Any]:
        """
        Analyze sentiment for a single business using Google Maps URL
        
        Args:
            google_maps_url: Google Maps URL of the business to analyze
            max_reviews: Maximum number of reviews to analyze
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            if not google_maps_url or not isinstance(google_maps_url, str):
                return {
                    "error": "Invalid Google Maps URL provided",
                    "business_info": {},
                    "reviews_data": pd.DataFrame(),
                    "sentiment_summary": {},
                    "ai_insights": {}
                }
            
            # Clean and validate the URL
            google_maps_url = google_maps_url.strip()
            if "maps.google.com" not in google_maps_url and "google.com/maps" not in google_maps_url:
                return {
                    "error": "Invalid Google Maps URL. Please provide a valid Google Maps business URL.",
                    "business_info": {},
                    "reviews_data": pd.DataFrame(),
                    "sentiment_summary": {},
                    "ai_insights": {}
                }
            
            logging.info(f"Starting business sentiment analysis for URL: {google_maps_url}")
            
            # Scrape reviews from the Google Maps URL
            df = self.scrape_google_reviews(google_maps_url, scroll_limit=max_reviews)
            
            if df.empty:
                return {
                    "error": "No reviews found for this business. Please ensure the Google Maps URL is correct and the business has reviews.",
                    "business_info": {
                        "google_maps_url": google_maps_url
                    },
                    "reviews_data": df,
                    "sentiment_summary": {},
                    "ai_insights": {}
                }
            
            # Process reviews with sentiment analysis
            df_processed = self.process_reviews_dataframe(df)
            
            # Generate sentiment summary
            summary = self.generate_sentiment_summary(df_processed)
            
            # Extract business information from the URL or reviews
            business_name = "Unknown Business"
            business_rating = summary.get("average_star_rating", 0)
            
            # Try to extract business name from URL first
            import re
            url_lower = google_maps_url.lower()
            
            # Try to extract from /place/ in URL (common Google Maps format)
            place_match = re.search(r'/place/([^/@]+)', google_maps_url)
            if place_match:
                business_name = place_match.group(1).replace('+', ' ').replace('%20', ' ')
                # Decode URL encoding
                from urllib.parse import unquote
                business_name = unquote(business_name)
                # Clean up - remove parentheses and extra info
                business_name = re.sub(r'\s*\([^)]*\)\s*', '', business_name).strip()
            
            # If still default, try extracting from URL parameters or path
            if business_name == "Unknown Business":
                # Try extracting from data parameter or other parts
                name_match = re.search(r'([A-Za-z0-9\s]+(?:Academy|Company|Business|Shop|Store|Restaurant|Hotel|Center|Centre|Inc|LLC))', google_maps_url, re.IGNORECASE)
                if name_match:
                    business_name = name_match.group(1).strip()
            
            # Final fallback: use a shortened version of URL
            if business_name == "Unknown Business":
                # Try to get a readable name from the URL path
                path_match = re.search(r'/([^/?]+)', google_maps_url.split('/place/')[-1] if '/place/' in google_maps_url else google_maps_url)
                if path_match:
                    potential_name = path_match.group(1).replace('+', ' ').replace('%20', ' ')
                    if len(potential_name) > 3 and len(potential_name) < 100:
                        business_name = potential_name[:50]  # Limit length
            
            # If still no good name, use a generic one
            if business_name == "Unknown Business" or len(business_name) < 3:
                business_name = "Your Business"
            
            # Generate AI insights for the business
            try:
                business_ai_input = {
                    "summary": {
                        "total_reviews": summary.get("total_reviews", 0),
                        "sentiment_percentages": summary.get("sentiment_percentages", {}),
                        "average_polarity": summary.get("average_polarity", 0),
                        "average_subjectivity": summary.get("average_subjectivity", 0),
                        "average_star_rating": summary.get("average_star_rating", 0)
                    },
                    "sample_reviews": df_processed.head(20)[["Review Text", "Sentiment", "Star Rating"]].to_dict("records"),
                    "business": {
                        "name": business_name,
                        "rating": business_rating,
                        "google_maps_url": google_maps_url
                    }
                }
                ai_insights = await self.gpt_service.generate_sentiment_insights(business_ai_input)
            except Exception as e:
                logging.warning(f"Error generating AI insights: {str(e)}")
                ai_insights = {
                    "insights": {
                        "summary": "AI insights unavailable at this time.",
                        "full_analysis": "Unable to generate AI insights. Please try again later."
                    }
                }
            
            return {
                "business_info": {
                    "name": business_name,
                    "google_maps_url": google_maps_url,
                    "rating": business_rating,
                    "total_reviews": summary.get("total_reviews", 0)
                },
                "reviews_data": df_processed,
                "sentiment_summary": summary,
                "total_reviews_analyzed": len(df_processed),
                "ai_insights": ai_insights,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Error in business sentiment analysis: {str(e)}")
            return {
                "error": f"Error analyzing business sentiment: {str(e)}",
                "business_info": {
                    "google_maps_url": google_maps_url if google_maps_url else ""
                },
                "reviews_data": pd.DataFrame(),
                "sentiment_summary": {},
                "ai_insights": {}
            }