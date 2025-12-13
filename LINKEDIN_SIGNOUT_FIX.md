# LinkedIn Auto Sign-Out Fix

## 🔐 Problem: LinkedIn Signs You Out Automatically

When you export cookies and use them in the scraper, LinkedIn detects that the cookies are being used from a different browser/environment and automatically signs you out as a security measure.

**Why this happens:**
- LinkedIn detects browser fingerprint differences (Playwright vs your regular browser)
- Different user agent, screen resolution, plugins, etc.
- LinkedIn sees this as suspicious activity and logs you out

## ✅ Solutions

### Solution 1: Use a Dedicated LinkedIn Account (RECOMMENDED)

**Best practice for production:**
1. Create a separate LinkedIn account specifically for scraping
2. Use that account's cookies in your scraper
3. Your personal account won't be affected

**Benefits:**
- Your personal account stays safe
- No risk of account restrictions
- Can scrape without worrying about sign-outs

---

### Solution 2: Improved Stealth Mode (Already Implemented)

I've updated the scraper with better stealth features:
- ✅ Hidden webdriver properties
- ✅ Realistic browser fingerprint
- ✅ Better user agent and headers
- ✅ JavaScript injection to hide automation

**This should reduce (but not eliminate) sign-out issues.**

---

### Solution 3: Use Cookies Immediately After Export

**Timing matters:**
1. Export cookies from your browser
2. **Immediately** paste them into `linkedin_auth.json`
3. **Immediately** restart Docker
4. Use the scraper right away

**Why:** Fresh cookies are less likely to trigger security checks.

---

### Solution 4: Reduce Scraping Frequency

**If you're scraping too often:**
- Add delays between requests
- Don't scrape the same page repeatedly
- Space out your scraping sessions

**LinkedIn may sign you out if:**
- Too many requests in short time
- Unusual access patterns
- Rapid page navigation

---

### Solution 5: Accept Occasional Re-authentication

**For development/testing:**
- Export fresh cookies when needed
- Accept that you may need to re-export occasionally
- This is normal with LinkedIn's security

---

## 🛡️ What I've Fixed

The scraper now includes:
1. **Stealth browser arguments** - Makes Playwright look more like a real browser
2. **JavaScript injection** - Hides automation indicators
3. **Realistic headers** - Matches real browser requests
4. **Better fingerprinting** - Reduces detection

---

## 📋 Best Practices

1. **Use a dedicated account** for scraping (most important!)
2. **Export fresh cookies** when they expire
3. **Don't scrape too frequently** - add delays
4. **Monitor your account** - check if you're signed out
5. **Keep cookies updated** - re-export when needed

---

## ⚠️ Important Notes

- **LinkedIn's security is aggressive** - some sign-outs are unavoidable
- **This is normal behavior** - LinkedIn protects user accounts
- **Dedicated account is best** - protects your personal account
- **Cookies expire** - you'll need to refresh them periodically

---

## 🔄 If You Get Signed Out

1. **Don't panic** - this is normal
2. **Re-export cookies** from your browser
3. **Update `linkedin_auth.json`**
4. **Restart Docker**
5. **Continue scraping**

The improved stealth mode should reduce sign-outs, but they may still happen occasionally due to LinkedIn's security measures.
