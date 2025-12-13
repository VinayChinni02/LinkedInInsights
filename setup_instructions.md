# Setup Instructions

## Quick Setup Guide

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Playwright Browsers

```bash
playwright install chromium
```

### 3. Setup Environment Variables

Copy the example environment file and configure it:

```bash
# Create .env file with your configuration
# See README.md for all available options
```

Minimum required:
```env
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=linkedin_insights
REDIS_URL=redis://localhost:6379
```

### 4. Start Services

#### Option A: Docker Compose (Recommended)
```bash
docker-compose up -d
```

#### Option B: Manual
1. Start MongoDB: `mongod`
2. Start Redis: `redis-server`
3. Run app: `python main.py`

### 5. Verify Installation

Visit: http://localhost:8000/docs

## Testing

Run tests:
```bash
pytest
```

## Postman Collection

Import `LinkedIn_Insights_API.postman_collection.json` into Postman.

## Troubleshooting

### MongoDB Connection Issues
- Ensure MongoDB is running: `mongod`
- Check connection string in `.env`

### Redis Connection Issues
- Ensure Redis is running: `redis-server`
- Application will continue without Redis (caching disabled)

### Playwright Issues
- Run: `playwright install chromium`
- For Docker: Already included in Dockerfile

### Scraping Issues
- LinkedIn may block automated scraping
- Consider using LinkedIn's official API for production
- Check network connectivity and LinkedIn access

