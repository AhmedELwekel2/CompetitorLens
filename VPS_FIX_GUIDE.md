# VPS Scraping Fix Guide

## Problem Identified
Your VPS scraping stopped due to three cascading issues:

### 1. **Chrome Version Mismatch** (CRITICAL)
- VPS has: Chrome 148.0.7778.215
- webdriver_manager was downloading: ChromeDriver 149.0.7827.54
- **Error**: "This version of ChromeDriver only supports Chrome version 149"
- **Impact**: All Selenium instances were failing to initialize

### 2. **Resource Exhaustion**
- System load: 10.63 (extremely high)
- Running tasks: 411 with 843 threads
- Memory pressure causing Chrome timeouts (57-58+ seconds)
- Multiple concurrent Chrome instances consuming all RAM
- Worker process killed by system (SIGTERM)

### 3. **Concurrent Browser Instances**
- Main Google Maps browser + up to 3 parallel Trustpilot browsers = 4+ instances
- Each Chrome instance uses 200-300MB+ with large pages
- On a 4GB VPS: 4 instances × 250MB = 1GB just for browsers

## Changes Made

### ✅ Fixed Files

#### 1. `ai_api/trustpilot_scraper.py`
- **Removed** webdriver_manager dependency (source of version mismatch)
- **Uses** system Chrome/Chromium only
- **Reduced** window size: 1920×1080 → 1280×720 (saves memory)
- **Added** `--single-process` flag (reduces memory footprint)
- **Reduced** page load timeout: 60s → 30s (fails faster on stuck pages)
- **Reduced** implicit wait: 3s → 2s
- **Disabled** image loading (profile.managed_default_content_settings: images: 2)

#### 2. `ai_api/competitor_search_service.py`
- **Removed** webdriver_manager dependency
- **Uses** system Chrome only
- **Changed** Trustpilot processing from parallel (3 workers) → sequential
- **Added** `gc.collect()` calls after heavy operations
- **Same window size and timeout reductions**

#### 3. `ai_api/sentiment_analyzer.py`
- **Removed** webdriver_manager dependency
- **Uses** system Chrome only
- **Same optimizations as above**

## What You Need to Do on the VPS

### Step 1: Update Chrome
Your VPS has Chrome 148, but the system chromedriver likely doesn't exist. You need to:

```bash
# Check if Chrome is installed
which google-chrome
which chromium
which chromium-browser

# If Chrome is missing, install it
sudo apt-get update
sudo apt-get install -y chromium-browser
# OR
sudo apt-get install -y google-chrome-stable
```

### Step 2: Ensure chromedriver Matches Your Chrome Version
The system Chrome version must match the system chromedriver.

```bash
# Check Chrome version
google-chrome --version
chromium-browser --version

# Check chromedriver version
chromedriver --version

# They MUST match. If chromedriver doesn't exist:
# Install chromedriver for your Chrome version
# Option 1: Download from https://googlechromelabs.github.io/chrome-for-testing/
# Option 2: Use your package manager
sudo apt-get install -y chromium-driver
```

### Step 3: Verify System Has Enough Resources
Before running, ensure your VPS has:
- **At least 2GB free RAM** (each Chrome instance: 250MB+)
- **Swap space enabled** (helps when memory is tight)

```bash
# Check memory
free -h

# Check swap
swapon --show

# Enable swap if needed (create 2GB swap file)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Step 4: Deploy Updated Code
Pull the changes and restart your application:

```bash
cd /path/to/competitorlens88
git pull origin main
# Or manually copy the updated files from:
# - ai_api/trustpilot_scraper.py
# - ai_api/competitor_search_service.py
# - ai_api/sentiment_analyzer.py
```

### Step 5: Test Before Running Full Scrape
Test with a small query first:

```bash
# Test sentiment analyzer (Google Maps scraping)
python -c "
from ai_api.sentiment_analyzer import SentimentAnalyzer
analyzer = SentimentAnalyzer()
result = analyzer.analyze_market(
    industry='restaurants',
    region='Cairo, Egypt',
    max_competitors=2  # Start small!
)
print('Success!')
"

# If this works, expand to your normal query
```

## Why These Changes Work

### Before
```
1. Google Maps browser (open)
   ↓
2. Process competitor 1
   ├─ Trustpilot browser 1
   ├─ Trustpilot browser 2
   └─ Trustpilot browser 3 (all in parallel)
   ↓
3. All 4+ browsers consuming memory simultaneously
4. Memory exhausted → Chrome timeouts → cascading failures
```

### After
```
1. Google Maps browser (open)
   ↓
2. Process competitor 1 → Trustpilot browser (open/close)
   ↓ [memory freed]
3. Process competitor 2 → Trustpilot browser (open/close)
   ↓ [memory freed]
4. Process competitor 3 → Trustpilot browser (open/close)
   ↓ [memory freed]
5. Only 1-2 browsers in memory at a time
6. Slower, but stable and no crashes
```

## Expected Results

### Performance
- **Slower**: Sequential vs. parallel (trade-off for stability)
  - 5 competitors: ~30 minutes → ~45 minutes
- **Stable**: No timeouts, no crashes
- **Reliable**: Completes scraping without memory exhaustion

### Logs Should Show
- ✅ "Chrome WebDriver initialized" (system Chrome found)
- ✅ No "webdriver_manager" errors
- ✅ No "DevToolsActivePort" errors
- ✅ No "Timed out receiving message from renderer" errors

## Monitoring on VPS

While scraping is running, monitor resources:

```bash
# Watch in real-time
watch -n 2 'free -h && echo "---" && ps aux | grep chrome | wc -l'

# Should show:
# - Free memory staying above 500MB
# - Number of chrome processes: 1-2 (not 4+)
```

## If Still Having Issues

### Issue: "Chrome driver not found"
```bash
# The code now expects system Chrome/chromedriver
# Verify they exist:
ls -la /usr/bin/chromium*
ls -la /usr/bin/google-chrome*
which chromedriver
```

### Issue: "Still running out of memory"
1. Reduce `max_reviews_per_competitor` (default: 100 → try 30)
2. Reduce `max_competitors` (default: 5 → try 2)
3. Increase wait times in sleep() calls (prevents hammering VPS)

### Issue: "Scraping is too slow"
This is expected with sequential processing. If you need faster scraping, you'll need a larger VPS with more RAM.

## Future Improvements

If you want better performance without crashes:
1. **Upgrade VPS**: 8GB+ RAM allows parallel browsers again
2. **Use headless APIs**: Replace Selenium with Playwright/Puppeteer (lighter memory)
3. **Distributed scraping**: Run multiple small VPS instances instead of one large task
4. **Caching**: Store results to avoid re-scraping same companies

---

**Key Takeaway**: The code now uses only the system's Chrome/Chromium (no version mismatch) and processes Trustpilot sequentially (no memory exhaustion). If your VPS has Chrome 148 installed with matching chromedriver, this should work.
