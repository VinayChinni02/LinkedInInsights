# Deployment Guide - Public API Access

## 🎯 Quick Answer

**For Deployment:**

✅ **No API key needed for users** - Your API is public, anyone can use it  
✅ **Only server needs LinkedIn credentials** - Add to `.env` on your server  
✅ **LinkedIn API token is OPTIONAL** - Only for enrichment, not required  
✅ **Users just call your API** - No authentication needed

## 📋 What Users Need vs What You Need

### For API Users (Anyone Using Your API):
- ❌ **No API key needed**
- ❌ **No LinkedIn account needed**
- ❌ **No credentials needed**
- ✅ **Just call your API endpoints** - That's it!

### For You (Server Administrator):
- ✅ **Add LinkedIn credentials to `.env`** (one-time setup)
- ⚠️ **LinkedIn API token is OPTIONAL** (only for enrichment)

## 🚀 Deployment Steps

### Step 1: Deploy Your Application

Deploy to your hosting platform (Heroku, AWS, DigitalOcean, etc.):

```bash
# Example: Using Docker
docker-compose up -d

# Or deploy to cloud platform
# (Follow platform-specific deployment instructions)
```

### Step 2: Configure Server Environment Variables

On your server, create/update `.env` file:

```env
# Required for full data scraping
LINKEDIN_EMAIL=your_email@example.com
LINKEDIN_PASSWORD=your_password

# Optional - Only for enrichment (not required)
# LINKEDIN_API_TOKEN=your_api_token_here

# Database & Redis (configure for your deployment)
MONGODB_URL=mongodb://your-mongodb-url
REDIS_URL=redis://your-redis-url

# Other configs...
```

### Step 3: That's It! Your API is Public

Once deployed, anyone can use your API:

```bash
# Example API call (no authentication needed)
curl https://your-api-domain.com/api/v1/pages/atlassian
```

## 🔐 Security Model

### Current Setup (Public API):
```
┌─────────────────┐
│  Any User       │  ← No API key needed
│  (Public)       │  ← No authentication
└────────┬────────┘
         │
         │ GET /api/v1/pages/{page_id}
         │
         ▼
┌─────────────────┐
│  Your Server    │  ← Has LinkedIn credentials in .env
│  (Deployed)     │  ← Handles authentication with LinkedIn
└────────┬────────┘
         │
         │ Uses server's LinkedIn credentials
         │
         ▼
┌─────────────────┐
│  LinkedIn       │
│  (Scraping)     │
└─────────────────┘
```

### What This Means:
- ✅ **Users don't need API keys** - Your API is open/public
- ✅ **Users don't need LinkedIn accounts** - Server handles it
- ✅ **Server credentials are secure** - Stored in `.env` on server
- ⚠️ **No rate limiting** - Consider adding if needed for production

## 🔑 Optional: Add API Authentication (If Needed)

If you want to **restrict access** or **add rate limiting**, you can add API key authentication:

### Option 1: API Key Authentication (Optional)

Add to your FastAPI app:

```python
# app/api/middleware.py
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    valid_keys = ["your-secret-key-1", "your-secret-key-2"]  # Store in env
    if api_key not in valid_keys:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key

# In routes.py
@router.get("/pages/{page_id}")
async def get_page_details(
    page_id: str,
    api_key: str = Security(verify_api_key)  # Add this
):
    # ... your code
```

### Option 2: Rate Limiting (Recommended for Production)

```python
# Add rate limiting middleware
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@router.get("/pages/{page_id}")
@limiter.limit("10/minute")  # 10 requests per minute
async def get_page_details(request: Request, page_id: str):
    # ... your code
```

## 📊 Deployment Checklist

### Required for Deployment:
- [ ] Deploy application to hosting platform
- [ ] Add `LINKEDIN_EMAIL` and `LINKEDIN_PASSWORD` to server `.env`
- [ ] Configure MongoDB (cloud or local)
- [ ] Configure Redis (cloud or local)
- [ ] Test API endpoints work

### Optional Enhancements:
- [ ] Add API key authentication (if you want to restrict access)
- [ ] Add rate limiting (recommended for production)
- [ ] Add monitoring/logging
- [ ] Add `LINKEDIN_API_TOKEN` for enrichment (optional)

## 🌐 Example Deployment Platforms

### Heroku:
```bash
# Add environment variables in Heroku dashboard
heroku config:set LINKEDIN_EMAIL=your_email@example.com
heroku config:set LINKEDIN_PASSWORD=your_password
```

### AWS/DigitalOcean:
```bash
# Add to .env file on server
# Or use platform's environment variable management
```

### Docker:
```bash
# Use docker-compose with .env file
docker-compose up -d
```

## ⚠️ Important Notes for Production

### 1. Rate Limiting
- **Current**: No rate limiting (unlimited requests)
- **Recommendation**: Add rate limiting to prevent abuse
- **Example**: 10-20 requests per minute per IP

### 2. API Authentication (Optional)
- **Current**: Public API (anyone can use)
- **If needed**: Add API key authentication
- **Users would need**: API key to access

### 3. Monitoring
- Monitor API usage
- Track scraping success rates
- Set up alerts for errors

### 4. Cost Considerations
- Scraping uses server resources
- Consider caching to reduce scraping
- Monitor database/Redis usage

## ✅ Summary

**For Deployment:**
1. ✅ Deploy your application
2. ✅ Add LinkedIn credentials to server `.env` (one-time)
3. ✅ **That's it!** - Your API is now public

**For Users:**
- ✅ No API key needed
- ✅ No LinkedIn account needed
- ✅ Just call your API endpoints

**Optional:**
- ⚠️ Add API key authentication (if you want to restrict access)
- ⚠️ Add rate limiting (recommended for production)
- ⚠️ Add LinkedIn API token (for enrichment only)

## 🎉 Your API is Ready!

Once deployed with LinkedIn credentials in `.env`, anyone can use your API:

```bash
# Example: Public API call
GET https://your-api.com/api/v1/pages/atlassian

# Returns full data (posts, comments, people)
# No authentication needed!
```

**Remember**: 
- Server needs LinkedIn credentials (in `.env`)
- Users don't need anything - just call your API! 🚀
