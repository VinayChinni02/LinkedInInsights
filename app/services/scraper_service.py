"""
LinkedIn scraper service using Selenium/Playwright.
"""
import asyncio
import re
from typing import Optional, List, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, Page as PlaywrightPage
from config import settings
from app.models.page import Page
from app.models.post import Post, Comment
from app.models.user import SocialMediaUser


class LinkedInScraperService:
    """Service for scraping LinkedIn company page data."""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.timeout = settings.scraper_timeout * 1000  # Convert to milliseconds
        self.is_authenticated = False
        self.context = None
    
    async def initialize(self):
        """Initialize browser."""
        import sys
        # Skip Playwright on Python 3.13 Windows due to asyncio subprocess issues
        if sys.platform == "win32" and sys.version_info >= (3, 13):
            print("[WARNING] Playwright not available on Python 3.13 Windows. Scraping will not be available.")
            self.browser = None
            return
        
        try:
            playwright = await async_playwright().start()
            # Check if we should run in headless mode
            # Allow non-headless for first-time verification
            import os
            headless_mode = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"
            
            # Launch browser with stealth mode to avoid detection
            # This helps prevent LinkedIn from logging you out when using cookies
            stealth_args = [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials',
                '--disable-infobars',
                '--disable-blink-features=AutomationControlled',
                '--exclude-switches=enable-automation',
                '--disable-extensions-except',
                '--disable-plugins-discovery',
                '--start-maximized'
            ]
            
            self.browser = await playwright.chromium.launch(
                headless=headless_mode,
                args=stealth_args
            )
            
            # Try to load saved session state if it exists
            import os
            import time
            session_file = "linkedin_auth.json"
            storage_state = None
            if os.path.exists(session_file):
                try:
                    import json
                    with open(session_file, 'r') as f:
                        data = json.load(f)
                    
                    # Handle both array format and dict format
                    if isinstance(data, list):
                        # Array format - convert to Playwright format
                        print("[INFO] Converting cookie array to Playwright format...")
                        storage_state = {
                            "cookies": [
                                {
                                    "name": c.get("name", ""),
                                    "value": c.get("value", ""),
                                    "domain": c.get("domain", ".linkedin.com"),
                                    "path": c.get("path", "/"),
                                    "expires": int(c.get("expirationDate", -1)) if c.get("expirationDate") else (c.get("expires", -1) if "expires" in c else -1),
                                    "httpOnly": c.get("httpOnly", False),
                                    "secure": c.get("secure", True),
                                    "sameSite": "None" if c.get("sameSite") in ["no_restriction", "None", "Lax", None] else "Lax"
                                }
                                for c in data if "linkedin.com" in c.get("domain", "")
                            ],
                            "origins": []
                        }
                    elif isinstance(data, dict) and "cookies" in data:
                        # Already in Playwright format
                        storage_state = data
                    else:
                        print("[WARNING] Invalid cookie file format")
                        storage_state = None
                    
                    if storage_state:
                        # Check if cookies are expired and if li_at exists
                        current_time = int(time.time())
                        cookies_valid = False
                        li_at_found = False
                        
                        cookies_list = storage_state.get("cookies", [])
                        print(f"[DEBUG] Checking {len(cookies_list)} cookies for li_at...")
                        
                        for cookie in cookies_list:
                            cookie_name = cookie.get("name", "")
                            if cookie_name == "li_at":
                                li_at_found = True
                                print(f"[DEBUG] Found li_at cookie")
                            expires = cookie.get("expires", -1)
                            # -1 means session cookie (doesn't expire until browser closes)
                            # If expires > 0, check if it's in the future
                            if expires > 0:
                                if expires < current_time:
                                    # Cookie expired
                                    cookies_valid = False
                                    break
                                else:
                                    cookies_valid = True
                            elif expires == -1:
                                # Session cookie, assume valid
                                cookies_valid = True
                        
                        if not li_at_found:
                            print("[WARNING] li_at cookie not found in session file. Authentication may fail.")
                            print("[INFO] Make sure you exported all cookies including li_at from your browser.")
                            # Don't set storage_state to None - still try to use cookies
                        elif not cookies_valid:
                            print("[WARNING] Some cookies in session file are expired. Will attempt to re-authenticate.")
                            # Keep storage_state but mark for re-auth
                        else:
                            print("[INFO] Found saved LinkedIn session, validating cookies...")
                except Exception as e:
                    print(f"[WARNING] Error loading session file: {e}")
                    storage_state = None
            
            # Create context with storage state for session persistence
            # Use realistic browser fingerprint to avoid detection
            context_options = {
                'viewport': {'width': 1920, 'height': 1080},
                'user_agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                'locale': 'en-US',
                'timezone_id': 'America/New_York',
                'permissions': ['geolocation'],
                'extra_http_headers': {
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Cache-Control': 'max-age=0',
                }
            }
            if storage_state:
                context_options['storage_state'] = storage_state
            
            self.context = await self.browser.new_context(**context_options)
            
            # Add JavaScript to hide webdriver property and other automation indicators
            # This helps prevent LinkedIn from detecting Playwright
            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Override plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                // Override languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                
                // Override permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // Chrome runtime
                window.chrome = {
                    runtime: {}
                };
            """)
            
            # Use cookies if they exist - validation may fail due to LinkedIn blocking, but cookies might still work
            if storage_state:
                # Check if li_at cookie exists (most important)
                li_at_exists = any(c.get("name") == "li_at" for c in storage_state.get("cookies", []))
                
                if li_at_exists:
                    print("[INFO] Found li_at cookie. Will attempt to use cookies (validation may be blocked by LinkedIn).")
                    # Don't validate immediately - LinkedIn may block validation but cookies might work for actual scraping
                    # Set as authenticated tentatively - will verify when actually scraping
                    self.is_authenticated = True
                    print("[INFO] Cookies loaded. Authentication will be verified during first scrape.")
                else:
                    print("[WARNING] li_at cookie not found. Cookies may not work.")
                    # Attempt login if credentials are provided
                    if settings.linkedin_email and settings.linkedin_password:
                        login_success = await self._login()
                        if login_success:
                            self.is_authenticated = True
                        else:
                            print("[WARNING] Login failed. Will try to scrape with public data.")
                    else:
                        print("[INFO] LinkedIn credentials not provided. Will try to scrape with public data.")
            else:
                # No cookies, attempt login if credentials are provided
                if settings.linkedin_email and settings.linkedin_password:
                    await self._login()
                else:
                    print("[INFO] LinkedIn credentials not provided. Scraping will work with public data only.")
                    print("[INFO] For full data access (description, followers, posts, people), add LINKEDIN_EMAIL and LINKEDIN_PASSWORD to .env")
            
            print("[OK] Playwright browser initialized")
        except (NotImplementedError, Exception) as e:
            # Catch NotImplementedError specifically (Python 3.13 Windows issue)
            print(f"[WARNING] Playwright initialization failed: {type(e).__name__}: {str(e)}. Scraping will not be available.")
            import traceback
            print(f"[DEBUG] Full error: {traceback.format_exc()}")
            self.browser = None
            # Don't re-raise - allow app to continue
    
    async def _validate_cookies(self) -> bool:
        """Validate if the saved cookies are still valid by checking if we can access a protected page."""
        if not self.context:
            return False
        
        try:
            page = await self.context.new_page()
            # Try to access feed page (requires authentication) with shorter timeout
            await page.goto("https://www.linkedin.com/feed", wait_until="domcontentloaded", timeout=8000)
            await page.wait_for_timeout(2000)
            
            current_url = page.url
            page_title = await page.title()
            
            # Check if we're redirected to login/authwall
            if ("login" in current_url.lower() or 
                "authwall" in current_url.lower() or 
                "challenge" in current_url.lower() or
                "Sign Up" in page_title or
                "Join LinkedIn" in page_title):
                await page.close()
                return False
            
            # If we're on feed or profile, cookies are valid
            if "feed" in current_url.lower() or "linkedin.com/in/" in current_url.lower():
                await page.close()
                return True
            
            # Unknown state, assume valid if not on login page
            is_valid = "login" not in current_url.lower()
            await page.close()
            return is_valid
            
        except Exception as e:
            print(f"[DEBUG] Cookie validation error: {e}")
            return False
    
    async def _login(self):
        """Login to LinkedIn if credentials are provided."""
        if not settings.linkedin_email or not settings.linkedin_password:
            return False
        
        if not self.context:
            return False
        
        try:
            page = await self.context.new_page()
            print("[INFO] Attempting LinkedIn login...")
            
            # Increase timeout for login page - wait for network idle to ensure page is fully loaded
            await page.goto("https://www.linkedin.com/login", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(5000)  # Extra wait for dynamic content
            
            # Check if we're already logged in (redirected away from login page)
            current_url = page.url
            page_title = await page.title()
            print(f"[DEBUG] Login page loaded. URL: {current_url}, Title: {page_title}")
            
            if "feed" in current_url.lower() or "linkedin.com/in/" in current_url.lower() or "linkedin.com/feed" in current_url.lower():
                print("[OK] Already logged in to LinkedIn")
                self.is_authenticated = True
                await self.context.storage_state(path="linkedin_auth.json")
                await page.close()
                return True
            
            # Check if we're on a challenge/verification page
            if "challenge" in current_url.lower() or "checkpoint" in current_url.lower() or "verify" in current_url.lower() or "authwall" in current_url.lower():
                print("[INFO] LinkedIn requires verification or showing authwall.")
                print("[INFO] This might be due to bot detection. Cookies may need to be refreshed.")
                print("[INFO] For Docker/headless mode, please export fresh cookies from your browser.")
                await page.close()
                return False
            
            # Wait for login form to appear - try waiting for any input field
            # LinkedIn may have different selectors or may be blocking
            login_form_found = False
            try:
                # Try multiple approaches to find login form
                selectors_to_try = [
                    'input[name="session_key"]',
                    'input[id="username"]',
                    'input[type="text"]',
                    'input[type="email"]',
                    'input[autocomplete="username"]',
                    '#username',
                    'input[placeholder*="Email"]',
                    'input[placeholder*="email"]',
                    'form',
                    'input'
                ]
                
                for selector in selectors_to_try:
                    try:
                        await page.wait_for_selector(selector, timeout=3000)
                        login_form_found = True
                        print(f"[DEBUG] Found login form element: {selector}")
                        break
                    except:
                        continue
                
                if not login_form_found:
                    # Check page content to understand what LinkedIn is showing
                    page_content = await page.content()
                    page_text = await page.evaluate("document.body.innerText")
                    
                    print("[WARNING] Login form not found. Checking page content...")
                    print(f"[DEBUG] Page text sample: {page_text[:200]}")
                    
                    if "bot" in page_content.lower() or "automated" in page_content.lower() or "unusual activity" in page_content.lower():
                        print("[WARNING] LinkedIn is blocking automated access.")
                        print("[INFO] LinkedIn detects Playwright/automation. Try using fresh cookies instead.")
                    elif "challenge" in current_url.lower() or "checkpoint" in current_url.lower():
                        print("[WARNING] LinkedIn requires additional verification (challenge/checkpoint).")
                        print("[INFO] This usually requires manual intervention or fresh cookies.")
                    else:
                        print("[WARNING] Could not find login form. LinkedIn may have changed their page structure.")
                        print("[INFO] Try exporting fresh cookies from your browser instead.")
                    
                    await page.close()
                    return False
            except Exception as e:
                print(f"[WARNING] Error waiting for login form: {e}")
                await page.close()
                return False
            
            # Try multiple selectors for email input (LinkedIn may have changed)
            email_input = None
            email_selectors = [
                'input[name="session_key"]',
                'input[id="username"]',
                'input[type="text"]',
                'input[type="email"]',
                'input[autocomplete="username"]',
                'input[placeholder*="Email"]',
                'input[placeholder*="email"]'
            ]
            
            for selector in email_selectors:
                try:
                    email_input = page.locator(selector).first
                    # Check if element exists and is visible
                    count = await email_input.count()
                    if count > 0:
                        is_visible = await email_input.is_visible(timeout=5000)
                        if is_visible:
                            print(f"[DEBUG] Found email input with selector: {selector}")
                            break
                except Exception as e:
                    continue
            
            if not email_input:
                print("[WARNING] Could not find email input field. LinkedIn may be blocking automated access.")
                print(f"[DEBUG] Current URL: {current_url}, Page title: {page_title}")
                print("[INFO] For Docker/headless mode, LinkedIn often blocks automated login.")
                print("[INFO] Solution: Export fresh cookies from your browser and update linkedin_auth.json")
                print("[INFO] See README or HYBRID_MODEL_SETUP.md for instructions on exporting cookies.")
                # Try to get page screenshot for debugging (if not headless)
                try:
                    screenshot_path = "/tmp/linkedin_login_debug.png"
                    await page.screenshot(path=screenshot_path, full_page=True)
                    print(f"[DEBUG] Screenshot saved to {screenshot_path} for debugging")
                except:
                    pass
                await page.close()
                return False
            
            await email_input.fill(settings.linkedin_email, timeout=10000)
            await page.wait_for_timeout(1000)
            
            # Try multiple selectors for password input
            password_input = None
            password_selectors = [
                'input[name="session_password"]',
                'input[id="password"]',
                'input[type="password"]',
                'input[autocomplete="current-password"]'
            ]
            
            for selector in password_selectors:
                try:
                    password_input = page.locator(selector).first
                    if await password_input.is_visible(timeout=5000):
                        break
                except:
                    continue
            
            if not password_input:
                print("[WARNING] Could not find password input field.")
                await page.close()
                return False
            
            await password_input.fill(settings.linkedin_password, timeout=10000)
            await page.wait_for_timeout(1000)
            
            # Try multiple selectors for login button
            login_button = None
            button_selectors = [
                'button[type="submit"]',
                'button:has-text("Sign in")',
                'button:has-text("Log in")',
                'input[type="submit"]',
                'button.btn-primary'
            ]
            
            for selector in button_selectors:
                try:
                    login_button = page.locator(selector).first
                    if await login_button.is_visible(timeout=5000):
                        break
                except:
                    continue
            
            if not login_button:
                print("[WARNING] Could not find login button.")
                await page.close()
                return False
            
            await login_button.click(timeout=10000)
            
            # Wait for navigation
            await page.wait_for_timeout(5000)
            
            current_url = page.url
            
            # Check if 2FA/email verification is required
            if "challenge" in current_url.lower() or "checkpoint" in current_url.lower() or "verify" in current_url.lower():
                print("[INFO] LinkedIn requires email verification/2FA")
                print("[INFO] Please check your email for the verification code")
                print("[INFO] Waiting up to 2 minutes for manual verification...")
                
                # Wait for user to complete verification manually
                # Check every 3 seconds for up to 2 minutes
                max_wait_time = 120  # 2 minutes
                check_interval = 3  # Check every 3 seconds
                elapsed_time = 0
                
                while elapsed_time < max_wait_time:
                    await page.wait_for_timeout(check_interval * 1000)
                    elapsed_time += check_interval
                    
                    # Check current URL to see if verification completed
                    current_url = page.url
                    page_title = await page.title()
                    
                    # If we're redirected to feed or profile, login succeeded
                    if "feed" in current_url.lower() or "linkedin.com/in/" in current_url.lower() or "linkedin.com/feed" in current_url.lower():
                        self.is_authenticated = True
                        print("[OK] LinkedIn login successful after verification!")
                        # Save authentication state
                        await self.context.storage_state(path="linkedin_auth.json")
                        await page.close()
                        return True
                    
                    # Check if still on challenge/verification page
                    if "challenge" not in current_url.lower() and "checkpoint" not in current_url.lower() and "verify" not in current_url.lower():
                        # Might have completed, check if we're logged in
                        if "login" not in current_url.lower():
                            self.is_authenticated = True
                            print("[OK] LinkedIn login successful!")
                            await self.context.storage_state(path="linkedin_auth.json")
                            await page.close()
                            return True
                    
                    # Print progress every 15 seconds
                    if elapsed_time % 15 == 0:
                        print(f"[INFO] Still waiting for verification... ({elapsed_time}s/{max_wait_time}s)")
                
                # Timeout - verification not completed
                print("[WARNING] Email verification timeout. Login not completed.")
                print("[INFO] You can try again, or use saved session cookies (see README)")
                self.is_authenticated = False
                await page.close()
                return False
            
            # Check if login was successful (no 2FA required)
            elif "feed" in current_url.lower() or "linkedin.com/in/" in current_url.lower():
                self.is_authenticated = True
                print("[OK] LinkedIn login successful")
                # Save authentication state
                await self.context.storage_state(path="linkedin_auth.json")
                await page.close()
                return True
            elif "login" in current_url.lower():
                print("[WARNING] Still on login page. Login may have failed.")
                self.is_authenticated = False
                await page.close()
                return False
            else:
                # Unknown state, assume success
                self.is_authenticated = True
                print("[OK] LinkedIn login successful")
                await self.context.storage_state(path="linkedin_auth.json")
                await page.close()
                return True
            
        except Exception as e:
            print(f"[WARNING] LinkedIn login failed: {e}")
            import traceback
            print(f"[DEBUG] Login error details: {traceback.format_exc()}")
            self.is_authenticated = False
            return False
    
    async def close(self):
        """Close browser."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
    
    async def scrape_page_details(self, page_id: str) -> Optional[Dict[str, Any]]:
        """
        Scrape basic details of a LinkedIn company page.
        
        Args:
            page_id: LinkedIn page ID (e.g., 'deepsolv')
            
        Returns:
            Dictionary containing page details
        """
        if not self.browser:
            await self.initialize()
        
        url = f"https://www.linkedin.com/company/{page_id}/"
        
        # Use authenticated context if available
        if self.context:
            page = await self.context.new_page()
        else:
            if not self.browser:
                await self.initialize()
            page = await self.browser.new_page()
        
        try:
            # Set additional headers to appear more like a real browser
            await page.set_extra_http_headers({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            })
            
            # Try to access the page
            await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
            await page.wait_for_timeout(3000)
            
            # Check if we're redirected to login or join page
            current_url = page.url
            page_title = await page.title()
            
            # Detect if we hit a login/join page
            if ("login" in current_url.lower() or 
                "challenge" in current_url.lower() or 
                "join" in current_url.lower() or
                "authwall" in current_url.lower() or
                "Join LinkedIn" in page_title or
                "Sign Up" in page_title):
                print(f"[WARNING] LinkedIn redirected to login/join page for {page_id}.")
                print(f"[INFO] Current URL: {current_url}, Title: {page_title}")
                
                # Update authentication status - cookies didn't work
                if self.is_authenticated:
                    print("[INFO] Cookies were loaded but appear invalid. Updating authentication status.")
                    self.is_authenticated = False
                
                # Try alternative approach - use mobile/user-agent variation
                if not settings.linkedin_email or not settings.linkedin_password:
                    print(f"[INFO] Trying alternative extraction methods for public data...")
                    # Try with different user agent
                    await page.set_extra_http_headers({
                        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
                    })
                    await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
                    await page.wait_for_timeout(3000)
                else:
                    # Try to login if credentials available
                    login_success = await self._login()
                    if login_success:
                        self.is_authenticated = True
                        await page.goto(url, wait_until="networkidle", timeout=self.timeout)
                        await page.wait_for_timeout(3000)
                    else:
                        print("[WARNING] Login failed. Will try to scrape with public data.")
            else:
                # Successfully accessed the page - cookies are working!
                if not self.is_authenticated:
                    print(f"[OK] Successfully accessed {page_id} page. Cookies are working!")
                    self.is_authenticated = True
            
            # Wait for content to load
            await page.wait_for_timeout(2000)
            
            # Scroll to load more content
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(1000)
            
            # Try to extract data from page context/JavaScript BEFORE getting HTML
            page_data_from_js = await self._extract_from_javascript(page)
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Also try to get data from network responses
            network_data = {}
            try:
                # Wait for any API calls to complete
                await page.wait_for_timeout(2000)
                # Try to intercept network responses for data
                network_data = await self._extract_from_network_responses(page)
            except Exception as e:
                print(f"[DEBUG] Network extraction error: {e}")
            
            # Extract page details with improved selectors - combine multiple sources
            extracted_name = self._extract_name(soup, content) or page_data_from_js.get("name") or network_data.get("name")
            
            # Final check: if we got generic LinkedIn text, try one more time with different approach
            if not extracted_name or 'join linkedin' in extracted_name.lower() or 'sign up' in extracted_name.lower():
                print(f"[WARNING] Got generic LinkedIn page for {page_id}. LinkedIn requires authentication for company data.")
                print(f"[INFO] To get all assignment details, add LINKEDIN_EMAIL and LINKEDIN_PASSWORD to .env file")
            
            # Extract description first (needed for follower extraction fallback)
            extracted_description = self._extract_description(soup, content) or page_data_from_js.get("description") or network_data.get("description")
            
            # Extract followers - try multiple sources, including from description
            extracted_followers = self._extract_followers(soup, content) or page_data_from_js.get("total_followers") or network_data.get("total_followers")
            # If not found, try extracting from description text
            if not extracted_followers and extracted_description:
                follower_match = re.search(r'([\d,]+)\s+followers?\s+on\s+LinkedIn|([\d,]+)\s+followers?', extracted_description, re.IGNORECASE)
                if follower_match:
                    try:
                        num_str = (follower_match.group(1) or follower_match.group(2)).replace(',', '')
                        extracted_followers = int(num_str)
                    except:
                        pass
            
            # Always clean description - remove follower count text regardless of where followers were extracted
            if extracted_description:
                # Remove "X followers on LinkedIn" patterns
                extracted_description = re.sub(r'[\d,]+?\s+followers?\s+on\s+LinkedIn\.?\s*', '', extracted_description, flags=re.IGNORECASE).strip()
                extracted_description = re.sub(r'[\d,]+?\s+followers?\.?\s*', '', extracted_description, flags=re.IGNORECASE).strip()
                # Remove trailing "|" and clean up
                extracted_description = re.sub(r'\s*\|\s*$', '', extracted_description).strip()
                extracted_description = re.sub(r'^\|\s*', '', extracted_description).strip()
            
            page_data = {
                "page_id": page_id,
                "name": extracted_name or page_id.title(),  # Fallback to capitalized page_id
                "url": url,
                "linkedin_id": self._extract_linkedin_id(soup, content) or page_data_from_js.get("linkedin_id") or network_data.get("linkedin_id"),
                "profile_picture": self._extract_profile_picture(soup) or page_data_from_js.get("profile_picture") or network_data.get("profile_picture"),
                "description": extracted_description,
                "website": self._extract_website(soup) or page_data_from_js.get("website") or network_data.get("website"),
                "industry": self._extract_industry(soup, content) or page_data_from_js.get("industry") or network_data.get("industry"),
                "total_followers": extracted_followers,
                "head_count": self._extract_head_count(soup, content) or page_data_from_js.get("head_count") or network_data.get("head_count"),
                "specialities": self._extract_specialities(soup, content) or page_data_from_js.get("specialities", []) or network_data.get("specialities", []),
                "location": self._extract_location(soup, content) or page_data_from_js.get("location") or network_data.get("location"),
                "founded": self._extract_founded(soup, content) or page_data_from_js.get("founded") or network_data.get("founded"),
                "company_type": self._extract_company_type(soup, content) or page_data_from_js.get("company_type") or network_data.get("company_type"),
            }
            
            # Log what we successfully extracted
            extracted_fields = [k for k, v in page_data.items() if v and k not in ['page_id', 'url', 'scraped_at', 'updated_at']]
            null_fields = [k for k, v in page_data.items() if not v and k not in ['page_id', 'url', 'scraped_at', 'updated_at', 'specialities', 'posts', 'people']]
            print(f"[DEBUG] Scraped {page_id}: Extracted {len(extracted_fields)} fields: {', '.join(extracted_fields[:5])}")
            if null_fields:
                print(f"[DEBUG] Null fields for {page_id}: {', '.join(null_fields)}")
            if not self.is_authenticated and len(extracted_fields) < 5:
                print(f"[INFO] Limited data extracted. For full data (description, followers, posts, people), configure LinkedIn authentication.")
            
            # Debug: Print a sample of the HTML to help diagnose extraction issues
            if null_fields and len(null_fields) > 3:
                print(f"[DEBUG] Sample HTML for {page_id} (first 500 chars): {content[:500]}")
                # Check if we're seeing LinkedIn authwall
                if 'authwall' in content.lower() or 'sign up' in content.lower() or 'join linkedin' in content.lower():
                    print(f"[WARNING] LinkedIn authwall detected for {page_id}. Authentication required for full data.")
            
            return page_data
            
        except Exception as e:
            print(f"Error scraping page {page_id}: {e}")
            import traceback
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            return None
        finally:
            await page.close()
    
    async def scrape_posts(self, page_id: str, max_posts: int = None) -> List[Dict[str, Any]]:
        """
        Scrape posts from a LinkedIn company page.
        
        Args:
            page_id: LinkedIn page ID
            max_posts: Maximum number of posts to scrape
            
        Returns:
            List of post dictionaries
        """
        if not self.browser:
            await self.initialize()
        
        max_posts = max_posts or settings.max_posts_to_scrape
        
        # Try main page first - sometimes posts are embedded there
        main_url = f"https://www.linkedin.com/company/{page_id}/"
        posts_url = f"https://www.linkedin.com/company/{page_id}/posts/"
        
            # First, try to get posts from main page using JavaScript evaluation
        if self.context:
            main_page = await self.context.new_page()
        else:
            main_page = await self.browser.new_page()
        
        try:
            # Use domcontentloaded instead of networkidle for faster loading
            await main_page.goto(main_url, wait_until="domcontentloaded", timeout=self.timeout)
            await main_page.wait_for_timeout(3000)  # Initial wait
            
            # Scroll to load more content (fewer scrolls but longer waits)
            for _ in range(3):  # Fewer scrolls to avoid timeout
                await main_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await main_page.wait_for_timeout(2000)  # Shorter wait to avoid timeout
            
            # Try to extract posts using JavaScript (bypasses some detection)
            try:
                js_posts = await main_page.evaluate("""
                    () => {
                        const posts = [];
                        // Find all potential post elements
                        const selectors = [
                            '[class*="feed-shared-update"]',
                            '[class*="update-components"]',
                            '[class*="feed-shared"]',
                            'article'
                        ];
                        
                        for (const selector of selectors) {
                            const elements = document.querySelectorAll(selector);
                            for (const elem of elements) {
                                try {
                                    // Method 1: Look for specific post text containers
                                    const textSelectors = [
                                        '[class*="feed-shared-text__text-view"]',
                                        '[class*="update-components-text"]',
                                        '[class*="break-words"]',
                                        '[data-test-id="post-text"]',
                                        'span[dir="ltr"]',
                                        'div[class*="text-view"]'
                                    ];
                                    
                                    let postText = '';
                                    let textElem = null;
                                    
                                    for (const textSelector of textSelectors) {
                                        textElem = elem.querySelector(textSelector);
                                        if (textElem) {
                                            const text = textElem.textContent.trim();
                                            if (text.length > 30) {
                                                postText = text;
                                                break;
                                            }
                                        }
                                    }
                                    
                                    // Method 2: Find longest meaningful text block
                                    if (!postText || postText.length < 30) {
                                        const allText = elem.textContent || '';
                                        const lines = allText.split(/\\n+/)
                                            .map(line => line.trim())
                                            .filter(line => line.length > 30 && !line.match(/^\\d+[,\\d]*\\s+followers?$/i));
                                        
                                        if (lines.length > 0) {
                                            // Get longest meaningful line (prefer non-uppercase-only)
                                            postText = lines.reduce((a, b) => {
                                                const aIsCaps = a.match(/^[A-Z\\s]+$/);
                                                const bIsCaps = b.match(/^[A-Z\\s]+$/);
                                                if (aIsCaps && !bIsCaps) return b;
                                                if (!aIsCaps && bIsCaps) return a;
                                                return a.length > b.length ? a : b;
                                            });
                                        }
                                    }
                                    
                                    // Skip if content is too short
                                    if (postText.length < 30) continue;
                                    
                                    // Skip if it's just company name (uppercase only, short, few words)
                                    const isAllCaps = postText === postText.toUpperCase() && postText !== postText.toLowerCase();
                                    if (isAllCaps && postText.length < 100 && postText.split(/\\s+/).length < 6) continue;
                                    
                                    // Skip if it matches company name pattern (all caps, few words)
                                    if (postText.match(/^[A-Z\\s]+$/) && postText.split(/\\s+/).length < 8) continue;
                                    
                                    // Skip if it's just followers count
                                    if (postText.match(/^[A-Za-z\\s]+\\s*\\d+[,\\d]*\\s+followers?$/i)) continue;
                                    
                                    // Skip if content looks like metadata only
                                    if (postText.match(/^\\d+[wmd]\\s*(ago|edited)?$/i)) continue;
                                    
                                    const post = {
                                        text: postText.substring(0, 3000),
                                        html: elem.innerHTML.substring(0, 3000)
                                    };
                                    
                                    // Try to find post URL - multiple strategies
                                    const urlSelectors = [
                                        'a[href*="/posts/"]',
                                        'a[href*="/activity-"]',
                                        'a[href*="/recent-activity/"]',
                                        'a[href*="/feed/update/"]'
                                    ];
                                    for (const urlSelector of urlSelectors) {
                                        const link = elem.querySelector(urlSelector);
                                        if (link && link.href && link.href.includes('linkedin.com')) {
                                            post.url = link.href.split('?')[0]; // Remove query params
                                            break;
                                        }
                                    }
                                    
                                    // Fallback: Look for any link with post-like structure
                                    if (!post.url) {
                                        const allLinks = elem.querySelectorAll('a[href]');
                                        for (const link of allLinks) {
                                            const href = link.href || '';
                                            if (href.includes('/posts/') || href.includes('/activity-')) {
                                                post.url = href.split('?')[0];
                                                break;
                                            }
                                        }
                                    }
                                    
                                    // Try to find images (not logos or profile pics)
                                    const imgs = elem.querySelectorAll('img');
                                    for (const img of imgs) {
                                        if (img.src && img.src.includes('media.licdn.com')) {
                                            if (!img.src.includes('logo') && !img.src.includes('profile') && !img.src.includes('company-logo')) {
                                                post.image = img.src;
                                                break;
                                            }
                                        }
                                    }
                                    
                                    // Extract engagement metrics - multiple strategies
                                    // Strategy 1: Check aria-labels on buttons
                                    const buttons = elem.querySelectorAll('button[aria-label*="reaction"], button[aria-label*="like"], button[aria-label*="comment"], button[aria-label*="share"]');
                                    for (const btn of buttons) {
                                        const label = btn.getAttribute('aria-label') || '';
                                        const numMatch = label.match(/(\\d+[,\\d]*)/);
                                        if (numMatch) {
                                            const num = parseInt(numMatch[1].replace(/,/g, ''));
                                            const labelLower = label.toLowerCase();
                                            if (labelLower.includes('reaction') || labelLower.includes('like')) {
                                                post.likes = num;
                                            } else if (labelLower.includes('comment')) {
                                                post.comments = num;
                                            } else if (labelLower.includes('share')) {
                                                post.shares = num;
                                            }
                                        }
                                    }
                                    
                                    // Strategy 2: Look for spans/divs with numbers near reaction icons
                                    if (!post.likes) {
                                        const reactionSpans = elem.querySelectorAll('[class*="reaction"], [class*="social-action"], [class*="engagement"]');
                                        for (const span of reactionSpans) {
                                            const text = span.textContent || '';
                                            const numMatch = text.match(/(\\d+[,\\d]*)/);
                                            if (numMatch && text.length < 50) {
                                                const num = parseInt(numMatch[1].replace(/,/g, ''));
                                                if (!post.likes && (text.includes('reaction') || text.includes('like') || span.classList.toString().includes('reaction'))) {
                                                    post.likes = num;
                                                }
                                            }
                                        }
                                    }
                                    
                                    // Strategy 3: Look for comment counts in spans/buttons
                                    if (!post.comments) {
                                        const commentElements = elem.querySelectorAll('[class*="comment"], button[class*="comment"]');
                                        for (const el of commentElements) {
                                            const text = el.textContent || '';
                                            const numMatch = text.match(/(\\d+[,\\d]*)/);
                                            if (numMatch && text.length < 50) {
                                                post.comments = parseInt(numMatch[1].replace(/,/g, ''));
                                                break;
                                            }
                                        }
                                    }
                                    
                                    // Extract author - multiple strategies
                                    const authorSelectors = [
                                        '[class*="feed-shared-actor"] a[href*="/in/"]',
                                        '[class*="feed-shared-actor__name"]',
                                        '[class*="update-components-actor"] a[href*="/in/"]',
                                        '[class*="actor"] a[href*="/in/"]',
                                        '[class*="author"] a[href*="/in/"]',
                                        'a[href*="/in/"][class*="actor"]',
                                        'a[href*="/in/"]'
                                    ];
                                    
                                    for (const authorSelector of authorSelectors) {
                                        const author = elem.querySelector(authorSelector);
                                        if (author) {
                                            // Try to get name from link text or nearby span
                                            let authorText = author.textContent ? author.textContent.trim() : '';
                                            
                                            // If no text in link, look for nearby span with name
                                            if (!authorText || authorText.length < 2) {
                                                // Look for name in parent/ancestor
                                                let parent = author.parentElement;
                                                for (let i = 0; i < 3 && parent; i++) {
                                                    const nameSpan = parent.querySelector('span[class*="name"], span[dir="ltr"], span[aria-hidden="true"]');
                                                    if (nameSpan && nameSpan.textContent) {
                                                        const text = nameSpan.textContent.trim();
                                                        if (text.length > 2 && text.length < 100) {
                                                            authorText = text;
                                                            break;
                                                        }
                                                    }
                                                    parent = parent.parentElement;
                                                }
                                            }
                                            
                                            // Also check aria-label for name
                                            if ((!authorText || authorText.length < 2) && author.getAttribute('aria-label')) {
                                                const ariaLabel = author.getAttribute('aria-label');
                                                if (ariaLabel && !ariaLabel.toLowerCase().includes('profile') && ariaLabel.length < 100) {
                                                    authorText = ariaLabel.trim();
                                                }
                                            }
                                            
                                            // Validate and set
                                            if (authorText && authorText.length > 2 && authorText.length < 100 && 
                                                !authorText.match(/^\\d+$/) && 
                                                !authorText.toLowerCase().includes('followers') &&
                                                !authorText.toLowerCase().includes('view profile')) {
                                                post.author = authorText;
                                                post.authorUrl = author.href.split('?')[0]; // Also capture profile URL
                                                break;
                                            }
                                        }
                                    }
                                    
                                    // Fallback: Try to find any link with /in/ and get name from nearby text
                                    if (!post.author) {
                                        const profileLinks = elem.querySelectorAll('a[href*="/in/"]');
                                        for (const link of profileLinks) {
                                            const href = link.href || '';
                                            if (href.includes('/in/')) {
                                                // Look for name in the same container
                                                let container = link.closest('[class*="actor"], [class*="author"], [class*="feed"]');
                                                if (container) {
                                                    const allText = container.textContent || '';
                                                    // Try to extract a name-like pattern (2-4 words, starts with capital)
                                                    const nameMatch = allText.match(/^([A-Z][a-z]+(?:\\s+[A-Z][a-z]+){1,3})/);
                                                    if (nameMatch && nameMatch[1].length > 3 && nameMatch[1].length < 50) {
                                                        post.author = nameMatch[1];
                                                        post.authorUrl = href.split('?')[0];
                                                        break;
                                                    }
                                                }
                                            }
                                        }
                                    }
                                    
                                    // Extract date
                                    const timeElem = elem.querySelector('time[datetime]');
                                    if (timeElem) {
                                        const datetime = timeElem.getAttribute('datetime');
                                        if (datetime) post.created_at = datetime;
                                    }
                                    
                                    // Only add if we have meaningful content
                                    if (post.text && post.text.length > 30) {
                                        posts.push(post);
                                    }
                                } catch (e) {
                                    continue;
                                }
                            }
                            if (posts.length >= 25) break;
                        }
                        return posts;
                    }
                """)
                
                if js_posts and len(js_posts) > 0:
                    print(f"[INFO] Found {len(js_posts)} posts via JavaScript extraction from main page")
                    posts = []
                    for js_post in js_posts[:max_posts]:
                        # Clean the post content - remove metadata and noise
                        raw_content = js_post.get("text", "")
                        
                        # Skip if it's just company name
                        if raw_content.strip().upper() == page_id.replace('-', ' ').upper():
                            continue
                        if len(raw_content.strip()) < 50 and raw_content.isupper():
                            continue  # Likely just company name in caps
                        
                        # Remove common LinkedIn metadata patterns
                        content_clean = re.sub(r'\d+[,\d]*\s+followers?\s*on\s+LinkedIn', '', raw_content, flags=re.IGNORECASE)
                        content_clean = re.sub(r'\d+[,\d]*\s+followers?', '', content_clean, flags=re.IGNORECASE)
                        content_clean = re.sub(r'\d+[wmd]\s*(ago|edited)?', '', content_clean, flags=re.IGNORECASE)
                        # Remove company name patterns
                        content_clean = re.sub(r'^[A-Z\s]+\s+(reposted|shared|posted)\s+this\s*', '', content_clean, flags=re.IGNORECASE)
                        content_clean = re.sub(r'\s*\n\s*\n\s*', '\n', content_clean)  # Clean up multiple newlines
                        content_clean = re.sub(r'\s+', ' ', content_clean).strip()
                        
                        # Remove if content is too short or just metadata
                        if len(content_clean) < 30:
                            continue
                        
                        # Parse created_at if available
                        created_at = None
                        if js_post.get("created_at"):
                            try:
                                # Try to parse ISO format datetime
                                if 'T' in js_post["created_at"]:
                                    created_at = datetime.fromisoformat(js_post["created_at"].replace('Z', '+00:00'))
                                else:
                                    # Try other formats
                                    created_at = datetime.strptime(js_post["created_at"], "%Y-%m-%d %H:%M:%S")
                            except:
                                pass
                        
                        # Get engagement metrics from JavaScript extraction
                        likes = js_post.get("likes") or 0
                        comments_count = js_post.get("comments") or 0
                        shares = js_post.get("shares") or 0
                        author_name = js_post.get("author")
                        author_url = js_post.get("authorUrl")
                        
                        post_data = {
                            "content": content_clean,
                            "post_url": js_post.get("url") or None,
                            "image_url": js_post.get("image") or None,
                            "author_name": author_name,
                            "author_profile_url": author_url,
                            "likes": int(likes) if likes else 0,
                            "comments_count": int(comments_count) if comments_count else 0,
                            "shares": int(shares) if shares else 0,
                            "created_at": created_at,
                            "comments": []
                        }
                        # Try to extract more details from HTML if available
                        if js_post.get("html"):
                            try:
                                html_soup = BeautifulSoup(js_post["html"], 'html.parser')
                                post_data["author_name"] = self._extract_post_author(html_soup)
                                post_data["likes"] = self._extract_post_likes(html_soup)
                                post_data["comments_count"] = self._extract_post_comments_count(html_soup)
                                post_data["shares"] = self._extract_post_shares(html_soup)
                                post_data["created_at"] = self._extract_post_date(html_soup)
                            except Exception as e:
                                print(f"[DEBUG] Error extracting post details from HTML: {e}")
                                # Continue with basic data
                        
                        # Only add if we have meaningful content
                        if post_data.get("content") and len(post_data.get("content", "")) > 20:
                            posts.append(post_data)
                    
                    if len(posts) > 0:
                        print(f"[INFO] Successfully extracted {len(posts)} posts from main page via JavaScript")
                        await main_page.close()
                        return posts
            except Exception as e:
                print(f"[DEBUG] JavaScript extraction failed: {e}")
            
            # Fallback to HTML parsing
            main_content = await main_page.content()
            main_soup = BeautifulSoup(main_content, 'html.parser')
            main_posts = main_soup.find_all('div', class_=re.compile(r'feed-shared-update|update-components|feed-shared', re.I))
            
            if len(main_posts) >= 3:  # If we found posts on main page, use them
                print(f"[INFO] Found {len(main_posts)} posts on main page for {page_id}, extracting...")
                posts = []
                for i, post_elem in enumerate(main_posts[:max_posts]):
                    post_data = {
                        "content": self._extract_post_content(post_elem),
                        "author_name": self._extract_post_author(post_elem),
                        "likes": self._extract_post_likes(post_elem),
                        "comments_count": self._extract_post_comments_count(post_elem),
                        "shares": self._extract_post_shares(post_elem),
                        "post_url": self._extract_post_url(post_elem),
                        "image_url": self._extract_post_image(post_elem),
                        "created_at": self._extract_post_date(post_elem),
                        "comments": []
                    }
                    if post_data.get("content") or post_data.get("post_url"):
                        posts.append(post_data)
                
                if len(posts) > 0:
                    print(f"[INFO] Successfully extracted {len(posts)} posts from main page")
                    await main_page.close()
                    return posts
            
            await main_page.close()
        except Exception as e:
            print(f"[DEBUG] Could not extract posts from main page: {e}")
            try:
                await main_page.close()
            except:
                pass
        
        # If main page didn't work, try dedicated posts page
        url = posts_url
        
        # Use authenticated context if available
        if self.context:
            page = await self.context.new_page()
        else:
            if not self.browser:
                await self.initialize()
            page = await self.browser.new_page()
        
        posts = []
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=self.timeout)
            await page.wait_for_timeout(5000)
            
            # Check if we're redirected to login/authwall
            current_url = page.url
            page_title = await page.title()
            page_content = await page.content()
            
            # More comprehensive authwall detection
            is_authwall = (
                "login" in current_url.lower() or 
                "authwall" in current_url.lower() or 
                "challenge" in current_url.lower() or
                "checkpoint" in current_url.lower() or
                "Sign Up" in page_title or
                "Join LinkedIn" in page_title or
                "authwall" in page_content.lower() or
                "sign in to continue" in page_content.lower() or
                "join linkedin" in page_content.lower()
            )
            
            if is_authwall:
                print(f"[WARNING] LinkedIn requires authentication to view posts for {page_id}")
                print(f"[DEBUG] Current URL: {current_url}, Title: {page_title[:100]}")
                
                # If we thought we were authenticated but got authwall, update status
                if self.is_authenticated:
                    print("[INFO] Authentication appears invalid. Attempting to re-authenticate...")
                    self.is_authenticated = False
                    # Try to login if credentials are available
                    if settings.linkedin_email and settings.linkedin_password:
                        print(f"[INFO] Attempting login with credentials: {settings.linkedin_email[:3]}***")
                        login_success = await self._login()
                        if login_success:
                            self.is_authenticated = True
                            print("[INFO] Re-authentication successful. Retrying posts scrape...")
                            await page.close()
                            # Retry with authenticated session
                            return await self.scrape_posts(page_id, max_posts)
                        else:
                            print("[WARNING] Re-authentication failed. Cannot access posts without valid session.")
                    else:
                        print("[WARNING] No credentials available for re-authentication.")
                else:
                    # Not authenticated, try login if credentials available
                    if settings.linkedin_email and settings.linkedin_password:
                        print(f"[INFO] Not authenticated. Attempting login with credentials: {settings.linkedin_email[:3]}***")
                        login_success = await self._login()
                        if login_success:
                            self.is_authenticated = True
                            print("[INFO] Login successful. Retrying posts scrape...")
                            await page.close()
                            return await self.scrape_posts(page_id, max_posts)
                
                await page.close()
                return []
            
            # Wait for posts to load initially (LinkedIn loads posts dynamically)
            print(f"[DEBUG] Waiting for posts to load on {url}...")
            await page.wait_for_timeout(5000)  # Initial wait for content
            
            # Scroll more aggressively to load posts (15-25 posts requirement)
            scroll_count = 10 if self.is_authenticated else 6
            posts_found = 0
            
            for scroll_iteration in range(scroll_count):
                # Scroll down gradually (more natural)
                await page.evaluate("window.scrollBy(0, 500)")
                await page.wait_for_timeout(2000)
                await page.evaluate("window.scrollBy(0, 500)")
                await page.wait_for_timeout(2000)
                
                # Check how many posts we have using multiple methods
                current_content = await page.content()
                current_soup = BeautifulSoup(current_content, 'html.parser')
                
                # Try multiple selectors
                current_posts = current_soup.find_all('div', class_=re.compile(r'feed-shared-update|update-components|feed-shared', re.I))
                
                # Also try article tags
                if len(current_posts) == 0:
                    current_posts = current_soup.find_all('article')
                
                # Try data attributes
                if len(current_posts) == 0:
                    current_posts = current_soup.find_all('div', {'data-test-id': re.compile(r'post|update|feed', re.I)})
                
                print(f"[DEBUG] Scroll {scroll_iteration + 1}/{scroll_count}: Found {len(current_posts)} post elements")
                
                if len(current_posts) >= max_posts:
                    posts_found = len(current_posts)
                    print(f"[DEBUG] Found enough posts ({posts_found}), stopping scroll")
                    break
                
                # Try clicking "Show more" or "Load more" if available
                try:
                    show_more_button = page.locator('button:has-text("Show more"), button:has-text("Load more"), button:has-text("See more"), button:has-text("Show more posts")').first
                    if await show_more_button.is_visible(timeout=2000):
                        await show_more_button.click()
                        await page.wait_for_timeout(3000)
                        print("[DEBUG] Clicked 'Show more' button")
                except:
                    pass
                
                # Try clicking "See more updates" or similar
                try:
                    see_more = page.locator('button:has-text("See more updates"), span:has-text("See more")').first
                    if await see_more.is_visible(timeout=2000):
                        await see_more.click()
                        await page.wait_for_timeout(3000)
                        print("[DEBUG] Clicked 'See more updates'")
                except:
                    pass
            
            # Final wait for any lazy-loaded content
            await page.wait_for_timeout(3000)
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract posts with multiple selector patterns (more comprehensive)
            post_elements = []
            
            # Method 1: Class-based selectors
            post_elements.extend(soup.find_all('div', class_=re.compile(r'feed-shared-update|update-components|feed-shared', re.I)))
            
            # Method 2: Article tags
            if len(post_elements) < max_posts:
                articles = soup.find_all('article')
                print(f"[DEBUG] Found {len(articles)} article elements")
                post_elements.extend(articles)
            
            # Method 3: Data attributes
            if len(post_elements) < max_posts:
                data_posts = soup.find_all('div', {'data-test-id': re.compile(r'post|update|feed|activity', re.I)})
                print(f"[DEBUG] Found {len(data_posts)} elements with post-related data-test-id")
                post_elements.extend(data_posts)
            
            # Method 4: ID-based
            if len(post_elements) < max_posts:
                id_posts = soup.find_all('div', id=re.compile(r'post|update|feed', re.I))
                post_elements.extend(id_posts)
            
            # Method 5: Look for specific LinkedIn post structure
            if len(post_elements) < max_posts:
                # Look for divs containing post-like content
                all_divs = soup.find_all('div')
                for div in all_divs:
                    div_text = div.get_text().lower()
                    div_class = ' '.join(div.get('class', []))
                    # Check if it looks like a post (has engagement metrics or post-like structure)
                    if any(keyword in div_text for keyword in ['like', 'comment', 'share', 'repost']) or \
                       any(keyword in div_class.lower() for keyword in ['feed', 'update', 'post', 'activity']):
                        if div not in post_elements:
                            post_elements.append(div)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_posts = []
            for post in post_elements:
                post_id = id(post)
                if post_id not in seen:
                    seen.add(post_id)
                    unique_posts.append(post)
            post_elements = unique_posts
            
            # Try extracting from JSON data in script tags (LinkedIn often embeds data here)
            if len(post_elements) < max_posts:
                # Method 1: Look for JSON-LD structured data
                script_tags = soup.find_all('script', type='application/ld+json')
                for script in script_tags:
                    try:
                        import json
                        data = json.loads(script.string)
                        # Look for post data in JSON-LD
                        if isinstance(data, dict) and 'itemListElement' in data:
                            print(f"[DEBUG] Found structured data in JSON-LD for posts")
                    except:
                        pass
                
                # Method 2: Extract from inline JSON in script tags (LinkedIn embeds data here)
                all_scripts = soup.find_all('script')
                for script in all_scripts:
                    if script.string:
                        script_text = script.string
                        # Look for LinkedIn's internal data structures
                        if 'feedUpdates' in script_text or 'elements' in script_text or 'posts' in script_text:
                            try:
                                # Try to extract JSON objects
                                import json
                                # Look for JSON objects in the script
                                json_matches = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', script_text)
                                for match in json_matches[:5]:  # Limit to avoid too much processing
                                    try:
                                        data = json.loads(match)
                                        if isinstance(data, dict):
                                            # Look for post-like structures
                                            if 'text' in data or 'content' in data or 'update' in str(data).lower():
                                                print(f"[DEBUG] Found potential post data in script JSON")
                                    except:
                                        continue
                            except:
                                pass
                
                # Method 3: Try to intercept network responses (if page is still open)
                try:
                    # Use Playwright to evaluate JavaScript and extract data from page's memory
                    if page and not page.is_closed():
                        # Try to get data from LinkedIn's internal state
                        page_data_js = await page.evaluate("""
                            () => {
                                // Try to access LinkedIn's internal data structures
                                const data = {};
                                // Look for window.__INITIAL_STATE__ or similar
                                if (window.__INITIAL_STATE__) {
                                    data.initialState = window.__INITIAL_STATE__;
                                }
                                // Look for feed data
                                if (window.feedUpdates) {
                                    data.feedUpdates = window.feedUpdates;
                                }
                                // Try to find post elements via DOM
                                const postDivs = document.querySelectorAll('[class*="feed-shared"], [class*="update-components"], article');
                                data.postCount = postDivs.length;
                                return data;
                            }
                        """)
                        if page_data_js and page_data_js.get('postCount', 0) > 0:
                            print(f"[DEBUG] Found {page_data_js.get('postCount')} posts via JavaScript evaluation")
                except Exception as e:
                    print(f"[DEBUG] Could not extract via JavaScript: {e}")
                
                # Method 4: Look for posts in inline JSON patterns
                json_patterns = [
                    r'"feedUpdates":\s*\[(.*?)\]',
                    r'"elements":\s*\[(.*?)\]',
                    r'"posts":\s*\[(.*?)\]',
                    r'"updates":\s*\[(.*?)\]',
                ]
                for pattern in json_patterns:
                    matches = re.findall(pattern, content, re.DOTALL)
                    if matches:
                        print(f"[DEBUG] Found potential post data in JSON pattern: {pattern[:20]}...")
            
            print(f"[DEBUG] Found {len(post_elements)} post elements for {page_id}, extracting up to {max_posts}")
            
            # If no posts found, check if page content suggests posts exist
            if len(post_elements) == 0:
                page_text = soup.get_text().lower()
                page_html_sample = content[:2000]  # First 2000 chars
                
                print(f"[WARNING] No posts found for {page_id}")
                print(f"[DEBUG] Page text sample: {page_text[:500]}")
                print(f"[DEBUG] Page HTML sample: {page_html_sample}")
                
                # Check what LinkedIn is actually showing
                if 'post' in page_text or 'update' in page_text or 'share' in page_text:
                    print(f"[WARNING] Page suggests posts exist but none extracted. This may indicate:")
                    print(f"[WARNING] 1. LinkedIn HTML structure changed (selectors outdated)")
                    print(f"[WARNING] 2. Posts are loaded via JavaScript and need more wait time")
                    print(f"[WARNING] 3. Authentication issue (even with cookies)")
                    print(f"[WARNING] 4. LinkedIn is showing a different page structure")
                
                # Try to detect if we're on the right page
                if '/posts/' not in current_url:
                    print(f"[WARNING] Not on posts page! Current URL: {current_url}")
                elif 'feed' in current_url.lower() or 'activity' in current_url.lower():
                    print(f"[INFO] On feed/activity page, which should have posts")
                
                # Save HTML for debugging
                try:
                    debug_file = f"/tmp/linkedin_posts_debug_{page_id}.html"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"[DEBUG] Saved HTML to {debug_file} for inspection")
                except:
                    pass
            
            for i, post_elem in enumerate(post_elements[:max_posts]):
                if i >= max_posts:
                    break
                
                post_data = {
                    "content": self._extract_post_content(post_elem),
                    "author_name": self._extract_post_author(post_elem),
                    "likes": self._extract_post_likes(post_elem),
                    "comments_count": self._extract_post_comments_count(post_elem),
                    "shares": self._extract_post_shares(post_elem),
                    "post_url": self._extract_post_url(post_elem),
                    "image_url": self._extract_post_image(post_elem),
                    "created_at": self._extract_post_date(post_elem),
                    "comments": []
                }
                
                # Only add post if it has content
                if post_data.get("content") or post_data.get("post_url"):
                    # Scrape comments for this post (limit to avoid timeout)
                    if post_data.get("post_url") and len(posts) < 25:  # Limit comments scraping
                        try:
                            comments = await self._scrape_post_comments(post_data["post_url"])
                            post_data["comments"] = comments
                        except Exception as e:
                            print(f"[DEBUG] Error scraping comments for post: {e}")
                            post_data["comments"] = []
                    
                    posts.append(post_data)
            
            print(f"[DEBUG] Successfully extracted {len(posts)} posts for {page_id}")
            return posts
            
        except Exception as e:
            print(f"Error scraping posts for {page_id}: {e}")
            return posts
        finally:
            await page.close()
    
    async def scrape_people(self, page_id: str) -> List[Dict[str, Any]]:
        """
        Scrape people working at the company.
        
        Args:
            page_id: LinkedIn page ID
            
        Returns:
            List of people dictionaries
        """
        if not self.browser:
            await self.initialize()
        
        people_url = f"https://www.linkedin.com/company/{page_id}/people/"
        main_url = f"https://www.linkedin.com/company/{page_id}/"
        
        # First, try to get people from main page using JavaScript extraction
        if self.context:
            main_page = await self.context.new_page()
        else:
            main_page = await self.browser.new_page()
        
        try:
            await main_page.goto(main_url, wait_until="domcontentloaded", timeout=self.timeout)
            await main_page.wait_for_timeout(3000)
            
            # Scroll to load content
            for _ in range(3):
                await main_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await main_page.wait_for_timeout(2000)
            
            # Try JavaScript extraction for people
            try:
                js_people = await main_page.evaluate("""
                    () => {
                        const people = [];
                        // Look for people/employee elements
                        const selectors = [
                            '[class*="entity-result"]',
                            '[class*="search-result"]',
                            '[class*="people"]',
                            '[class*="employee"]',
                            '[class*="member"]',
                            'li[class*="people"]'
                        ];
                        
                        for (const selector of selectors) {
                            const elements = document.querySelectorAll(selector);
                            for (const elem of elements) {
                                const text = elem.textContent.trim();
                                // Skip job listings
                                if (text.toLowerCase().includes('jobs') || text.toLowerCase().includes('job opening')) continue;
                                
                                if (text.length > 20 && text.length < 500) {
                                    // Try to find profile link first (must have /in/ to be a real person)
                                    const link = elem.querySelector('a[href*="/in/"]');
                                    if (!link) continue;  // Skip if no profile link
                                    
                                    const person = { text: text, url: link.href };
                                    
                                    // Try to find name
                                    const nameElem = elem.querySelector('[class*="name"], h3, h2, a[href*="/in/"]');
                                    if (nameElem) {
                                        person.name = nameElem.textContent.trim();
                                        // Skip if name contains "jobs" or is too generic
                                        if (person.name.toLowerCase().includes('jobs') || person.name.toLowerCase().includes('job')) continue;
                                    }
                                    
                                    // Try to find headline/title
                                    const headlineElem = elem.querySelector('[class*="headline"], [class*="subline"], [class*="title"]');
                                    if (headlineElem) person.headline = headlineElem.textContent.trim();
                                    
                                    // Try to find profile picture
                                    const img = elem.querySelector('img');
                                    if (img && img.src && !img.src.includes('logo') && !img.src.includes('job')) {
                                        person.image = img.src;
                                    }
                                    
                                    // Only add if we have a name and URL
                                    if (person.name && person.url) {
                                        people.push(person);
                                    }
                                }
                            }
                            if (people.length >= 50) break;
                        }
                        return people;
                    }
                """)
                
                if js_people and len(js_people) > 0:
                    print(f"[INFO] Found {len(js_people)} people via JavaScript extraction from main page")
                    people = []
                    for js_person in js_people[:100]:
                        person_data = {
                            "name": js_person.get("name") or js_person.get("text", "").split("\n")[0],
                            "profile_url": js_person.get("url"),
                            "headline": js_person.get("headline"),
                            "location": None,
                            "current_position": js_person.get("headline"),
                            "profile_picture": js_person.get("image"),
                        }
                        
                        if person_data.get("name") and len(person_data["name"]) > 2:
                            people.append(person_data)
                    
                    if len(people) > 0:
                        print(f"[INFO] Successfully extracted {len(people)} people from main page via JavaScript")
                        await main_page.close()
                        return people
            except Exception as e:
                print(f"[DEBUG] JavaScript people extraction failed: {e}")
            
            await main_page.close()
        except asyncio.TimeoutError:
            print(f"[DEBUG] Timeout extracting people from main page")
            try:
                await main_page.close()
            except:
                pass
        except Exception as e:
            print(f"[DEBUG] Could not extract people from main page: {e}")
            try:
                await main_page.close()
            except:
                pass
        
        # If main page didn't work, try dedicated people page
        url = people_url
        
        # Use authenticated context if available
        if self.context:
            page = await self.context.new_page()
        else:
            if not self.browser:
                await self.initialize()
            page = await self.browser.new_page()
        
        people = []
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
            await page.wait_for_timeout(3000)
            
            # Check if we're redirected to login/authwall
            current_url = page.url
            page_title = await page.title()
            page_content = await page.content()
            
            # More comprehensive authwall detection
            is_authwall = (
                "login" in current_url.lower() or 
                "authwall" in current_url.lower() or 
                "challenge" in current_url.lower() or
                "checkpoint" in current_url.lower() or
                "Sign Up" in page_title or
                "Join LinkedIn" in page_title or
                "authwall" in page_content.lower() or
                "sign in to continue" in page_content.lower() or
                "join linkedin" in page_content.lower()
            )
            
            if is_authwall:
                print(f"[WARNING] LinkedIn requires authentication to view people for {page_id}")
                print(f"[DEBUG] Current URL: {current_url}, Title: {page_title[:100]}")
                
                # If we thought we were authenticated but got authwall, update status
                if self.is_authenticated:
                    print("[INFO] Authentication appears invalid. Attempting to re-authenticate...")
                    self.is_authenticated = False
                    # Try to login if credentials are available
                    if settings.linkedin_email and settings.linkedin_password:
                        print(f"[INFO] Attempting login with credentials: {settings.linkedin_email[:3]}***")
                        login_success = await self._login()
                        if login_success:
                            self.is_authenticated = True
                            print("[INFO] Re-authentication successful. Retrying people scrape...")
                            await page.close()
                            # Retry with authenticated session
                            return await self.scrape_people(page_id)
                        else:
                            print("[WARNING] Re-authentication failed. Cannot access people without valid session.")
                    else:
                        print("[WARNING] No credentials available for re-authentication.")
                else:
                    # Not authenticated, try login if credentials available
                    if settings.linkedin_email and settings.linkedin_password:
                        print(f"[INFO] Not authenticated. Attempting login with credentials: {settings.linkedin_email[:3]}***")
                        login_success = await self._login()
                        if login_success:
                            self.is_authenticated = True
                            print("[INFO] Login successful. Retrying people scrape...")
                            await page.close()
                            return await self.scrape_people(page_id)
                
                await page.close()
                
                # Fallback: Try to extract people from posts (post authors)
                print("[INFO] Attempting to extract people from post authors as fallback...")
                try:
                    posts_data = await self.scrape_posts(page_id, max_posts=50)
                    if posts_data:
                        people_from_posts = await self._extract_people_from_posts(posts_data)
                        if people_from_posts:
                            print(f"[INFO] Extracted {len(people_from_posts)} people from post authors")
                            return people_from_posts
                except Exception as e:
                    print(f"[DEBUG] Failed to extract people from posts: {e}")
                
                return []
            
            # Try JavaScript extraction first for better results
            try:
                js_people = await page.evaluate("""
                    () => {
                        const people = [];
                        // Look for people cards/items - LinkedIn people page uses these classes
                        const selectors = [
                            '[class*="org-people-profile-card"]',
                            '[class*="entity-result"]',
                            '[class*="search-result"]',
                            '[class*="reusable-search"]',
                            '[class*="org-people-profiles-module"]',
                            'li[class*="people"]',
                            'div[class*="people-card"]'
                        ];
                        
                        for (const selector of selectors) {
                            const elements = document.querySelectorAll(selector);
                            for (const elem of elements) {
                                try {
                                    // Must have a profile link to be valid
                                    const profileLink = elem.querySelector('a[href*="/in/"]');
                                    if (!profileLink || !profileLink.href) continue;
                                    
                                    const person = { url: profileLink.href };
                                    
                                    // Extract name - try multiple approaches
                                    const nameSelectors = [
                                        'a[href*="/in/"] span[aria-hidden="true"]',
                                        'a[href*="/in/"]',
                                        '[class*="entity-result__title"]',
                                        '[class*="name"]',
                                        'h3',
                                        'h2'
                                    ];
                                    for (const nameSelector of nameSelectors) {
                                        const nameElem = elem.querySelector(nameSelector);
                                        if (nameElem && nameElem.textContent) {
                                            const name = nameElem.textContent.trim();
                                            // Skip if it looks like metadata
                                            if (name.length > 2 && name.length < 100 && !name.match(/^\\d+$/) && !name.toLowerCase().includes('view profile')) {
                                                person.name = name;
                                                break;
                                            }
                                        }
                                    }
                                    
                                    // Extract headline/position
                                    const headlineSelectors = [
                                        '[class*="entity-result__primary-subtitle"]',
                                        '[class*="headline"]',
                                        '[class*="subline"]',
                                        '[class*="position"]',
                                        'p[class*="subtitle"]'
                                    ];
                                    for (const headlineSelector of headlineSelectors) {
                                        const headlineElem = elem.querySelector(headlineSelector);
                                        if (headlineElem && headlineElem.textContent) {
                                            const headline = headlineElem.textContent.trim();
                                            if (headline.length > 5 && !headline.toLowerCase().includes('job')) {
                                                person.headline = headline;
                                                break;
                                            }
                                        }
                                    }
                                    
                                    // Extract location
                                    const locationSelectors = [
                                        '[class*="entity-result__secondary-subtitle"]',
                                        '[class*="location"]',
                                        'span[class*="location"]'
                                    ];
                                    for (const locationSelector of locationSelectors) {
                                        const locationElem = elem.querySelector(locationSelector);
                                        if (locationElem && locationElem.textContent) {
                                            const location = locationElem.textContent.trim();
                                            if (location.length > 2 && location.length < 100) {
                                                person.location = location;
                                                break;
                                            }
                                        }
                                    }
                                    
                                    // Extract profile picture
                                    const img = elem.querySelector('img[class*="presence-entity"], img[class*="entity-result__universal-image"], img[class*="profile-photo"]');
                                    if (img && img.src && !img.src.includes('logo') && !img.src.includes('ghost') && !img.src.includes('blank')) {
                                        person.image = img.src;
                                    }
                                    
                                    // Only add if we have name and URL
                                    if (person.name && person.url) {
                                        people.push(person);
                                    }
                                } catch (e) {
                                    continue;
                                }
                            }
                            if (people.length >= 50) break;
                        }
                        return people;
                    }
                """)
                
                if js_people and len(js_people) > 0:
                    print(f"[INFO] Found {len(js_people)} people via JavaScript extraction from people page")
                    people = []
                    for js_person in js_people[:100]:
                        person_data = {
                            "name": js_person.get("name", "").strip(),
                            "profile_url": js_person.get("url"),
                            "headline": js_person.get("headline"),
                            "location": js_person.get("location"),
                            "current_position": js_person.get("headline"),  # Use headline as position
                            "profile_picture": js_person.get("image"),
                        }
                        
                        if person_data.get("name") and len(person_data["name"]) > 2:
                            people.append(person_data)
                    
                    if len(people) > 0:
                        print(f"[INFO] Successfully extracted {len(people)} people from people page via JavaScript")
                        await page.close()
                        return people
            except Exception as e:
                print(f"[DEBUG] JavaScript people extraction from people page failed: {e}")
            
            # Fallback to HTML extraction
            # Scroll more aggressively to load people
            scroll_count = 8 if self.is_authenticated else 6
            people_found = 0
            
            for scroll_iteration in range(scroll_count):
                # Scroll down
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(3000)
                
                # Try clicking "Show more" or "See more people" if available
                try:
                    show_more_selectors = [
                        'button:has-text("Show more")',
                        'button:has-text("See more people")',
                        'button[aria-label*="Show more"]',
                        'button[class*="show-more"]'
                    ]
                    for selector in show_more_selectors:
                        try:
                            show_more_button = page.locator(selector).first
                            if await show_more_button.is_visible(timeout=1000):
                                await show_more_button.click()
                                await page.wait_for_timeout(2000)
                                break
                        except:
                            continue
                except:
                    pass
                
                # Check how many people we have
                try:
                    current_count = await page.evaluate("""
                        () => {
                            return document.querySelectorAll('a[href*="/in/"]').length;
                        }
                    """)
                    if current_count >= 50:
                        people_found = current_count
                        break
                except:
                    pass
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract people with multiple selector patterns
            people_elements = soup.find_all('div', class_=re.compile(r'entity-result|search-result|reusable-search|org-people-profile-card|org-people-profiles', re.I))
            
            # Also try alternative selectors
            if len(people_elements) < 20:
                alt_elements = soup.find_all('li', class_=re.compile(r'people|employee|member', re.I))
                people_elements.extend(alt_elements)
            
            # Also look for any div containing profile links
            if len(people_elements) < 20:
                profile_link_containers = soup.find_all('div', class_=lambda x: x and ('people' in x.lower() or 'member' in x.lower() or 'employee' in x.lower()))
                people_elements.extend(profile_link_containers)
            
            # Try extracting from structured data
            if len(people_elements) < 20:
                # Look for people in JSON data
                script_tags = soup.find_all('script', type='application/ld+json')
                for script in script_tags:
                    try:
                        import json
                        data = json.loads(script.string)
                        if isinstance(data, dict) and 'employee' in data:
                            print(f"[DEBUG] Found employee data in JSON-LD")
                    except:
                        pass
            
            print(f"[DEBUG] Found {len(people_elements)} people elements for {page_id}")
            
            # If no people found, check if page content suggests people exist
            if len(people_elements) == 0:
                page_text = soup.get_text().lower()
                if 'employee' in page_text or 'people' in page_text or 'member' in page_text:
                    print(f"[WARNING] Page suggests people exist but none extracted. This may indicate authentication or selector issues.")
            
            for person_elem in people_elements[:100]:  # Limit to 100 people
                person_data = {
                    "name": self._extract_person_name(person_elem),
                    "profile_url": self._extract_person_profile_url(person_elem),
                    "headline": self._extract_person_headline(person_elem),
                    "location": self._extract_person_location(person_elem),
                    "current_position": self._extract_person_position(person_elem),
                    "profile_picture": self._extract_person_picture(person_elem),
                }
                
                # Only add if we have at least a name
                if person_data.get("name"):
                    people.append(person_data)
            
            print(f"[DEBUG] Successfully extracted {len(people)} people for {page_id}")
            return people
            
        except Exception as e:
            print(f"Error scraping people for {page_id}: {e}")
            return people
        finally:
            await page.close()
    
    async def _scrape_post_comments(self, post_url: str) -> List[Dict[str, Any]]:
        """Scrape comments for a specific post."""
        if not self.browser:
            await self.initialize()
        
        # Use authenticated context if available
        if self.context:
            page = await self.context.new_page()
        else:
            page = await self.browser.new_page()
        
        comments = []
        
        try:
            await page.goto(post_url, wait_until="networkidle", timeout=self.timeout)
            await page.wait_for_timeout(3000)
            
            # Scroll to load comments
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract comments (simplified)
            comment_elements = soup.find_all('div', class_=re.compile(r'comment', re.I))
            
            for comment_elem in comment_elements[:settings.max_comments_per_post]:
                comment_data = {
                    "author_name": self._extract_comment_author(comment_elem),
                    "content": self._extract_comment_content(comment_elem),
                    "likes": self._extract_comment_likes(comment_elem),
                    "created_at": self._extract_comment_date(comment_elem),
                }
                
                if comment_data.get("content"):
                    comments.append(comment_data)
            
            return comments
            
        except Exception as e:
            print(f"Error scraping comments for post {post_url}: {e}")
            return comments
        finally:
            await page.close()
    
    # Extraction helper methods
    def _extract_name(self, soup: BeautifulSoup, content: str = "") -> str:
        """Extract page name."""
        # Try multiple selectors (more comprehensive)
        selectors = [
            'h1.org-top-card-summary__title',
            'h1[data-test-id="org-name"]',
            'h1.top-card-layout__title',
            'h1.text-heading-xlarge',
            'h1.org-top-card-summary-info__primary-content',
            '.org-top-card-summary__title',
            '[data-test-id="org-name"]',
            'h1',
            'title',  # Fallback to page title
        ]
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                name = elem.get_text(strip=True)
                if name and len(name) > 1:
                    # Clean up title tag if used
                    if selector == 'title':
                        name = name.replace(' | LinkedIn', '').replace('Join LinkedIn', '').strip()
                    # Skip generic LinkedIn text
                    if name.lower() in ['join linkedin', 'sign up', 'linkedin', 'welcome to linkedin']:
                        continue
                    return name
        
        # Try extracting from meta tags
        meta_title = soup.select_one('meta[property="og:title"], meta[name="title"]')
        if meta_title:
            title = meta_title.get('content', '').strip()
            if title and 'join linkedin' not in title.lower():
                return title.replace(' | LinkedIn', '').strip()
        
        # Try extracting from JSON-LD (all instances)
        json_ld_scripts = soup.select('script[type="application/ld+json"]')
        for json_ld in json_ld_scripts:
            try:
                import json
                data = json.loads(json_ld.string)
                if isinstance(data, dict):
                    if 'name' in data and 'join linkedin' not in str(data.get('name', '')).lower():
                        return data['name']
                    if '@type' in data and 'Organization' in str(data.get('@type', '')):
                        if 'name' in data:
                            return data['name']
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and 'name' in item:
                            name = item['name']
                            if 'join linkedin' not in str(name).lower():
                                return name
            except:
                pass
        
        # Try extracting from script tags with more patterns
        import json
        # Look for name in various JSON patterns
        name_patterns = [
            r'"name":\s*"([^"]+)"',
            r'"localizedName":\s*"([^"]+)"',
            r'"vanityName":\s*"([^"]+)"',
            r'name["\']?\s*:\s*["\']([^"\']+)["\']',
        ]
        for pattern in name_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if match and len(match) > 1 and 'join linkedin' not in match.lower():
                    return match
        
        return ""
    
    def _extract_linkedin_id(self, soup: BeautifulSoup, content: str) -> Optional[str]:
        """Extract LinkedIn platform specific ID."""
        # Try multiple patterns for LinkedIn company ID
        patterns = [
            r'"entityUrn":"urn:li:fs_company:(\d+)"',
            r'"entityUrn":"urn:li:organization:(\d+)"',
            r'"companyId":(\d+)',
            r'"organizationId":(\d+)',
            r'urn:li:fs_company:(\d+)',
            r'urn:li:organization:(\d+)',
            r'/company/(\d+)/',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1)
        
        # Try extracting from data attributes
        org_elem = soup.select_one('[data-organization-id], [data-company-id]')
        if org_elem:
            org_id = org_elem.get('data-organization-id') or org_elem.get('data-company-id')
            if org_id:
                return str(org_id)
        
        return None
    
    def _extract_profile_picture(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract profile picture URL."""
        # Try multiple selectors for company logo
        img_selectors = [
            'img.org-top-card-primary-content__logo',
            'img[data-test-id="org-logo"]',
            'img.org-top-card-summary__image',
            '.org-top-card-primary-content__logo img',
            'img[alt*="logo"]',
            'img[alt*="Logo"]',
            'img.org-top-card-primary-content__logo-image',
            '.org-top-card-summary__image img',
            'img[src*="company-logo"]',
            'img[src*="logo"]',
        ]
        
        for selector in img_selectors:
            img = soup.select_one(selector)
            if img:
                # Try multiple attributes for image URL
                img_url = img.get('src') or img.get('data-src') or img.get('data-delayed-url') or img.get('data-lazy-url')
                if img_url:
                    # Clean up LinkedIn image URLs (remove size parameters if needed)
                    if img_url.startswith('http'):
                        return img_url
                    elif img_url.startswith('//'):
                        return 'https:' + img_url
                    elif img_url.startswith('/'):
                        return 'https://www.linkedin.com' + img_url
        
        # Try extracting from structured data
        og_image = soup.select_one('meta[property="og:image"]')
        if og_image:
            img_url = og_image.get('content', '')
            if img_url and ('linkedin.com' in img_url or 'licdn.com' in img_url):
                return img_url
        
        # Try extracting from JSON-LD
        json_ld_scripts = soup.select('script[type="application/ld+json"]')
        for json_ld in json_ld_scripts:
            try:
                import json
                data = json.loads(json_ld.string)
                if isinstance(data, dict):
                    if 'logo' in data:
                        logo = data['logo']
                        if isinstance(logo, dict) and 'url' in logo:
                            return logo['url']
                        elif isinstance(logo, str):
                            return logo
                    if 'image' in data:
                        return data['image']
            except:
                pass
        
        return None
    
    def _extract_description(self, soup: BeautifulSoup, content: str = "") -> Optional[str]:
        """Extract page description."""
        # Try multiple selectors (including authenticated page selectors)
        selectors = [
            '.org-top-card-summary__tagline',
            '[data-test-id="org-tagline"]',
            '.top-card-layout__headline',
            '.text-body-medium',
            '.break-words',
            '.org-about-us-organization-description__text',
            'div[data-test-id="about-us-description"]',
            'section.artdeco-card p',
            '.org-about-us-organization-description',
            'p.org-top-card-summary-info-list__info-item',
            '.org-about-us-organization-description__text',
            'div.org-about-us-organization-description',
        ]
        for selector in selectors:
            desc = soup.select_one(selector)
            if desc:
                text = desc.get_text(strip=True)
                # Skip generic LinkedIn descriptions and YouTube channel info
                exclude_patterns = ['750 million', 'manage your professional', 'published monthly', 'subscribers', 'youtube']
                if text and len(text) > 10 and not any(pattern in text.lower() for pattern in exclude_patterns):
                    return text
        
        # Try extracting from meta tags (most reliable for public pages)
        meta_desc = soup.select_one('meta[property="og:description"], meta[name="description"]')
        if meta_desc:
            desc_text = meta_desc.get('content', '').strip()
            # Skip generic LinkedIn descriptions and YouTube info
            exclude_patterns = ['750 million', 'published monthly', 'subscribers', 'youtube']
            if desc_text and len(desc_text) > 10 and not any(pattern in desc_text.lower() for pattern in exclude_patterns):
                return desc_text
        
        # Try extracting from JSON-LD (all instances)
        json_ld_scripts = soup.select('script[type="application/ld+json"]')
        for json_ld in json_ld_scripts:
            try:
                import json
                data = json.loads(json_ld.string)
                if isinstance(data, dict):
                    if 'description' in data:
                        desc = data['description']
                        exclude_patterns = ['750 million', 'published monthly', 'subscribers', 'youtube']
                        if desc and len(desc) > 10 and not any(pattern in str(desc).lower() for pattern in exclude_patterns):
                            return desc
                    if '@type' in data and 'Organization' in str(data.get('@type', '')):
                        if 'description' in data:
                            desc = data['description']
                            exclude_patterns = ['750 million', 'published monthly', 'subscribers', 'youtube']
                            if desc and len(desc) > 10 and not any(pattern in str(desc).lower() for pattern in exclude_patterns):
                                return desc
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and 'description' in item:
                            desc = item['description']
                            exclude_patterns = ['750 million', 'published monthly', 'subscribers', 'youtube']
                            if desc and len(desc) > 10 and not any(pattern in str(desc).lower() for pattern in exclude_patterns):
                                return desc
            except:
                pass
        
        # Try extracting from script tags with regex (more patterns)
        import json
        desc_patterns = [
            r'"description":\s*"([^"]{20,})"',
            r'"tagline":\s*"([^"]{20,})"',
            r'description["\']?\s*:\s*["\']([^"\']{20,})["\']',
        ]
        for pattern in desc_patterns:
            desc_match = re.search(pattern, content)
            if desc_match:
                desc = desc_match.group(1)
                if '750 million' not in desc.lower():
                    return desc
        
        return None
    
    def _extract_website(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract company website."""
        # Try multiple selectors for website link
        website_selectors = [
            'a.org-top-card-primary-content__website-link',
            'a[data-test-id="website"]',
            'a.org-top-card-summary-info-list__info-item',
            'a[href^="http"]:not([href*="linkedin.com"])',
            'a[href^="https"]:not([href*="linkedin.com"])',
            '.org-top-card-summary-info-list a[href^="http"]',
        ]
        
        for selector in website_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href', '').strip()
                text = link.get_text(strip=True)
                # Prefer href if it's a valid URL
                if href and (href.startswith('http://') or href.startswith('https://')):
                    if 'linkedin.com' not in href.lower() and 'linkedin' not in href.lower():
                        return href
                # Otherwise use text if it looks like a URL
                elif text and (text.startswith('http://') or text.startswith('https://')):
                    if 'linkedin.com' not in text.lower():
                        return text
        
        # Try extracting from structured data/JSON
        website_patterns = [
            r'"website":\s*"([^"]+)"',
            r'"url":\s*"([^"]+)"',
            r'"sameAs":\s*"([^"]+)"',
        ]
        for pattern in website_patterns:
            website_match = re.search(pattern, str(soup))
            if website_match:
                website = website_match.group(1)
                if website and 'linkedin.com' not in website.lower() and (website.startswith('http://') or website.startswith('https://')):
                    return website
        
        # Try extracting from JSON-LD
        json_ld_scripts = soup.select('script[type="application/ld+json"]')
        for json_ld in json_ld_scripts:
            try:
                import json
                data = json.loads(json_ld.string)
                if isinstance(data, dict):
                    if 'url' in data and data['url'] and 'linkedin.com' not in str(data['url']).lower():
                        return data['url']
                    if 'sameAs' in data:
                        same_as = data['sameAs']
                        if isinstance(same_as, list):
                            for url in same_as:
                                if url and 'linkedin.com' not in str(url).lower() and (str(url).startswith('http://') or str(url).startswith('https://')):
                                    return url
                        elif isinstance(same_as, str) and 'linkedin.com' not in same_as.lower():
                            return same_as
            except:
                pass
        
        return None
    
    def _extract_industry(self, soup: BeautifulSoup, content: str = "") -> Optional[str]:
        """Extract industry."""
        # Try specific industry selectors first
        industry_selectors = [
            '[data-test-id="industry"]',
            '.org-top-card-summary-info-list__info-item',
            '.top-card-layout__first-subline',
            '.org-top-card-summary-info-list__info-item',
            '.org-top-card-summary-info-list',
        ]
        
        for selector in industry_selectors:
            items = soup.select(selector)
            for item in items:
                text = item.get_text(strip=True)
                # Exclude non-industry text
                if text and not any(x in text.lower() for x in ['followers', 'employees', 'founded', '@', 'http', 'linkedin.com', 'on linkedin']):
                    # Industry is usually a single word or short phrase
                    if len(text) > 3 and len(text) < 100:
                        # Exclude if it contains numbers (likely not industry)
                        if not re.search(r'\d+', text):
                            # Check if it looks like an industry (common industries)
                            common_industries = ['technology', 'software', 'internet', 'financial', 'healthcare', 'education', 
                                               'consulting', 'manufacturing', 'retail', 'media', 'telecommunications', 'services',
                                               'development', 'engineering', 'management', 'advertising', 'marketing', 'higher education',
                                               'education management', 'career services', 'placement', 'recruitment']
                            if any(ind in text.lower() for ind in common_industries) or len(text.split()) <= 3:
                                return text
        
        # Try extracting from description if it mentions industry
        description_elem = soup.select_one('.org-top-card-summary-info-list, .org-top-card-primary-content')
        if description_elem:
            desc_text = description_elem.get_text()
            # Look for industry keywords in description
            industry_keywords = ['education', 'placement', 'career services', 'recruitment', 'higher education']
            for keyword in industry_keywords:
                if keyword in desc_text.lower():
                    # Try to extract the full industry phrase
                    # Build pattern outside f-string to avoid backslash issue
                    keyword_pattern = keyword.replace(" ", r"\s+")
                    pattern = rf'([A-Z][a-z]+(?:\s+[A-Z]?[a-z]+)*\s*(?:{re.escape(keyword)}|{keyword_pattern}))'
                    industry_match = re.search(pattern, desc_text, re.IGNORECASE)
                    if industry_match:
                        return industry_match.group(1).strip()
                    return keyword.title()
        
        # Try extracting from structured data/JSON
        industry_patterns = [
            r'"industry":\s*"([^"]+)"',
            r'"industryName":\s*"([^"]+)"',
            r'"industryType":\s*"([^"]+)"',
            r'"industry":\s*"([^"]{3,50})"',
        ]
        for pattern in industry_patterns:
            industry_match = re.search(pattern, content)
            if industry_match:
                industry = industry_match.group(1)
                # Clean up industry name
                if industry and len(industry) > 3 and len(industry) < 100:
                    return industry
        
        # Try extracting from JSON-LD
        json_ld_scripts = soup.select('script[type="application/ld+json"]')
        for json_ld in json_ld_scripts:
            try:
                import json
                data = json.loads(json_ld.string)
                if isinstance(data, dict):
                    if 'industry' in data:
                        return data['industry']
            except:
                pass
        
        return None
    
    def _extract_followers(self, soup: BeautifulSoup, content: str = "") -> Optional[int]:
        """Extract total followers count."""
        # Try multiple selectors (including authenticated page selectors)
        selectors = [
            '.org-top-card-summary-info-list__info-item',
            '.top-card-layout__first-subline',
            '[data-test-id="followers-count"]',
            '.org-top-card-summary-info-list',
            'span[data-test-id="followers-count"]',
            'div.org-top-card-summary-info-list',
        ]
        
        for selector in selectors:
            followers_elem = soup.select(selector)
            for elem in followers_elem:
                text = elem.get_text(strip=True)
                if 'follower' in text.lower():
                    # Extract number from text like "5,000 followers" or "5K followers" or "5M followers"
                    text_clean = text.replace(',', '').replace(' ', '')
                    # Handle K, M suffixes
                    match = re.search(r'([\d.]+)\s*([KMkm]?)\s*follower', text_clean, re.I)
                    if match:
                        try:
                            num = float(match.group(1))
                            suffix = match.group(2).upper()
                            if suffix == 'K':
                                num *= 1000
                            elif suffix == 'M':
                                num *= 1000000
                            return int(num)
                        except:
                            pass
                    # Try simple number extraction
                    match = re.search(r'([\d,]+)', text.replace(',', ''))
                    if match:
                        try:
                            return int(match.group(1))
                        except:
                            pass
        
        # Try extracting from JSON-LD
        json_ld = soup.select_one('script[type="application/ld+json"]')
        if json_ld:
            try:
                import json
                data = json.loads(json_ld.string)
                # Look for follower count in various formats
                if isinstance(data, dict):
                    if 'interactionStatistic' in data:
                        for stat in data.get('interactionStatistic', []):
                            if stat.get('interactionType') == 'https://schema.org/FollowAction':
                                count = stat.get('userInteractionCount')
                                if count:
                                    return int(count)
            except:
                pass
        
        # Try extracting from structured data/JSON in content
        followers_patterns = [
            r'"followersCount":\s*(\d+)',
            r'"followerCount":\s*(\d+)',
            r'"totalFollowers":\s*(\d+)',
            r'"followers":\s*(\d+)',
            r'followers["\']?\s*:\s*(\d+)',
            r'followerCount["\']?\s*:\s*(\d+)',
        ]
        for pattern in followers_patterns:
            followers_match = re.search(pattern, content)
            if followers_match:
                try:
                    return int(followers_match.group(1))
                except:
                    pass
        
        # Fallback: Try to extract from any text on the page (including description)
        # Look for patterns like "1,051 followers" or "1.5K followers" or "2M followers"
        page_text = soup.get_text()
        follower_text_patterns = [
            r'([\d,]+)\s+followers?\s+on\s+LinkedIn',  # "1,051 followers on LinkedIn"
            r'([\d,]+)\s+followers?',  # "1,051 followers"
            r'([\d.]+)\s*([KMkm])\s+followers?',  # "1.5K followers" or "2M followers"
        ]
        for pattern in follower_text_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                try:
                    if len(match.groups()) == 2:  # Has K/M suffix
                        num = float(match.group(1))
                        suffix = match.group(2).upper()
                        if suffix == 'K':
                            num *= 1000
                        elif suffix == 'M':
                            num *= 1000000
                        return int(num)
                    else:  # Just number
                        num_str = match.group(1).replace(',', '')
                        return int(num_str)
                except:
                    pass
        
        return None
    
    def _extract_head_count(self, soup: BeautifulSoup, content: str = "") -> Optional[str]:
        """Extract head count."""
        # Look for employee count information with more specific patterns
        info_items = soup.select('.org-top-card-summary-info-list__info-item, .top-card-layout__first-subline')
        for item in info_items:
            text = item.get_text(strip=True)
            # Look for employee-related text but exclude followers
            if 'employee' in text.lower() and 'follower' not in text.lower():
                # Clean up the text
                text_clean = re.sub(r'\d+[,\d]*\s*followers?', '', text, flags=re.IGNORECASE).strip()
                if text_clean:
                    return text_clean
            # Look for employee count patterns
            if re.search(r'\d+[,\d]*\s*employees?', text, re.I):
                return text
            # Look for range patterns like "10,001-50,000 employees"
            if re.search(r'\d+[,\d]*-\d+[,\d]*\s*employees?', text, re.I):
                return text
        
        # Try extracting from structured data with multiple patterns
        employee_patterns = [
            r'"employeesCount":\s*"([^"]+)"',
            r'"employeeCount":\s*(\d+)',
            r'"headCount":\s*"([^"]+)"',
            r'"staffSize":\s*"([^"]+)"',
        ]
        for pattern in employee_patterns:
            employees_match = re.search(pattern, content)
            if employees_match:
                return employees_match.group(1)
        
        return None
    
    def _extract_specialities(self, soup: BeautifulSoup, content: str = "") -> List[str]:
        """Extract specialities."""
        specialities = []
        
        # Look for specialities section - be more specific
        spec_section = soup.select_one('.org-top-card-summary-info-list, .specialities-section, [data-test-id="specialities"]')
        if spec_section:
            spec_items = spec_section.select('.org-top-card-summary-info-list__info-item, .speciality-item, li')
            for elem in spec_items:
                text = elem.get_text(strip=True)
                # Filter out non-speciality items
                if text and len(text) > 3 and len(text) < 50:
                    # Exclude location, followers, employees, and other non-speciality text
                    exclude_patterns = [
                        r'\d+[,\d]*\s*followers?',
                        r'\d+[,\d]*\s*employees?',
                        r'\d+[km]?\s*employees?',
                        r'founded',
                        r'@',
                        r'http',
                        r'linkedin\.com',
                        r'california',
                        r'new york',
                        r'texas',
                        r',\s*[A-Z]{2}',  # State abbreviations like ", CA"
                    ]
                    # Check if text matches exclusion patterns
                    should_exclude = False
                    for pattern in exclude_patterns:
                        if re.search(pattern, text, re.IGNORECASE):
                            should_exclude = True
                            break
                    # Also exclude if it looks like a location (contains comma and state-like text)
                    if ',' in text and any(state in text.lower() for state in ['ca', 'ny', 'tx', 'fl', 'il', 'pa']):
                        should_exclude = True
                    
                    if not should_exclude and text not in specialities:
                        specialities.append(text)
        
        # Try extracting from structured data
        if not specialities:
            spec_patterns = [
                r'"specialities":\s*\[(.*?)\]',
                r'"specialties":\s*\[(.*?)\]',
                r'"speciality":\s*\[(.*?)\]',
            ]
            for pattern in spec_patterns:
                spec_match = re.findall(pattern, content)
                if spec_match:
                    # Parse JSON array
                    import json
                    try:
                        spec_list = json.loads(f"[{spec_match[0]}]")
                        for s in spec_list:
                            if s and str(s) not in specialities:
                                # Filter out non-speciality items
                                s_str = str(s)
                                if not any(x in s_str.lower() for x in ['followers', 'employees', 'founded', '@', 'http']):
                                    specialities.append(s_str)
                    except:
                        pass
        
        return specialities[:10]  # Limit to 10
    
    def _extract_location(self, soup: BeautifulSoup, content: str = "") -> Optional[str]:
        """Extract location."""
        # Try multiple selectors - filter after selection since :has-text() isn't supported
        selectors = [
            '[data-test-id="location"]',
            '.org-top-card-summary-info-list__info-item',
            '.top-card-layout__first-subline',
            '.org-top-card-summary-info-list__info-item',
            '.org-top-card-summary-info-list',
        ]
        
        for selector in selectors:
            location_elems = soup.select(selector)
            for elem in location_elems:
                text = elem.get_text(strip=True)
                # Exclude followers, employees, and other non-location text
                if text and not any(x in text.lower() for x in ['followers', 'employees', 'founded', '@', 'http', 'on linkedin']):
                    # Look for location patterns (city, state/country)
                    location_indicators = ['city', 'state', 'country', 'united states', 'usa', 'california', 'new york', 
                                         'texas', 'bengaluru', 'bangalore', 'mumbai', 'delhi', 'india', 'karnataka',
                                         'maharashtra', 'tamil nadu', 'kerala', 'hyderabad', 'pune', 'chennai']
                    if (',' in text or any(x in text.lower() for x in location_indicators)):
                        # Clean up - remove any numbers that might be followers count
                        text_clean = re.sub(r'\d+[,\d]*\s*followers?', '', text, flags=re.IGNORECASE).strip()
                        text_clean = re.sub(r'\d+[,\d]*\s*employees?', '', text_clean, flags=re.IGNORECASE).strip()
                        # Remove trailing numbers that might be follower counts
                        text_clean = re.sub(r'\s+\d+[,\d]*$', '', text_clean).strip()
                        # Remove "on LinkedIn" text
                        text_clean = re.sub(r'\s+on\s+linkedin\.?\s*$', '', text_clean, flags=re.IGNORECASE).strip()
                        # Remove pipe separators
                        text_clean = re.sub(r'^\|\s*|\s*\|$', '', text_clean).strip()
                        if len(text_clean) > 3 and len(text_clean) < 100:
                            return text_clean
        
        # Try extracting from description if it mentions location
        description_elem = soup.select_one('.org-top-card-summary-info-list, .org-top-card-primary-content')
        if description_elem:
            desc_text = description_elem.get_text()
            # Look for location in description (e.g., "Manipal Institute of Technology, Bengaluru")
            location_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,?\s*(?:Bengaluru|Bangalore|Mumbai|Delhi|Hyderabad|Pune|Chennai|Karnataka|Maharashtra|India))', desc_text)
            if location_match:
                return location_match.group(1).strip()
        
        # Try extracting from structured data/JSON
        location_patterns = [
            r'"location":\s*"([^"]+)"',
            r'"headquarters":\s*"([^"]+)"',
            r'"addressLocality":\s*"([^"]+)"',
            r'"addressRegion":\s*"([^"]+)"',
            r'"addressCountry":\s*"([^"]+)"',
        ]
        for pattern in location_patterns:
            location_match = re.search(pattern, content)
            if location_match:
                loc = location_match.group(1)
                # Clean up location
                loc = re.sub(r'\d+[,\d]*\s*followers?', '', loc, flags=re.IGNORECASE).strip()
                loc = re.sub(r'\s+on\s+linkedin\.?\s*$', '', loc, flags=re.IGNORECASE).strip()
                if loc and len(loc) > 3:
                    return loc
        
        # Try extracting from JSON-LD
        json_ld_scripts = soup.select('script[type="application/ld+json"]')
        for json_ld in json_ld_scripts:
            try:
                import json
                data = json.loads(json_ld.string)
                if isinstance(data, dict):
                    if 'address' in data:
                        address = data['address']
                        if isinstance(address, dict):
                            parts = []
                            if 'addressLocality' in address:
                                parts.append(address['addressLocality'])
                            if 'addressRegion' in address:
                                parts.append(address['addressRegion'])
                            if parts:
                                return ', '.join(parts)
            except:
                pass
        
        return None
    
    def _extract_founded(self, soup: BeautifulSoup, content: str = "") -> Optional[str]:
        """Extract founded year."""
        # Look for founded information with more specific patterns
        info_items = soup.select('.org-top-card-summary-info-list__info-item, .top-card-layout__first-subline')
        for item in info_items:
            text = item.get_text(strip=True)
            if 'founded' in text.lower():
                # Extract year (4 digits, typically 1800-2100)
                year_match = re.search(r'\b(1[89]\d{2}|20[0-2]\d)\b', text)
                if year_match:
                    return year_match.group(1)
                # If no year found, return the text
                if len(text) < 50:  # Reasonable length
                    return text
        
        # Try extracting from structured data with multiple patterns
        founded_patterns = [
            r'"founded":\s*"([^"]+)"',
            r'"foundedYear":\s*(\d{4})',
            r'"foundedOn":\s*"([^"]+)"',
            r'"yearFounded":\s*(\d{4})',
            r'founded["\']?\s*:\s*["\']?(\d{4})',
        ]
        for pattern in founded_patterns:
            founded_match = re.search(pattern, content)
            if founded_match:
                founded = founded_match.group(1)
                # If it's just a year, return it
                if founded.isdigit() and len(founded) == 4:
                    return founded
                # Otherwise return the full text
                return founded
        
        return None
    
    def _extract_company_type(self, soup: BeautifulSoup, content: str = "") -> Optional[str]:
        """Extract company type."""
        # Try extracting from structured data/JSON
        company_type_patterns = [
            r'"companyType":\s*"([^"]+)"',
            r'"type":\s*"([^"]+)"',
            r'"organizationType":\s*"([^"]+)"',
            r'"entityType":\s*"([^"]+)"',
        ]
        for pattern in company_type_patterns:
            type_match = re.search(pattern, content)
            if type_match:
                company_type = type_match.group(1)
                if company_type and len(company_type) < 50:
                    return company_type
        
        # Try extracting from visible text
        info_items = soup.select('.org-top-card-summary-info-list__info-item, .top-card-layout__first-subline')
        for item in info_items:
            text = item.get_text(strip=True).lower()
            # Common company types
            company_types = ['public company', 'private company', 'non-profit', 'government agency', 
                           'educational', 'self-employed', 'partnership', 'sole proprietorship']
            for ctype in company_types:
                if ctype in text:
                    return ctype.title()
        
        return None
    
    def _extract_post_content(self, elem) -> str:
        """Extract post content."""
        # Try multiple selectors for post content
        selectors = [
            '.feed-shared-text',
            '.update-components-text',
            '.feed-shared-update-v2__description',
            '.feed-shared-text__text-view',
            '[data-test-id="post-text"]',
            '.break-words',
            'span.feed-shared-text__text-view',
            'div.feed-shared-text',
        ]
        for selector in selectors:
            content = elem.select_one(selector)
            if content:
                text = content.get_text(strip=True)
                if text and len(text) > 5:
                    return text
        
        # Try to get from any text element
        text_elements = elem.select('p, span, div')
        for text_elem in text_elements:
            text = text_elem.get_text(strip=True)
            if text and len(text) > 20 and len(text) < 5000:  # Reasonable post length
                return text
        
        return ""
    
    def _extract_post_author(self, elem) -> Optional[str]:
        """Extract post author."""
        author = elem.select_one('.feed-shared-actor__name, .update-components-actor__name')
        if author:
            return author.get_text(strip=True)
        return None
    
    def _extract_post_likes(self, elem) -> int:
        """Extract post likes count."""
        # Try multiple selectors
        selectors = [
            '.social-actions-button__reactions-count',
            '[data-test-id="social-actions__reactions-count"]',
            '.social-actions-button__reactions-count-button',
            'button[aria-label*="reaction"]',
            'span:has-text("reaction")',
        ]
        for selector in selectors:
            likes = elem.select_one(selector)
            if likes:
                text = likes.get_text(strip=True)
                # Handle K, M suffixes
                text_clean = text.replace(',', '').replace(' ', '')
                match = re.search(r'([\d.]+)\s*([KMkm]?)', text_clean)
                if match:
                    try:
                        num = float(match.group(1))
                        suffix = match.group(2).upper()
                        if suffix == 'K':
                            num *= 1000
                        elif suffix == 'M':
                            num *= 1000000
                        return int(num)
                    except:
                        pass
                # Try simple number
                match = re.search(r'(\d+)', text.replace(',', ''))
                if match:
                    try:
                        return int(match.group(1))
                    except:
                        pass
        return 0
    
    def _extract_post_comments_count(self, elem) -> int:
        """Extract post comments count."""
        # Try multiple selectors
        selectors = [
            '.social-actions-button__comment-count',
            '[data-test-id="social-actions__comments-count"]',
            'button[aria-label*="comment"]',
            # Note: :has-text() is Playwright-only, not supported in BeautifulSoup
        ]
        for selector in selectors:
            comments = elem.select_one(selector)
            if comments:
                text = comments.get_text(strip=True)
                match = re.search(r'(\d+)', text.replace(',', ''))
                if match:
                    try:
                        return int(match.group(1))
                    except:
                        pass
        return 0
    
    def _extract_post_shares(self, elem) -> int:
        """Extract post shares count."""
        shares = elem.select_one('.social-actions-button__share-count')
        if shares:
            text = shares.get_text(strip=True)
            match = re.search(r'(\d+)', text.replace(',', ''))
            if match:
                try:
                    return int(match.group(1))
                except:
                    pass
        return 0
    
    def _extract_post_url(self, elem) -> Optional[str]:
        """Extract post URL."""
        # Try multiple selectors
        selectors = [
            'a[href*="/posts/"]',
            'a[href*="/activity-"]',
            'a[data-test-id="post-link"]',
            'a.feed-shared-update-v2__description-wrapper',
        ]
        for selector in selectors:
            link = elem.select_one(selector)
            if link:
                href = link.get('href')
                if href:
                    if not href.startswith('http'):
                        return f"https://www.linkedin.com{href}"
                    return href
        
        # Try to extract from data attributes
        if elem.get('data-urn'):
            urn = elem.get('data-urn')
            # Convert URN to URL if possible
            if 'activity' in urn:
                activity_id = urn.split(':')[-1] if ':' in urn else urn
                return f"https://www.linkedin.com/feed/update/{activity_id}"
        
        return None
    
    def _extract_post_image(self, elem) -> Optional[str]:
        """Extract post image URL."""
        img = elem.select_one('img.feed-shared-image, img.update-components-image')
        if img:
            return img.get('src') or img.get('data-src')
        return None
    
    def _extract_post_date(self, elem) -> Optional[datetime]:
        """Extract post date."""
        date_elem = elem.select_one('.feed-shared-actor__sub-description, time')
        if date_elem:
            datetime_attr = date_elem.get('datetime')
            if datetime_attr:
                try:
                    return datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
                except:
                    pass
        return None
    
    async def _extract_people_from_posts(self, posts_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract people from post authors as a fallback when people page is inaccessible.
        
        Note: This method only extracts basic info (name, profile_url) from posts.
        Full profile data (headline, location, profile_picture, etc.) requires visiting
        individual profile pages, which is slow and may trigger bot detection.
        """
        people_dict = {}  # Use dict to deduplicate by profile_url
        
        for post in posts_data:
            author_profile_url = post.get("author_profile_url")
            author_name = post.get("author_name")
            
            # Only add if we have a profile URL (required field)
            if author_profile_url and author_profile_url not in people_dict:
                # Extract LinkedIn username from URL
                linkedin_user_id = None
                display_name = None
                
                if "/in/" in author_profile_url:
                    # Extract username from URL like https://in.linkedin.com/in/rajeshjaipur
                    parts = author_profile_url.split("/in/")
                    if len(parts) > 1:
                        username = parts[1].split("/")[0].split("?")[0]
                        linkedin_user_id = username
                        
                        # Try to extract a readable name from the username
                        # Convert "rajesh-gupta-12345" -> "Rajesh Gupta"
                        if username and not author_name:
                            # Remove numbers and dashes, capitalize words
                            name_parts = username.split('-')
                            # Filter out numeric parts and convert to title case
                            clean_parts = []
                            for part in name_parts:
                                if part and not part.isdigit() and len(part) > 1:
                                    clean_parts.append(part.capitalize())
                            if len(clean_parts) >= 2:  # At least first and last name
                                display_name = ' '.join(clean_parts[:2])  # Use first 2 parts (first + last name)
                            elif len(clean_parts) == 1:
                                display_name = clean_parts[0]
                
                person_data = {
                    "linkedin_user_id": linkedin_user_id,
                    "name": author_name or display_name or "Unknown",  # Prefer author_name, then extracted name, then Unknown
                    "profile_url": author_profile_url,
                    # Note: profile_picture, headline, location, etc. require visiting the profile page
                    # This is not done here to avoid triggering bot detection and slowing down scraping
                    "profile_picture": None,
                    "headline": None,
                    "location": None,
                    "current_position": None,
                    "connection_count": None,
                }
                
                # Only add if we have at least profile_url
                if person_data["profile_url"]:
                    people_dict[author_profile_url] = person_data
        
        if people_dict:
            print(f"[INFO] Extracted {len(people_dict)} people from post authors. Enriching with full profile data...")
            # Enrich with full profile data by visiting individual profiles
            enriched_people = await self._enrich_people_profiles(list(people_dict.values()))
            return enriched_people
        
        return list(people_dict.values())
    
    async def _enrich_people_profiles(self, people: List[Dict[str, Any]], max_profiles: int = 20) -> List[Dict[str, Any]]:
        """Enrich people data by visiting their LinkedIn profile pages.
        
        Args:
            people: List of people dicts with at least profile_url
            max_profiles: Maximum number of profiles to enrich (to avoid too many requests)
            
        Returns:
            List of enriched people dicts
        """
        if not people or not self.context:
            return people
        
        enriched = []
        # Limit to avoid too many requests
        profiles_to_enrich = people[:max_profiles]
        
        print(f"[INFO] Enriching {len(profiles_to_enrich)} profile(s) with full data (headline, location, profile_picture, etc.)...")
        
        for i, person in enumerate(profiles_to_enrich):
            profile_url = person.get("profile_url")
            if not profile_url:
                enriched.append(person)
                continue
            
            try:
                # Rate limiting: delay between requests (3-5 seconds)
                if i > 0:
                    delay = 3 + (i % 3)  # 3-5 seconds
                    print(f"[INFO] Waiting {delay}s before next profile request (rate limiting)...")
                    await asyncio.sleep(delay)
                
                page = await self.context.new_page()
                
                try:
                    await page.goto(profile_url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(3000)  # Wait for content to load
                    
                    # Check for authwall or redirect
                    current_url = page.url
                    if "login" in current_url.lower() or "authwall" in current_url.lower():
                        print(f"[WARNING] Cannot access profile {profile_url} - authentication required")
                        enriched.append(person)  # Use basic data
                        continue
                    
                    # Extract profile data using JavaScript
                    profile_data = await page.evaluate("""
                        () => {
                            const data = {};
                            
                            // Extract headline - try more selectors
                            const headlineSelectors = [
                                '.text-body-medium.break-words',
                                '.ph5.pb5 .text-body-medium.break-words',
                                '[class*="top-card-layout__headline"]',
                                '[data-generated-suggestion-target]',
                                '.ph5 .text-body-medium',
                                'h2[class*="headline"]',
                                '.pv-text-details__left-panel h2',
                                'div[class*="headline"]',
                                'span[class*="text-body-medium"]',
                                '.top-card-layout__headline'
                            ];
                            for (const selector of headlineSelectors) {
                                try {
                                    const elem = document.querySelector(selector);
                                    if (elem) {
                                        const text = elem.textContent ? elem.textContent.trim() : '';
                                        if (text && text.length > 5 && text.length < 200 && !text.toLowerCase().includes('connections')) {
                                            data.headline = text;
                                            break;
                                        }
                                    }
                                } catch(e) {
                                    continue;
                                }
                            }
                            
                            // Extract location - try more selectors
                            const locationSelectors = [
                                '.text-body-small.inline.t-black--light.break-words',
                                '.ph5 .text-body-small',
                                '[class*="top-card-layout__first-subline"]',
                                'span[class*="location"]',
                                '.text-body-small[class*="location"]',
                                '.top-card-layout__first-subline',
                                'span[class*="text-body-small"]:not([class*="headline"])'
                            ];
                            for (const selector of locationSelectors) {
                                try {
                                    const elem = document.querySelector(selector);
                                    if (elem) {
                                        const text = elem.textContent ? elem.textContent.trim() : '';
                                        if (text && text.length > 2 && text.length < 100 && 
                                            !text.includes('connections') && 
                                            !text.toLowerCase().includes('followers') &&
                                            !text.match(/^\\d+$/)) {
                                            // Likely a location if it contains common location words or commas
                                            if (text.includes(',') || /^[A-Z][a-z]+/.test(text)) {
                                                data.location = text;
                                                break;
                                            }
                                        }
                                    }
                                } catch(e) {
                                    continue;
                                }
                            }
                            
                            // Extract profile picture - improved selectors
                            const imgSelectors = [
                                'img[class*="presence-entity__image"]',
                                'img[class*="profile-photo"]',
                                '.pv-top-card-profile-picture__image',
                                'img[alt*="profile"]',
                                '.top-card-profile-picture img',
                                'img[src*="media.licdn.com/dms/image"][src*="/profile"]'
                            ];
                            for (const selector of imgSelectors) {
                                try {
                                    const img = document.querySelector(selector);
                                    if (img && img.src) {
                                        const src = img.src.split('?')[0];
                                        if (src && !src.includes('logo') && !src.includes('ghost') && !src.includes('blank')) {
                                            data.profile_picture = src;
                                            break;
                                        }
                                    }
                                } catch(e) {
                                    continue;
                                }
                            }
                            
                            // Extract name (in case it wasn't in posts)
                            if (!data.name) {
                                const nameSelectors = [
                                    'h1[class*="text-heading-xlarge"]',
                                    '.text-heading-xlarge',
                                    '.top-card-layout__title',
                                    'h1',
                                    '[class*="top-card-layout__title"]'
                                ];
                                for (const selector of nameSelectors) {
                                    try {
                                        const elem = document.querySelector(selector);
                                        if (elem && elem.textContent) {
                                            const text = elem.textContent.trim();
                                            if (text.length > 2 && text.length < 100) {
                                                data.name = text;
                                                break;
                                            }
                                        }
                                    } catch(e) {
                                        continue;
                                    }
                                }
                            }
                            
                            return data;
                        }
                    """)
                    
                    # Update person data with enriched fields (handle None case)
                    if profile_data and isinstance(profile_data, dict):
                        if profile_data.get("name"):
                            person["name"] = profile_data["name"]
                        if profile_data.get("headline"):
                            person["headline"] = profile_data["headline"]
                            person["current_position"] = profile_data["headline"]  # Use headline as position
                        if profile_data.get("location"):
                            person["location"] = profile_data["location"]
                        if profile_data.get("profile_picture"):
                            person["profile_picture"] = profile_data["profile_picture"]
                    else:
                        print(f"[DEBUG] Profile data extraction returned: {type(profile_data)}")
                    
                    print(f"[INFO] Enriched profile: {person.get('name', 'Unknown')} - {person.get('headline', 'N/A')[:50]}")
                    
                except asyncio.TimeoutError:
                    print(f"[WARNING] Timeout accessing profile {profile_url}")
                except Exception as e:
                    print(f"[WARNING] Error enriching profile {profile_url}: {e}")
                finally:
                    await page.close()
                
                enriched.append(person)
                
            except Exception as e:
                print(f"[WARNING] Error processing profile {profile_url}: {e}")
                enriched.append(person)  # Use basic data if enrichment fails
        
        # Add remaining people without enrichment
        enriched.extend(people[max_profiles:])
        
        print(f"[INFO] Successfully enriched {len(profiles_to_enrich)} profile(s)")
        return enriched
    
    def _extract_comment_author(self, elem) -> Optional[str]:
        """Extract comment author."""
        author = elem.select_one('.comment__actor-name, .comments-post-meta__actor-name')
        if author:
            return author.get_text(strip=True)
        return None
    
    def _extract_comment_content(self, elem) -> str:
        """Extract comment content."""
        # Try multiple selectors
        selectors = [
            '.comment__text',
            '.comments-post-meta__text',
            '.comment-text',
            '[data-test-id="comment-text"]',
            '.feed-shared-comment__text',
            'p.comment',
            'div.comment-content',
        ]
        for selector in selectors:
            content = elem.select_one(selector)
            if content:
                text = content.get_text(strip=True)
                if text and len(text) > 1:
                    return text
        
        # Fallback: get any text content
        text = elem.get_text(strip=True)
        if text and len(text) > 5:
            return text
        
        return ""
    
    def _extract_comment_likes(self, elem) -> int:
        """Extract comment likes."""
        likes = elem.select_one('.comment__social-action-count')
        if likes:
            text = likes.get_text(strip=True)
            match = re.search(r'(\d+)', text.replace(',', ''))
            if match:
                try:
                    return int(match.group(1))
                except:
                    pass
        return 0
    
    def _extract_comment_date(self, elem) -> Optional[datetime]:
        """Extract comment date."""
        date_elem = elem.select_one('time')
        if date_elem:
            datetime_attr = date_elem.get('datetime')
            if datetime_attr:
                try:
                    return datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
                except:
                    pass
        return None
    
    def _extract_person_name(self, elem) -> Optional[str]:
        """Extract person name."""
        # Try multiple selectors
        selectors = [
            '.entity-result__title-text a',
            '.search-result__result-link',
            'a[data-test-id="people-name"]',
            '.org-people-profile-card__profile-title',
            'h3 a',
            'a[href*="/in/"]',
        ]
        for selector in selectors:
            name = elem.select_one(selector)
            if name:
                text = name.get_text(strip=True)
                if text and len(text) > 1:
                    return text
        
        # Try to get from heading
        heading = elem.select_one('h3, h4, .entity-result__title')
        if heading:
            text = heading.get_text(strip=True)
            if text:
                return text
        
        return None
    
    def _extract_person_profile_url(self, elem) -> Optional[str]:
        """Extract person profile URL."""
        link = elem.select_one('a[href*="/in/"]')
        if link:
            href = link.get('href')
            if href and not href.startswith('http'):
                return f"https://www.linkedin.com{href}"
            return href
        return None
    
    def _extract_person_headline(self, elem) -> Optional[str]:
        """Extract person headline."""
        headline = elem.select_one('.entity-result__primary-subtitle, .search-result__snippets')
        if headline:
            return headline.get_text(strip=True)
        return None
    
    def _extract_person_location(self, elem) -> Optional[str]:
        """Extract person location."""
        location = elem.select_one('.entity-result__secondary-subtitle')
        if location:
            return location.get_text(strip=True)
        return None
    
    def _extract_person_position(self, elem) -> Optional[str]:
        """Extract person current position."""
        # Position is often in the headline
        return self._extract_person_headline(elem)
    
    def _extract_person_picture(self, elem) -> Optional[str]:
        """Extract person profile picture."""
        img = elem.select_one('img.entity-result__image, img.search-result__image')
        if img:
            return img.get('src') or img.get('data-src')
        return None
    
    async def _extract_from_javascript(self, page: PlaywrightPage) -> Dict[str, Any]:
        """Extract data from JavaScript variables and window objects."""
        data = {}
        try:
            # Try to extract from window.__INITIAL_STATE__ or similar
            js_code = """
            () => {
                const data = {};
                // Try to find data in window objects
                if (window.__INITIAL_STATE__) {
                    data.initial_state = window.__INITIAL_STATE__;
                }
                if (window.__APP_STATE__) {
                    data.app_state = window.__APP_STATE__;
                }
                if (window.__INITIAL_LOAD_STATE__) {
                    data.initial_load_state = window.__INITIAL_LOAD_STATE__;
                }
                if (window.__INITIAL_LOADING_STATE__) {
                    data.initial_loading_state = window.__INITIAL_LOADING_STATE__;
                }
                // Try to find JSON-LD structured data
                const jsonLd = document.querySelector('script[type="application/ld+json"]');
                if (jsonLd) {
                    try {
                        data.json_ld = JSON.parse(jsonLd.textContent);
                    } catch(e) {}
                }
                // Try to find ALL JSON-LD scripts
                const allJsonLd = Array.from(document.querySelectorAll('script[type="application/ld+json"]'));
                if (allJsonLd.length > 0) {
                    data.all_json_ld = [];
                    allJsonLd.forEach(script => {
                        try {
                            data.all_json_ld.push(JSON.parse(script.textContent));
                        } catch(e) {}
                    });
                }
                // Try to find data in script tags (more aggressive)
                const scripts = Array.from(document.querySelectorAll('script:not([src])'));
                const relevantScripts = [];
                for (const script of scripts) {
                    const text = script.textContent || '';
                    if (text.length > 100 && (
                        text.includes('"company"') || 
                        text.includes('"organization"') ||
                        text.includes('"name"') ||
                        text.includes('"description"') ||
                        text.includes('followers') ||
                        text.includes('industry')
                    )) {
                        relevantScripts.push(text.substring(0, 5000)); // First 5000 chars
                    }
                }
                data.relevant_scripts = relevantScripts;
                
                // Try to extract from data attributes
                const pageElement = document.querySelector('[data-test-id="org-name"], .org-top-card-summary__title, h1');
                if (pageElement) {
                    data.page_element_text = pageElement.textContent;
                    data.page_element_html = pageElement.innerHTML;
                }
                
                return data;
            }
            """
            result = await page.evaluate(js_code)
            if result:
                # Parse the extracted data
                if result.get('json_ld'):
                    json_ld = result['json_ld']
                    if isinstance(json_ld, dict):
                        data['name'] = json_ld.get('name') or data.get('name')
                        data['description'] = json_ld.get('description') or data.get('description')
                        data['url'] = json_ld.get('url') or data.get('url')
                
                # Parse all JSON-LD
                if result.get('all_json_ld'):
                    for json_ld_item in result['all_json_ld']:
                        if isinstance(json_ld_item, dict):
                            if '@type' in json_ld_item and 'Organization' in str(json_ld_item.get('@type', '')):
                                data['name'] = json_ld_item.get('name') or data.get('name')
                                data['description'] = json_ld_item.get('description') or data.get('description')
                                data['url'] = json_ld_item.get('url') or data.get('url')
                                if 'sameAs' in json_ld_item:
                                    data['website'] = json_ld_item.get('sameAs')
                
                # Try to extract from relevant scripts
                if result.get('relevant_scripts'):
                    import json
                    import re
                    for script_text in result['relevant_scripts']:
                        # Try to find JSON objects
                        json_matches = re.findall(r'\{[^{}]*"(?:name|description|followers|industry|website)"[^{}]*\}', script_text)
                        for match in json_matches:
                            try:
                                parsed = json.loads(match)
                                if 'name' in parsed and not data.get('name'):
                                    data['name'] = parsed['name']
                                if 'description' in parsed and not data.get('description'):
                                    data['description'] = parsed['description']
                                if 'followers' in parsed and not data.get('total_followers'):
                                    data['total_followers'] = parsed.get('followers')
                            except:
                                pass
        except Exception as e:
            print(f"[DEBUG] Error extracting from JavaScript: {e}")
        return data
    
    async def _extract_from_network_responses(self, page: PlaywrightPage) -> Dict[str, Any]:
        """Extract data from network API responses."""
        data = {}
        responses = []
        handler_added = False
        
        try:
            # Set up response listener
            async def handle_response(response):
                url = response.url
                if 'linkedin.com' in url and ('api' in url or 'voyager' in url or 'graphql' in url or 'voyager-api' in url):
                    try:
                        content_type = response.headers.get('content-type', '')
                        if 'application/json' in content_type:
                            json_data = await response.json()
                            responses.append({
                                'url': url,
                                'data': json_data
                            })
                    except Exception as e:
                        # Some responses might not be JSON or might be too large
                        pass
            
            # Add listener if not already added
            if not handler_added:
                page.on('response', handle_response)
                handler_added = True
            
            # Wait a bit for responses to come in
            await page.wait_for_timeout(3000)
            
            # Parse responses for company data
            for response_info in responses:
                response_data = response_info.get('data', {})
                if isinstance(response_data, dict):
                    # Look for company/organization data in various structures
                    def extract_from_dict(obj, path='', depth=0):
                        if depth > 10:  # Prevent infinite recursion
                            return
                        if isinstance(obj, dict):
                            # Check for common LinkedIn data fields
                            if 'name' in obj and not data.get('name') and 'join linkedin' not in str(obj.get('name', '')).lower():
                                data['name'] = obj.get('name')
                            if 'localizedName' in obj and not data.get('name'):
                                data['name'] = obj.get('localizedName')
                            if 'vanityName' in obj and not data.get('name'):
                                data['name'] = obj.get('vanityName')
                            if 'description' in obj and not data.get('description') and '750 million' not in str(obj.get('description', '')).lower():
                                data['description'] = obj.get('description')
                            if 'followersCount' in obj and not data.get('total_followers'):
                                data['total_followers'] = obj.get('followersCount')
                            if 'followerCount' in obj and not data.get('total_followers'):
                                data['total_followers'] = obj.get('followerCount')
                            if 'totalFollowers' in obj and not data.get('total_followers'):
                                data['total_followers'] = obj.get('totalFollowers')
                            if 'industry' in obj and not data.get('industry'):
                                if isinstance(obj.get('industry'), str):
                                    data['industry'] = obj.get('industry')
                            if 'website' in obj and not data.get('website'):
                                data['website'] = obj.get('website')
                            if 'localizedWebsite' in obj and not data.get('website'):
                                data['website'] = obj.get('localizedWebsite')
                            if 'location' in obj and not data.get('location'):
                                data['location'] = obj.get('location')
                            if 'foundedOn' in obj and not data.get('founded'):
                                data['founded'] = str(obj.get('foundedOn'))
                            if 'specialties' in obj and not data.get('specialities'):
                                specialties = obj.get('specialties', [])
                                if isinstance(specialties, list):
                                    data['specialities'] = [str(s) for s in specialties if s]
                            
                            # Recursively search nested structures
                            for key, value in obj.items():
                                if isinstance(value, (dict, list)):
                                    extract_from_dict(value, f"{path}.{key}", depth + 1)
                        elif isinstance(obj, list):
                            for item in obj:
                                extract_from_dict(item, path, depth + 1)
                    
                    extract_from_dict(response_data)
        except Exception as e:
            print(f"[DEBUG] Error extracting from network: {e}")
        
        return data


scraper_service = LinkedInScraperService()

