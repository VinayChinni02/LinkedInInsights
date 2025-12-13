# Export LinkedIn Cookies for Docker

## 🎯 Quick Solution

Since you're using Python 3.13 (Playwright doesn't work) and Docker is headless, export cookies from your regular browser.

## ✅ Step-by-Step

### Method 1: Using Browser Extension (Easiest)

1. **Install Cookie-Editor Extension**:
   - Chrome: https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm
   - Firefox: https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/

2. **Login to LinkedIn** in your regular browser:
   - Go to https://www.linkedin.com
   - Make sure you're logged in
   - Complete any verification if needed

3. **Export Cookies**:
   - Click the Cookie-Editor extension icon
   - Click "Export" button
   - Select "JSON" format
   - Copy the JSON

4. **Save as `linkedin_auth.json`**:
   - Create file: `linkedin_auth.json` in project root
   - Paste the JSON, but we need to format it for Playwright

5. **Format for Playwright**:
   The file should look like this:
   ```json
   {
     "cookies": [
       {
         "name": "li_at",
         "value": "YOUR_COOKIE_VALUE_HERE",
         "domain": ".linkedin.com",
         "path": "/",
         "expires": -1,
         "httpOnly": true,
         "secure": true,
         "sameSite": "None"
       },
       {
         "name": "JSESSIONID",
         "value": "YOUR_JSESSIONID_VALUE",
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

### Method 2: Manual Cookie Extraction

1. **Open LinkedIn** in your browser
2. **Open Developer Tools** (F12)
3. **Go to Application/Storage tab** → Cookies → https://www.linkedin.com
4. **Find these cookies**:
   - `li_at` (most important - authentication cookie)
   - `JSESSIONID`
5. **Create `linkedin_auth.json`** with the format above

## 🔧 Quick Script to Help

I'll create a helper script to format cookies correctly.

## 📋 After Exporting

1. **Place `linkedin_auth.json` in project root** (same folder as `main.py`)
2. **Start Docker**:
   ```bash
   docker-compose up -d
   ```
3. **Docker will automatically use the saved session!**

## ✅ Verify It Works

After starting Docker, check logs:
```bash
docker-compose logs -f app
```

You should see:
```
[INFO] Found saved LinkedIn session, attempting to use it...
[OK] LinkedIn login successful
```

No more verification needed!
