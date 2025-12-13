# LinkedIn Insights Microservice

A robust, scalable microservice for scraping and analyzing LinkedIn company page data. Built with FastAPI, MongoDB, and modern async Python patterns.

## 🎯 Features

### Mandatory Requirements ✅
- **Scraper Service**: Scrapes LinkedIn company pages for:
  - Basic page details (name, URL, ID, profile picture, description, website, industry, followers, head count, specialities)
  - Posts (15-25 posts) with comments
  - People working at the company
- **Database Storage**: MongoDB with proper relationships between entities (Page, Post, Comment, SocialMediaUser)
- **RESTful API**: GET endpoints with:
  - Page details retrieval
  - Filtering by follower count range, name search, industry
  - Get followers/people list
  - Get recent posts (10-15)
  - Pagination support
- **Postman Collection**: Ready-to-use API collection

### Bonus Features 🚀
- **AI Summary**: OpenAI-powered summaries of company pages
- **Asynchronous Programming**: Full async/await implementation for I/O operations
- **Storage Server**: S3 integration for profile pictures and post images
- **Caching**: Redis-based caching with configurable TTL (5 minutes default)
- **Docker Support**: Complete Docker and Docker Compose setup

## 📋 Prerequisites

- Python 3.11+
- MongoDB 7.0+
- Redis 7.0+
- (Optional) AWS S3 account for storage
- (Optional) OpenAI API key for AI summaries

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd deepsolv
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Playwright Browsers

```bash
playwright install chromium
```

### 4. Configure Environment Variables

Create a `.env` file in the root directory:

```env
# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=linkedin_insights

# Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_TTL=300

# OpenAI Configuration (Optional)
OPENAI_API_KEY=your_openai_api_key_here

# AWS S3 Configuration (Optional)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=linkedin-insights-storage

# LinkedIn Authentication (Optional but Recommended for Full Data Access)
# Add your LinkedIn credentials to get all page details, posts, and people
LINKEDIN_EMAIL=your_linkedin_email@example.com
LINKEDIN_PASSWORD=your_linkedin_password

# LinkedIn API (Optional - Alternative to scraping, requires API access)
# Get API token from: https://www.linkedin.com/developers/apps
LINKEDIN_API_TOKEN=your_linkedin_api_token_here

# Application Configuration
APP_ENV=development
DEBUG=True
```

**Important Note on LinkedIn Authentication:**

**Option 1: Without LinkedIn Credentials (Public Access)**
- ✅ Works for anyone using the API
- ✅ Can access basic public data (page name, URL, basic info)
- ⚠️ Limited data: description, followers, industry, posts, and people may not be available
- ✅ Perfect for testing and public API access

**Option 2: With LinkedIn Credentials (Full Access)**
- ✅ Full page description
- ✅ Total followers count
- ✅ Industry, location, specialities
- ✅ Posts (15-25) with comments
- ✅ People working at the company
- ⚠️ Requires adding `LINKEDIN_EMAIL` and `LINKEDIN_PASSWORD` to `.env`
- ⚠️ If you encounter 2FA or captcha, you may need to handle them manually

**For Public API Access:**
- The API works without credentials - users can access it without login
- Data will be limited to what's publicly available on LinkedIn
- For full data, the API administrator can add LinkedIn credentials to the server's `.env` file
- Users don't need to provide their own credentials - it's a server-side configuration

### 5. Start Services

#### Option A: Using Docker Compose (Recommended)

```bash
docker-compose up -d
```

This will start:
- MongoDB on port 27017
- Redis on port 6379
- Application on port 8000

#### Option B: Manual Setup

1. Start MongoDB:
```bash
mongod
```

2. Start Redis:
```bash
redis-server
```

3. Run the application:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

## 📚 API Documentation

### Interactive API Docs

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### API Endpoints

#### 1. Get Page Details
```http
GET /api/v1/pages/{page_id}
```

Get details of a LinkedIn page. If the page doesn't exist in the database, it will be scraped automatically.

**Parameters:**
- `page_id` (path): LinkedIn page ID (e.g., "deepsolv")
- `force_refresh` (query, optional): Force re-scraping (default: false)

**Example:**
```bash
curl http://localhost:8000/api/v1/pages/deepsolv
```

#### 2. Search Pages
```http
GET /api/v1/pages
```

Search and filter pages with pagination.

**Query Parameters:**
- `follower_min` (optional): Minimum follower count
- `follower_max` (optional): Maximum follower count
- `name_search` (optional): Search by page name (partial match)
- `industry` (optional): Filter by industry
- `page` (default: 1): Page number
- `page_size` (default: 10, max: 100): Items per page

**Example:**
```bash
curl "http://localhost:8000/api/v1/pages?follower_min=20000&follower_max=40000&page=1&page_size=10"
```

#### 3. Get Page Followers/People
```http
GET /api/v1/pages/{page_id}/followers
```

Get list of people working at a page.

**Parameters:**
- `page_id` (path): LinkedIn page ID
- `page` (query, default: 1): Page number
- `page_size` (query, default: 50, max: 100): Items per page

**Example:**
```bash
curl http://localhost:8000/api/v1/pages/deepsolv/followers?page=1&page_size=50
```

#### 4. Get Page Posts
```http
GET /api/v1/pages/{page_id}/posts
```

Get recent posts of a page.

**Parameters:**
- `page_id` (path): LinkedIn page ID
- `limit` (query, default: 15, max: 25): Number of posts to retrieve

**Example:**
```bash
curl http://localhost:8000/api/v1/pages/deepsolv/posts?limit=15
```

#### 5. Refresh Page Data
```http
POST /api/v1/pages/{page_id}/refresh
```

Force refresh page data by re-scraping.

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/pages/deepsolv/refresh
```

#### 6. Health Check
```http
GET /api/v1/health
```

Check service health status.

## 🏗️ Project Structure

```
deepsolv/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration settings
│   ├── database.py             # MongoDB connection
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py           # API endpoints
│   ├── models/
│   │   ├── __init__.py
│   │   ├── page.py             # Page model
│   │   ├── post.py             # Post and Comment models
│   │   └── user.py               # SocialMediaUser model
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── page_repository.py  # Page database operations
│   │   ├── post_repository.py  # Post database operations
│   │   └── user_repository.py  # User database operations
│   └── services/
│       ├── __init__.py
│       ├── scraper_service.py  # LinkedIn scraper
│       ├── cache_service.py    # Redis caching
│       ├── ai_service.py       # AI summary generation
│       ├── storage_service.py  # S3 storage
│       └── page_service.py     # Page business logic
├── tests/
│   ├── __init__.py
│   └── test_api.py             # API tests
├── main.py                     # Application entry point
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker configuration
├── docker-compose.yml          # Docker Compose setup
├── pytest.ini                 # Pytest configuration
└── README.md                   # This file
```

## 🧪 Testing

Run tests using pytest:

```bash
pytest
```

Or with coverage:

```bash
pytest --cov=app tests/
```

## 🐳 Docker

### Build Docker Image

```bash
docker build -t linkedin-insights .
```

### Run with Docker Compose

```bash
docker-compose up -d
```

### View Logs

```bash
docker-compose logs -f app
```

## 🔧 Configuration

All configuration is managed through environment variables (see `.env.example`). Key settings:

- **MONGODB_URL**: MongoDB connection string
- **REDIS_URL**: Redis connection string
- **REDIS_TTL**: Cache TTL in seconds (default: 300)
- **OPENAI_API_KEY**: For AI summaries (optional)
- **S3_BUCKET_NAME**: For image storage (optional)
- **MAX_POSTS_TO_SCRAPE**: Maximum posts to scrape (default: 20)

## 📊 Database Schema

### Page Collection
- `_id`: MongoDB ObjectId
- `page_id`: LinkedIn page ID (unique)
- `name`: Page name
- `url`: Full LinkedIn URL
- `linkedin_id`: LinkedIn platform ID
- `profile_picture`: Profile picture URL
- `description`: Page description
- `website`: Company website
- `industry`: Industry
- `total_followers`: Follower count
- `head_count`: Employee count range
- `specialities`: List of specialities
- `scraped_at`: Scraping timestamp
- `updated_at`: Last update timestamp

### Post Collection
- `_id`: MongoDB ObjectId
- `page_id`: Reference to Page
- `content`: Post content
- `likes`: Like count
- `comments_count`: Comment count
- `shares`: Share count
- `post_url`: Post URL
- `image_url`: Post image URL
- `created_at`: Post creation date
- `comments`: Embedded comments array

### User Collection
- `_id`: MongoDB ObjectId
- `page_id`: Reference to Page
- `name`: User name
- `profile_url`: LinkedIn profile URL
- `headline`: User headline
- `current_position`: Current position
- `location`: User location

## 🎨 Design Patterns

This project follows:
- **Repository Pattern**: Data access abstraction
- **Service Layer**: Business logic separation
- **Dependency Injection**: Loose coupling
- **SOLID Principles**: Clean, maintainable code
- **RESTful API Design**: Standard HTTP methods and status codes

## ⚠️ Important Notes

1. **LinkedIn Scraping**: LinkedIn may have anti-scraping measures. The scraper uses Playwright with headless browser. For production, consider:
   - Using LinkedIn's official API
   - Implementing rate limiting
   - Adding proxy rotation
   - Respecting robots.txt

2. **Rate Limiting**: Consider implementing rate limiting for production use.

3. **Authentication**: Currently, the API is open. For production, add authentication/authorization.

4. **Error Handling**: Comprehensive error handling is implemented, but monitor logs for scraping failures.

## 📝 Postman Collection

Import the `LinkedIn_Insights_API.postman_collection.json` file into Postman to test all endpoints.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is part of a GenAI Developer Intern assignment.

## 👤 Author

Developed as part of the GenAI Developer Intern assignment.

---

**Status**: ✅ All mandatory requirements completed
**Bonus Features**: ✅ AI Summary, Async Programming, Storage Server, Caching, Docker

