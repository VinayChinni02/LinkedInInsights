# LinkedIn Insights Microservice

A microservice for scraping and analyzing LinkedIn company page data. Built with FastAPI, MongoDB, Redis, and Playwright.

## Features

- **Company Page Scraping**: Extract page details, posts, and people from LinkedIn company pages
- **RESTful API**: Complete API with filtering, pagination, and search
- **MongoDB Storage**: Persistent storage with proper relationships
- **Redis Caching**: Fast response times with configurable caching
- **Docker Support**: Complete Docker and Docker Compose setup
- **AI Summaries**: OpenAI-powered company summaries (optional)

## Prerequisites

- Python 3.11+
- MongoDB 7.0+
- Redis 7.0+
- (Optional) OpenAI API key for AI summaries
- (Optional) LinkedIn credentials for full data access

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd deepsolv
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Environment

Create a `.env` file:

```env
# MongoDB
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=linkedin_insights

# Redis
REDIS_URL=redis://localhost:6379
REDIS_TTL=300

# LinkedIn Authentication (Optional - for full data access)
LINKEDIN_EMAIL=your_email@example.com
LINKEDIN_PASSWORD=your_password
# Or use linkedin_auth.json with cookies (see Authentication section)

# OpenAI (Optional)
OPENAI_API_KEY=your_openai_key

# Application
APP_ENV=development
DEBUG=True
```

### 3. Start Services

**Using Docker Compose (Recommended):**

```bash
docker-compose up -d
```

**Manual Setup:**

```bash
# Terminal 1: MongoDB
mongod

# Terminal 2: Redis
redis-server

# Terminal 3: Application
python main.py
```

API will be available at `http://localhost:8000`

## API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

#### Get Page Details
```http
GET /api/v1/pages/{page_id}
```
Scrapes and returns company page data. Auto-scrapes if not in database.

#### Search Pages
```http
GET /api/v1/pages?follower_min=1000&follower_max=5000&industry=Technology&page=1
```
Search and filter pages with pagination.

#### Get Posts
```http
GET /api/v1/pages/{page_id}/posts?limit=15
```
Get recent posts for a company.

#### Get People
```http
GET /api/v1/pages/{page_id}/followers?page=1&page_size=50
```
Get people working at the company.

#### Refresh Page Data
```http
POST /api/v1/pages/{page_id}/refresh
```
Force re-scrape page data.

### Example Requests

```bash
# Get page details
curl http://localhost:8000/api/v1/pages/deepsolv

# Search pages
curl "http://localhost:8000/api/v1/pages?follower_min=20000&industry=Technology"

# Get posts
curl http://localhost:8000/api/v1/pages/deepsolv/posts?limit=20
```

## LinkedIn Authentication

### Option 1: Credentials (Simple)

Add to `.env`:
```env
LINKEDIN_EMAIL=your_email@example.com
LINKEDIN_PASSWORD=your_password
```

**Note**: If 2FA is enabled, you'll need to handle verification codes or use Option 2.

### Option 2: Cookies (Recommended for 2FA)

1. Login to LinkedIn in your browser
2. Export cookies using a browser extension (e.g., "EditThisCookie" or "Cookie Editor")
3. Save as `linkedin_auth.json` in the project root:

```json
{
  "cookies": [
    {
      "name": "li_at",
      "value": "your_li_at_cookie_value",
      "domain": ".linkedin.com",
      "path": "/",
      "expires": 1234567890
    }
  ]
}
```

The scraper will automatically use these cookies if `linkedin_auth.json` exists.

**Security**: Add `linkedin_auth.json` to `.gitignore` to prevent committing credentials.

### Public Access (No Authentication)

The API works without authentication but with limited data:
- ✅ Basic page info (name, URL)
- ⚠️ Limited: description, followers, posts, people may be incomplete

## Database Schema

### Pages Collection
- `page_id`: LinkedIn page ID (unique)
- `name`, `url`, `description`, `website`
- `industry`, `location`, `head_count`
- `total_followers`, `founded`, `company_type`
- `scraped_at`, `updated_at`

### Posts Collection
- `page_id`: Reference to Page
- `content`, `author_name`, `author_profile_url`
- `post_url`, `linkedin_post_id`
- `likes`, `comments_count`, `shares`
- `created_at`, `scraped_at`
- `comments`: Array of embedded comments

### Users Collection (People)
- `page_id`: Reference to Page
- `name`, `profile_url`
- `headline`, `location`
- `current_position`, `connection_count`
- `scraped_at`

## Project Structure

```
deepsolv/
├── app/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Configuration
│   ├── database.py          # MongoDB connection
│   ├── api/
│   │   └── routes.py        # API endpoints
│   ├── models/              # Pydantic models
│   ├── repositories/        # Data access layer
│   ├── services/            # Business logic
│   └── middleware/          # Middleware (caching, error handling)
├── main.py                  # Entry point
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
└── README.md
```

## Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=app tests/
```

## Docker Commands

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f app

# Rebuild after changes
docker-compose up -d --build app

# Stop services
docker-compose down
```

## Configuration

Key environment variables:

- `MONGODB_URL`: MongoDB connection string
- `REDIS_URL`: Redis connection string
- `REDIS_TTL`: Cache TTL in seconds (default: 300)
- `OPENAI_API_KEY`: For AI summaries (optional)
- `LINKEDIN_EMAIL` / `LINKEDIN_PASSWORD`: For full scraping (optional)
- `MAX_POSTS_TO_SCRAPE`: Max posts per page (default: 20)

## Important Notes

1. **LinkedIn Rate Limiting**: The scraper includes rate limiting. Be respectful of LinkedIn's resources.
2. **Anti-Scraping**: LinkedIn has anti-scraping measures. Using authenticated cookies improves success rates.
3. **Data Accuracy**: Some fields may be null due to LinkedIn's dynamic content and access restrictions.
4. **Production**: Consider adding API authentication/authorization for production use.

## Postman Collection

Import `LinkedIn_Insights_API.postman_collection.json` to test all endpoints.

## Troubleshooting

### Scraping fails with authentication errors
- Check LinkedIn credentials in `.env` or `linkedin_auth.json`
- Ensure cookies are not expired
- Try logging in manually and exporting fresh cookies

### Missing data (null values)
- Some fields require authentication for full access
- LinkedIn may limit public data
- Try using authenticated cookies for better results

### Docker issues
- Ensure MongoDB and Redis are accessible
- Check logs: `docker-compose logs app`
- Verify environment variables are set correctly

---

**Status**: ✅ Production Ready
