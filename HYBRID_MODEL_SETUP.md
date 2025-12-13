# Hybrid Model Setup Guide

## 🎯 What is the Hybrid Model?

Our system uses **two data sources** working together:

1. **Web Scraping (Primary)** - Gets ALL data including posts, comments, and people
2. **LinkedIn API (Enrichment)** - Fills in missing basic company information

## 📋 Configuration Steps

### Step 1: Create/Update `.env` File

Create a `.env` file in the root directory with the following:

```env
# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=linkedin_insights

# Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_TTL=300

# LinkedIn Authentication (REQUIRED for full data)
# This enables scraping to get posts, comments, and people
LINKEDIN_EMAIL=your_linkedin_email@example.com
LINKEDIN_PASSWORD=your_linkedin_password

# LinkedIn API (OPTIONAL - for enrichment only)
# Get API token from: https://www.linkedin.com/developers/apps
# This only enriches basic company info, cannot get posts/people
LINKEDIN_API_TOKEN=your_linkedin_api_token_here

# OpenAI Configuration (Optional)
OPENAI_API_KEY=your_openai_api_key_here

# AWS S3 Configuration (Optional)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=linkedin-insights-storage

# Application Configuration
APP_ENV=development
DEBUG=True
```

### Step 2: Required vs Optional

#### ✅ REQUIRED for Full Data:
- `LINKEDIN_EMAIL` + `LINKEDIN_PASSWORD` 
  - **Why**: Enables scraping to get posts (15-25), comments, and people
  - **Without this**: You'll only get limited public data

#### ⚠️ OPTIONAL (Enrichment Only):
- `LINKEDIN_API_TOKEN`
  - **Why**: Can enrich basic company info (name, description, followers)
  - **Limitation**: Cannot get posts, comments, or people
  - **Note**: Requires LinkedIn Developer App approval

## 🔄 How It Works

### Data Flow:

```
1. User requests page data
   ↓
2. Scraper extracts data (posts, comments, people, basic info)
   ↓
3. LinkedIn API enriches missing basic fields (if token provided)
   ↓
4. Combined data returned to user
```

### Example:

**With Scraping Only:**
- ✅ Gets: Page details, 15-25 posts, comments, people
- ✅ Full assignment requirements met

**With Scraping + API:**
- ✅ Gets: Page details, 15-25 posts, comments, people
- ✅ Plus: API-verified follower counts, enriched descriptions
- ✅ Best of both worlds

## 🚀 Testing the Hybrid Model

### 1. Start the Application

```bash
# Using Docker (Recommended)
docker-compose up -d

# Or manually
python main.py
```

### 2. Test API Endpoint

```bash
# Get page details with force refresh
curl "http://localhost:8000/api/v1/pages/atlassian?force_refresh=true"
```

### 3. Check Logs

Look for these messages in the logs:

**Successful Scraping:**
```
[OK] Scraper service initialized
[INFO] Successfully extracted 20 posts for atlassian
[INFO] Successfully extracted 45 people for atlassian
```

**API Enrichment (if token provided):**
```
[OK] LinkedIn API service initialized
[INFO] Enriched atlassian data with LinkedIn API
```

**Without Credentials:**
```
[WARNING] Limited data extracted. For full data (description, followers, posts, people), configure LinkedIn authentication.
```

## 📊 What Data You'll Get

### With LinkedIn Credentials (Scraping):

| Data Type | Available | Source |
|-----------|-----------|--------|
| Page Name | ✅ | Scraping |
| Description | ✅ | Scraping |
| Website | ✅ | Scraping |
| Industry | ✅ | Scraping |
| Followers | ✅ | Scraping |
| Location | ✅ | Scraping |
| **Posts (15-25)** | ✅ | **Scraping Only** |
| **Post Comments** | ✅ | **Scraping Only** |
| **People/Employees** | ✅ | **Scraping Only** |

### With API Token (Additional Enrichment):

- Can verify/enrich follower counts
- Can enrich descriptions (if admin access)
- Can enrich basic company info

## ⚠️ Important Notes

1. **Scraping is Mandatory**: You MUST have `LINKEDIN_EMAIL` and `LINKEDIN_PASSWORD` to get posts, comments, and people.

2. **API is Optional**: The API token only enriches basic info. It cannot replace scraping.

3. **2FA/Captcha**: If LinkedIn requires 2FA or captcha, you may need to handle it manually or use a session cookie.

4. **Rate Limiting**: Be respectful with scraping. Don't make too many requests too quickly.

## 🐛 Troubleshooting

### Issue: "Limited data extracted"
**Solution**: Add `LINKEDIN_EMAIL` and `LINKEDIN_PASSWORD` to `.env` and restart.

### Issue: "LinkedIn API access denied"
**Solution**: 
- Check if your API token is valid
- Verify you have the right permissions
- API is optional - scraping will still work

### Issue: "Scraper service initialization failed"
**Solution**:
- Check Playwright is installed: `playwright install chromium`
- On Windows, ensure Python 3.10-3.12 (not 3.13)
- Or use Docker which handles this automatically

## ✅ Success Checklist

- [ ] `.env` file created with `LINKEDIN_EMAIL` and `LINKEDIN_PASSWORD`
- [ ] Application starts without errors
- [ ] Logs show "Scraper service initialized"
- [ ] API endpoint returns data with posts and people
- [ ] (Optional) API token added for enrichment

## 🎉 You're Ready!

Once configured, the hybrid model will:
1. Scrape all required data (posts, comments, people)
2. Enrich with API data when available
3. Return complete data for your assignment

Happy scraping! 🚀
