"""
Helper script to create linkedin_auth.json from browser cookies.
Run this script and follow the prompts.
"""
import json
import os

print("=" * 60)
print("LinkedIn Cookie Exporter for Playwright")
print("=" * 60)
print()

print("Option 1: Manual Entry")
print("Option 2: From Cookie-Editor Extension JSON")
print()

choice = input("Choose option (1 or 2): ").strip()

cookies = []

if choice == "1":
    print("\n--- Manual Cookie Entry ---")
    print("Open your browser, go to linkedin.com, and:")
    print("1. Press F12 to open Developer Tools")
    print("2. Go to Application/Storage → Cookies → https://www.linkedin.com")
    print("3. Find the 'li_at' cookie value")
    print()
    
    li_at = input("Enter 'li_at' cookie value: ").strip()
    
    if li_at:
        cookies.append({
            "name": "li_at",
            "value": li_at,
            "domain": ".linkedin.com",
            "path": "/",
            "expires": -1,
            "httpOnly": True,
            "secure": True,
            "sameSite": "None"
        })
    
    jsessionid = input("Enter 'JSESSIONID' cookie value (optional, press Enter to skip): ").strip()
    if jsessionid:
        cookies.append({
            "name": "JSESSIONID",
            "value": jsessionid,
            "domain": ".linkedin.com",
            "path": "/",
            "expires": -1,
            "httpOnly": True,
            "secure": True,
            "sameSite": "None"
        })

elif choice == "2":
    print("\n--- From Cookie-Editor Extension ---")
    print("1. Install Cookie-Editor extension in your browser")
    print("2. Go to linkedin.com and make sure you're logged in")
    print("3. Click Cookie-Editor icon → Export → JSON")
    print("4. Paste the JSON below (press Enter, then Ctrl+Z, then Enter to finish):")
    print()
    
    lines = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass
    
    json_text = "\n".join(lines)
    
    try:
        exported_data = json.loads(json_text)
        
        # Handle different export formats
        if isinstance(exported_data, list):
            # List of cookies
            for cookie in exported_data:
                if cookie.get("domain") and "linkedin.com" in cookie.get("domain", ""):
                    cookies.append({
                        "name": cookie.get("name", ""),
                        "value": cookie.get("value", ""),
                        "domain": cookie.get("domain", ".linkedin.com"),
                        "path": cookie.get("path", "/"),
                        "expires": cookie.get("expires", -1),
                        "httpOnly": cookie.get("httpOnly", True),
                        "secure": cookie.get("secure", True),
                        "sameSite": cookie.get("sameSite", "None")
                    })
        elif isinstance(exported_data, dict):
            # Object with cookies array
            if "cookies" in exported_data:
                for cookie in exported_data["cookies"]:
                    if cookie.get("domain") and "linkedin.com" in cookie.get("domain", ""):
                        cookies.append({
                            "name": cookie.get("name", ""),
                            "value": cookie.get("value", ""),
                            "domain": cookie.get("domain", ".linkedin.com"),
                            "path": cookie.get("path", "/"),
                            "expires": cookie.get("expires", -1),
                            "httpOnly": cookie.get("httpOnly", True),
                            "secure": cookie.get("secure", True),
                            "sameSite": cookie.get("sameSite", "None")
                        })
    except json.JSONDecodeError:
        print("Error: Invalid JSON. Please try again.")
        exit(1)

else:
    print("Invalid choice. Exiting.")
    exit(1)

if not cookies:
    print("\nError: No cookies found. Please try again.")
    exit(1)

# Create Playwright-compatible format
playwright_session = {
    "cookies": cookies,
    "origins": []
}

# Save to file
output_file = "linkedin_auth.json"
with open(output_file, 'w') as f:
    json.dump(playwright_session, f, indent=2)

print(f"\n✅ Success! Created {output_file}")
print(f"📁 Location: {os.path.abspath(output_file)}")
print(f"🍪 Found {len(cookies)} cookie(s)")
print("\n🚀 Next steps:")
print("1. Start Docker: docker-compose up -d")
print("2. Docker will automatically use this session!")
print("\n✅ No more verification codes needed!")
