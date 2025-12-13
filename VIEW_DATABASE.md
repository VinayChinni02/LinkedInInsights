# How to View Your MongoDB Database

## Database Information
- **Database Name**: `linkedin_insights`
- **MongoDB Port**: `27017` (exposed on localhost)
- **Collections**: `pages`, `posts`, `comments`, `users`

---

## Method 1: MongoDB Compass (GUI - Easiest) ⭐ RECOMMENDED

### Install MongoDB Compass
1. Download from: https://www.mongodb.com/try/download/compass
2. Install the application

### Connect
1. Open MongoDB Compass
2. Connection String: `mongodb://localhost:27017`
3. Click "Connect"
4. Select database: `linkedin_insights`
5. Browse collections: `pages`, `posts`, `comments`, `users`

### View Data
- Click on any collection to see documents
- Use filters to search
- View relationships (page_id references)

---

## Method 2: Command Line (mongosh)

### Access MongoDB Shell
```bash
# Connect to MongoDB container
docker exec -it deepsolv-mongodb-1 mongosh

# Or if mongosh is installed locally
mongosh mongodb://localhost:27017
```

### Useful Commands
```javascript
// Switch to database
use linkedin_insights

// Show all collections
show collections

// View all pages
db.pages.find().pretty()

// View all posts
db.posts.find().pretty()

// View all users/people
db.users.find().pretty()

// View all comments
db.comments.find().pretty()

// Count documents
db.pages.countDocuments()
db.posts.countDocuments()
db.users.countDocuments()
db.comments.countDocuments()

// Find specific page
db.pages.findOne({ page_id: "ocecas-mitblr" })

// Find posts for a page (by page_id ObjectId)
db.posts.find({ page_id: ObjectId("693d8980c17807f3b77ae686") }).pretty()

// Find people for a page
db.users.find({ page_id: ObjectId("693d8980c17807f3b77ae686") }).pretty()

// Find comments for a post
db.comments.find({ post_id: ObjectId("...") }).pretty()
```

---

## Method 3: Python Script (View Data Programmatically)

Run the provided script:
```bash
python view_database.py
```

This will show:
- All pages with their data
- Posts linked to each page
- People linked to each page
- Comments linked to each post

---

## Method 4: API Endpoints

### View All Pages
```
GET http://localhost:8000/api/v1/pages
```

### View Specific Page (with relationships)
```
GET http://localhost:8000/api/v1/pages/ocecas-mitblr
```

This returns:
- Page data
- All posts (with comments)
- All people

---

## Method 5: Quick Database Stats Script

Run:
```bash
python database_stats.py
```

Shows:
- Total pages, posts, users, comments
- Sample data from each collection
- Relationship counts

---

## Troubleshooting

### Can't Connect?
1. Check if MongoDB is running:
   ```bash
   docker-compose ps
   ```

2. Check MongoDB logs:
   ```bash
   docker-compose logs mongodb
   ```

3. Verify port is exposed:
   ```bash
   netstat -an | findstr 27017
   ```

### Empty Collections?
- Data is only stored after scraping
- Make an API request first: `GET /api/v1/pages/{page_id}?force_refresh=true`
- Check if scraping was successful in logs
