# Where to Enter LinkedIn Verification Code

## ❌ Problem: You're in Docker (Headless Mode)

**You CANNOT enter the verification code in Docker** because:
- Docker runs in headless mode (no visible browser)
- There's no UI to interact with
- The browser is invisible

## ✅ Solution: Two Options

### Option 1: Export Fresh Cookies (RECOMMENDED - Easiest)

Since you can't enter the code in Docker, export fresh cookies from your regular browser:

1. **Open your regular browser** (Chrome/Edge/Firefox)
2. **Log in to LinkedIn manually** (enter your email, password, and verification code)
3. **Install "Cookie-Editor" extension** (if not already installed)
4. **Go to linkedin.com** (make sure you're logged in)
5. **Open Cookie-Editor extension**
6. **Click "Export" → "JSON"**
7. **Copy all the JSON**
8. **Paste into `linkedin_auth.json`** (replace the entire file content)
9. **Restart Docker**: `docker-compose restart app`

**That's it!** Docker will use your fresh cookies and won't need to login.

---

### Option 2: Run Locally First (Then Use in Docker)

If you want to complete verification programmatically:

1. **Stop Docker**:
   ```bash
   docker-compose down
   ```

2. **Run locally** (so you can see the browser):
   ```bash
   python main.py
   ```

3. **A browser window will open** - you'll see the login page
4. **Enter your email and password**
5. **When verification code prompt appears**, enter the code from your email
6. **Wait for**: `[OK] LinkedIn login successful after verification!`
7. **Check**: `linkedin_auth.json` file is created/updated
8. **Start Docker**: `docker-compose up -d`
9. **Docker will use the saved session**

---

## 🎯 Quick Answer

**You can't enter the verification code in Docker.**

**Best solution**: Export fresh cookies from your browser after logging in manually, then paste them into `linkedin_auth.json`.

---

## 📋 Step-by-Step: Export Cookies

1. Open Chrome/Edge/Firefox
2. Go to https://www.linkedin.com
3. Log in manually (enter email, password, verification code)
4. Install "Cookie-Editor" extension:
   - Chrome: https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm
   - Firefox: https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/
5. Click the Cookie-Editor icon
6. Click "Export" button
7. Select "JSON" format
8. Copy all the JSON text
9. Open `linkedin_auth.json` in your project
10. Replace entire file content with the copied JSON
11. Save the file
12. Restart Docker: `docker-compose restart app`

---

## ✅ Verify It Worked

After updating cookies, check logs:
```bash
docker-compose logs app | grep -i "cookie\|login\|authenticated"
```

You should see:
- `[INFO] Found saved LinkedIn session, validating cookies...`
- `[OK] LinkedIn session cookies are valid`

If you see errors, the cookies might be expired - export fresh ones!
