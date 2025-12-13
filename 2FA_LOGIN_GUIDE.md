# Handling LinkedIn 2FA/Email Verification

## 🔐 Problem

LinkedIn is sending verification codes to your email, which the automated scraper can't handle automatically.

## ✅ Solutions

### Solution 1: Manual Verification (Recommended - Easiest)

The scraper now **waits for you to complete verification manually**:

1. **Start the application** - The scraper will attempt login
2. **Check your email** - LinkedIn sends a verification code
3. **Enter the code** - The scraper will wait up to 2 minutes for you to:
   - Open the browser (if not headless)
   - Enter the verification code from your email
   - Complete the verification
4. **Session saved** - Once verified, the session is saved to `linkedin_auth.json`
5. **Future logins** - The saved session will be reused (no more 2FA needed!)

**Note**: If running in Docker or headless mode, you may need to use Solution 2 or 3.

### Solution 2: Use Saved Session Cookies

If you've already logged in manually in a browser:

1. **Export cookies** from your browser (using a browser extension)
2. **Save as JSON** in the format Playwright expects
3. **Place in project root** as `linkedin_auth.json`
4. **Restart application** - It will use the saved session

### Solution 3: Run in Non-Headless Mode (For Manual Verification)

Modify the scraper to run with a visible browser so you can enter the code:

```python
# In scraper_service.py, change:
headless=True  # to False
```

Then you can see the browser and enter the verification code manually.

### Solution 4: Temporarily Disable 2FA (Not Recommended)

1. Go to LinkedIn Settings → Security
2. Temporarily disable 2FA
3. Run the scraper
4. Re-enable 2FA after

⚠️ **Security Risk**: Only do this if you understand the risks.

## 🚀 Quick Start (Recommended Approach)

### Step 1: Run Application

```bash
python main.py
# OR
docker-compose up
```

### Step 2: Watch the Logs

You'll see:
```
[INFO] Attempting LinkedIn login...
[INFO] LinkedIn requires email verification/2FA
[INFO] Please check your email for the verification code
[INFO] Waiting up to 2 minutes for manual verification...
```

### Step 3: Complete Verification

1. Check your email for the LinkedIn verification code
2. If browser is visible: Enter the code in the browser
3. If headless: The scraper will wait, but you may need to use Solution 2

### Step 4: Session Saved

Once verified, you'll see:
```
[OK] LinkedIn login successful after verification!
```

The session is saved to `linkedin_auth.json` and will be reused next time!

## 📋 What Happens Next Time?

After the first successful login with verification:
- Session is saved to `linkedin_auth.json`
- Next time you start the app, it will try to use the saved session
- **No more 2FA needed** (until the session expires)

## 🔧 Troubleshooting

### Issue: "Email verification timeout"

**Solution**: 
- The 2-minute wait period expired
- Try again, or use Solution 2 (saved cookies)

### Issue: "Still on login page"

**Solution**:
- Credentials might be incorrect
- Check your `.env` file
- Try logging in manually in a browser first

### Issue: Running in Docker (Can't see browser)

**Solution**:
- Use Solution 2 (saved session cookies)
- Or temporarily run locally (not in Docker) to complete first verification

## 💡 Best Practice

1. **First time**: Complete verification manually (Solution 1)
2. **Session saved**: `linkedin_auth.json` is created
3. **Future runs**: Use saved session automatically
4. **If session expires**: Repeat step 1

## 🎯 Current Status

The scraper now:
- ✅ Detects 2FA/email verification
- ✅ Waits up to 2 minutes for manual completion
- ✅ Saves session after successful verification
- ✅ Reuses saved session on next startup

**Try running the application now - it will wait for you to complete verification!**
