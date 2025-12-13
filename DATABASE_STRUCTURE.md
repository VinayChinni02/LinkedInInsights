# Database Structure and Relationships

## ✅ Yes, We ARE Storing Data in MongoDB with Relationships!

### Database Collections

1. **`pages`** - Main company page data
2. **`posts`** - Company posts (linked to pages)
3. **`comments`** - Comments on posts (linked to posts)
4. **`users`** - People working at companies (linked to pages)

### Relationships Maintained

#### 1. Page → Posts (One-to-Many)
- **Page Model**: `app/models/page.py`
- **Post Model**: `app/models/post.py`
- **Relationship**: `Post.page_id` → `Page._id` (ObjectId reference)
- **Storage**: Posts stored in `posts` collection with `page_id` field

```python
# Post has reference to Page
post_data["page_id"] = page_db_id  # ObjectId reference
await post_repository.create(post_data)
```

#### 2. Post → Comments (One-to-Many)
- **Post Model**: `app/models/post.py`
- **Comment Model**: `app/models/post.py`
- **Relationship**: `Comment.post_id` → `Post._id` (ObjectId reference)
- **Storage**: Comments stored in `comments` collection with `post_id` field

```python
# Comment has reference to Post
comment_data["post_id"] = post.id  # ObjectId reference
await comment_repository.create(comment_data)
```

#### 3. Page → People (One-to-Many)
- **Page Model**: `app/models/page.py`
- **User Model**: `app/models/user.py`
- **Relationship**: `SocialMediaUser.page_id` → `Page._id` (ObjectId reference)
- **Storage**: Users stored in `users` collection with `page_id` field

```python
# User has reference to Page
person_data["page_id"] = page_db_id  # ObjectId reference
await user_repository.create(person_data)
```

### Data Flow

1. **Scrape Page** → Store in `pages` collection
2. **Scrape Posts** → Store in `posts` collection with `page_id` reference
3. **Scrape Comments** → Store in `comments` collection with `post_id` reference
4. **Scrape People** → Store in `users` collection with `page_id` reference

### Querying Relationships

When you fetch a page, the system automatically:
1. Gets the page from `pages` collection
2. Queries `posts` collection for all posts with matching `page_id`
3. For each post, queries `comments` collection for all comments with matching `post_id`
4. Queries `users` collection for all people with matching `page_id`

```python
# In page_service.py
result["posts"] = await self._get_posts_for_page(page.id)
result["people"] = await self._get_people_for_page(page.id)
```

### MongoDB ObjectId References

All relationships use MongoDB's native `ObjectId` type:
- `Page._id` → MongoDB ObjectId
- `Post.page_id` → References `Page._id` (ObjectId)
- `Comment.post_id` → References `Post._id` (ObjectId)
- `SocialMediaUser.page_id` → References `Page._id` (ObjectId)

This ensures:
- ✅ Referential integrity
- ✅ Fast queries with indexes
- ✅ Proper data relationships
- ✅ Easy joins via MongoDB queries

## Why Some Fields Are Still Null

### Possible Reasons:

1. **LinkedIn Authentication Required**
   - Many fields (website, industry, location, specialities) may require authentication
   - LinkedIn shows limited data to unauthenticated users
   - Empty `posts` and `people` arrays often indicate authwall

2. **Data Not Available on Page**
   - Company may not have filled in all fields
   - Some fields might be in different sections (About, Overview, etc.)

3. **HTML Structure Changes**
   - LinkedIn frequently updates their HTML structure
   - Selectors may need updating

4. **Extraction Logic Needs Refinement**
   - Some fields might be in JSON-LD or script tags
   - Need better regex patterns or selectors

### Debugging Null Fields

The scraper now includes debug logging:
- Lists which fields are null
- Shows sample HTML if many fields are null
- Detects LinkedIn authwall
- Logs extraction attempts

Check Docker logs:
```bash
docker-compose logs app | grep -i "null\|debug\|warning"
```

## Next Steps to Fix Null Values

1. **Check Authentication Status**
   - Verify `linkedin_auth.json` has valid cookies
   - Check if `is_authenticated` is `True` in logs

2. **Inspect Actual HTML**
   - Add debug endpoint to see raw HTML
   - Check what LinkedIn actually returns

3. **Improve Selectors**
   - Update CSS selectors based on actual HTML
   - Add more fallback patterns

4. **Use LinkedIn API** (if available)
   - Official API provides structured data
   - More reliable than scraping
