# How to Add Reviews to Production

## Method 1: Admin Panel (Recommended for Single Reviews)

### Step 1: Login as Admin
Navigate to: `https://www.visionary-suite.com/login`
Use admin credentials to login.

### Step 2: Access Admin Panel
Navigate to: `https://www.visionary-suite.com/app/admin`

### Step 3: Manage Reviews
- Go to Reviews section
- View pending reviews that users have submitted
- Approve or reject reviews

### API Endpoints (for Admin):
```bash
# Get pending reviews
GET /api/reviews/admin/pending

# Approve a review
POST /api/reviews/admin/{review_id}/approve
Body: {"approved": true}

# Seed a single review
POST /api/reviews/admin/seed
Body: {"name": "...", "role": "...", "rating": 5, "message": "..."}

# Bulk seed default reviews (5 reviews)
POST /api/reviews/admin/seed-bulk
```

---

## Method 2: Direct Database Seed Script

### MongoDB Shell Script
```javascript
// Connect to production MongoDB and run:
use creatorstudio_production

db.user_reviews.insertMany([
  {
    id: UUID().toString(),
    name: "Sarah Johnson",
    role: "Content Creator", 
    rating: 5,
    message: "Visionary Suite has completely transformed how I create content. The AI-powered tools are intuitive and the results are amazing!",
    approved: true,
    seeded: true,
    createdAt: "2026-02-15T10:30:00Z",
    updatedAt: new Date().toISOString()
  },
  {
    id: UUID().toString(),
    name: "Michael Chen",
    role: "Digital Marketer",
    rating: 5,
    message: "The Story Video Studio feature is a game-changer. I can create professional videos from simple text stories in minutes.",
    approved: true,
    seeded: true,
    createdAt: "2026-02-20T14:15:00Z",
    updatedAt: new Date().toISOString()
  },
  {
    id: UUID().toString(),
    name: "Emma Davis",
    role: "Author",
    rating: 5,
    message: "I use the Kids Story Pack feature for my storytelling channel. The illustrations are beautiful and my audience loves the content.",
    approved: true,
    seeded: true,
    createdAt: "2026-02-25T08:45:00Z",
    updatedAt: new Date().toISOString()
  },
  {
    id: UUID().toString(),
    name: "James Wilson",
    role: "Social Media Manager",
    rating: 4,
    message: "Great platform for generating engaging content quickly. The Comic Story Builder is my favorite feature.",
    approved: true,
    seeded: true,
    createdAt: "2026-03-01T16:20:00Z",
    updatedAt: new Date().toISOString()
  },
  {
    id: UUID().toString(),
    name: "Lisa Anderson",
    role: "YouTube Creator",
    rating: 5,
    message: "The credits system is fair and transparent. My engagement has doubled since using Visionary Suite.",
    approved: true,
    seeded: true,
    createdAt: "2026-03-05T11:00:00Z",
    updatedAt: new Date().toISOString()
  }
])

// Verify
db.user_reviews.find({approved: true}).count()
```

---

## Method 3: Users Submit Real Reviews

### How Users Can Submit Reviews:

1. **Login** to their account
2. **Navigate** to `/reviews` page
3. **Click** "Write a Review" button
4. **Fill out** the form:
   - Name
   - Role (optional)
   - Rating (1-5 stars)
   - Message (10-1000 characters)
5. **Submit** - Review goes to pending queue

### Admin Approval Flow:
1. Admin receives notification of new review
2. Admin goes to Admin Panel → Reviews
3. Admin approves or rejects the review
4. Approved reviews appear on the public Reviews page

### API for User Review Submission:
```bash
POST /api/reviews/submit
Headers: Authorization: Bearer <token>
Body: {
  "name": "User Name",
  "role": "Their Role",
  "rating": 5,
  "message": "Their review message..."
}
```

---

## Quick Admin Commands (curl)

### Bulk Seed Reviews (Admin Token Required):
```bash
ADMIN_TOKEN="your_admin_token_here"

curl -X POST "https://www.visionary-suite.com/api/reviews/admin/seed-bulk" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Seed Single Review:
```bash
curl -X POST "https://www.visionary-suite.com/api/reviews/admin/seed" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "name": "New Reviewer",
    "role": "Blogger",
    "rating": 5,
    "message": "Great platform for content creation!"
  }'
```

### Approve Pending Review:
```bash
curl -X POST "https://www.visionary-suite.com/api/reviews/admin/REVIEW_ID/approve" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"approved": true}'
```

---

## Expected Result After Seeding

| Metric | Value |
|--------|-------|
| Total Reviews | 5 |
| Average Rating | 4.8 |
| Display | Star rating + review cards |
