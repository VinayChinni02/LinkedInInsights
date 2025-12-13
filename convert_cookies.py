"""
Convert browser cookie format to Playwright format.
"""
import json
import os

# Read the current file
with open('linkedin_auth.json', 'r') as f:
    data = json.load(f)
    
# Handle both array format and dict format
if isinstance(data, list):
    # Array format - extract cookies directly
    cookies_data = data
elif isinstance(data, dict) and 'cookies' in data:
    # Already in Playwright format
    cookies_data = data['cookies']
else:
    # Unknown format
    cookies_data = []

# Convert to Playwright format
playwright_cookies = []

for cookie in cookies_data:
    # Convert cookie format
    playwright_cookie = {
        "name": cookie.get("name", ""),
        "value": cookie.get("value", ""),
        "domain": cookie.get("domain", ".linkedin.com"),
        "path": cookie.get("path", "/"),
        "expires": int(cookie.get("expirationDate", -1)) if cookie.get("expirationDate") else -1,
        "httpOnly": cookie.get("httpOnly", False),
        "secure": cookie.get("secure", True),
        "sameSite": "None" if cookie.get("sameSite") in ["no_restriction", "None", "Lax"] else "Lax"
    }
    
    # Only add cookies for LinkedIn domains
    if "linkedin.com" in playwright_cookie["domain"]:
        playwright_cookies.append(playwright_cookie)

# Create Playwright session format
playwright_session = {
    "cookies": playwright_cookies,
    "origins": []
}

# Save back to file
with open('linkedin_auth.json', 'w') as f:
    json.dump(playwright_session, f, indent=2)

print(f"[OK] Converted {len(playwright_cookies)} cookies to Playwright format")
print(f"[OK] Saved to linkedin_auth.json")

# Check for important cookies
important_cookies = ["li_at", "JSESSIONID", "bscookie"]
found = [name for name in important_cookies if any(c.get("name") == name for c in playwright_cookies)]
print(f"[INFO] Important cookies found: {', '.join(found) if found else 'None'}")
if "li_at" in found:
    print("[OK] li_at cookie found - authentication should work!")
else:
    print("[WARNING] li_at cookie not found - authentication may fail")
