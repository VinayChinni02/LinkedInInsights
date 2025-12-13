# Docker + Email Verification Solution

## 🔐 Problem

You're running in Docker (headless mode) and got a verification code, but can't enter it because there's no visible browser.

## ✅ Solution: Run Locally First, Then Use Saved Session

### Step 1: Run Locally (Not in Docker) for First Login

1. **Stop Docker**:
   ```bash
   docker-compose down
   ```

2. **Run locally** (so you can see the browser):
   ```bash
   # Make sure MongoDB and Redis are running
   # Then run:
   python main.py
   ```

3. **Watch for login prompt** - A browser window will open
4. **Enter verification code** when prompted
5. **Session saved** - Creates `linkedin_auth.json` file

### Step 2: Copy Session File to Docker

After successful login locally:

1. **Copy the session file**:
   ```bash
   # The file linkedin_auth.json should be in your project root
   # It will be automatically used by Docker
   ```

2. **Restart Docker**:
   ```bash
   docker-compose up -d
   ```

3. **Docker will use the saved session** - No more verification needed!

## 🚀 Alternative: Use Browser Extension to Export Cookies

If you've already logged into LinkedIn in your regular browser:

### Step 1: Export Cookies from Browser

1. **Install a cookie export extension** (e.g., "Cookie-Editor" for Chrome/Firefox)
2. **Go to linkedin.com** and make sure you're logged in
3. **Export cookies** as JSON
4. **Save as** `linkedin_auth.json` in your project root

### Step 2: Format for Playwright

The JSON should have this structure:
```json
{
  "cookies": [
    {
      "name": "li_at",
      "value": "your_cookie_value",
      "domain": ".linkedin.com",
      "path": "/",
      "expires": -1,
      "httpOnly": true,
      "secure": true,
      "sameSite": "None"
    }
  ],
  "origins": []
}
```

### Step 3: Use in Docker

1. **Place `linkedin_auth.json` in project root**
2. **Restart Docker**:
   ```bash
   docker-compose restart app
   ```

## 📋 Quick Steps (Recommended)

**Easiest approach:**

1. **Stop Docker**: `docker-compose down`
2. **Run locally**: `python main.py` (browser will open)
3. **Enter verification code** when browser shows it
4. **Wait for**: `[OK] LinkedIn login successful after verification!`
5. **Check**: `linkedin_auth.json` file is created
6. **Start Docker**: `docker-compose up -d`
7. **Done!** Docker will use saved session

## 🔍 Verify Session File Exists

After local login, check:
```bash
ls linkedin_auth.json
# OR
dir linkedin_auth.json
```

If the file exists, Docker will automatically use it!

## ⚠️ Important Notes

- **Session expires**: LinkedIn sessions typically last 30-60 days
- **If expired**: Repeat the local login process
- **File location**: `linkedin_auth.json` must be in project root (same folder as `main.py`)

## 🎯 Current Status

Your verification code is ready - you just need to:
1. Run locally (not Docker) to enter it
2. Save the session
3. Use saved session in Docker

**The session file will work in Docker automatically!**
