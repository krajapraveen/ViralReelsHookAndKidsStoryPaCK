# Post-Deployment GA4 Verification Checklist

## Overview
This checklist helps you verify that all Google Analytics 4 events are working correctly on your production site (visionary-suite.com) after deployment.

---

## Pre-Verification Setup

### Step 1: Open GA4 Realtime
1. Go to [Google Analytics](https://analytics.google.com)
2. Select your property: **Visionary Suite** (G-X4Y9E4QSF8)
3. Navigate to **Reports → Realtime**
4. Keep this tab open while testing

### Step 2: Open Your Production Site
1. Open a new incognito/private browser window
2. Go to [https://www.visionary-suite.com](https://www.visionary-suite.com)
3. Perform each action below and verify in GA4 Realtime

---

## Event Verification Checklist

### 1. Landing Page Events
| Action | Expected Event | GA4 Parameters | Status |
|--------|---------------|----------------|--------|
| Visit landing page | `experiment_view` | experiment_name, variant (A or B) | ☐ |
| Visit landing page | `funnel_step` | step_name: landing_view | ☐ |
| Click "Start Creating Free" CTA | `experiment_conversion` | experiment_name, variant, conversion_type | ☐ |
| Click "Start Creating Free" CTA | `funnel_step` | step_name: signup_start | ☐ |

### 2. Authentication Events
| Action | Expected Event | GA4 Parameters | Status |
|--------|---------------|----------------|--------|
| Complete signup (email) | `sign_up` | method: email | ☐ |
| Complete signup (Google) | `sign_up` | method: google | ☐ |
| Login (email) | `login` | method: email | ☐ |
| Login (Google) | `login` | method: google | ☐ |
| Complete signup | `funnel_step` | step_name: signup_complete | ☐ |

### 3. Content Generation Events
| Action | Expected Event | GA4 Parameters | Status |
|--------|---------------|----------------|--------|
| Generate GIF | `generate_content` | feature: gif_maker, credits_used | ☐ |
| Generate Comic Avatar | `generate_content` | feature: comic_avatar, credits_used | ☐ |
| Generate Reel Script | `generate_content` | feature: reel_generator, credits_used | ☐ |
| Generate Story Pack | `generate_content` | feature: story_generator, credits_used | ☐ |
| First generation | `funnel_step` | step_name: first_generation | ☐ |

### 4. Download Events
| Action | Expected Event | GA4 Parameters | Status |
|--------|---------------|----------------|--------|
| Download GIF | `download` | content_type: gif, feature: gif_maker | ☐ |
| Download Comic | `download` | content_type: image, feature: comic_avatar | ☐ |
| First download | `funnel_step` | step_name: first_download | ☐ |

### 5. E-Commerce Events
| Action | Expected Event | GA4 Parameters | Status |
|--------|---------------|----------------|--------|
| View Pricing page | `view_item_list` | item_list_name, items[] | ☐ |
| View Pricing page | `funnel_step` | step_name: pricing_view | ☐ |
| Click Buy/Subscribe | `select_item` | item_list_name, items[] | ☐ |
| Click Buy/Subscribe | `add_to_cart` | currency, value, items[] | ☐ |
| Start checkout | `begin_checkout` | currency, value, items[] | ☐ |
| Start checkout | `funnel_step` | step_name: checkout_start | ☐ |
| Enter payment info | `add_payment_info` | payment_type: cashfree | ☐ |
| Complete purchase | `purchase` | transaction_id, currency, value | ☐ |
| Complete purchase | `funnel_step` | step_name: purchase_complete | ☐ |
| Complete purchase | `funnel_complete` | funnel_name: main_conversion | ☐ |

### 6. Blog Events
| Action | Expected Event | GA4 Parameters | Status |
|--------|---------------|----------------|--------|
| Open blog article | `blog_view` | article_slug, article_title, category | ☐ |
| Read entire article | `blog_read_complete` | article_slug, read_time_seconds | ☐ |

### 7. A/B Test Events
| Action | Expected Event | GA4 Parameters | Status |
|--------|---------------|----------------|--------|
| View landing page | `experiment_view` | experiment_name: landing_page_2026, variant: A or B | ☐ |
| Click CTA on landing | `experiment_conversion` | experiment_name, variant, conversion_type | ☐ |

---

## Quick Verification Using GA4 Event Tester

If you're an admin, use the built-in GA4 Event Tester:

1. Login to Visionary Suite as admin
2. Go to `/app/admin/ga4-tester`
3. Click **"Check Status"** to verify GA4 is loaded
4. Click **"Run All Tests"** to fire all events at once
5. Check GA4 Realtime to see events appear

---

## Creating Key Events in GA4

After verifying events are firing, mark important ones as Key Events:

1. Go to **Configure → Events** in GA4
2. Find each event and toggle **"Mark as key event"**:
   - `sign_up` ✓
   - `login` ✓
   - `begin_checkout` ✓
   - `purchase` ✓
   - `generate_content` ✓
   - `download` ✓

---

## Creating Audiences in GA4

### Audience 1: Paid Users
1. Go to **Configure → Audiences → New audience**
2. Name: `Paid Users`
3. Include: Users where Event = `purchase`
4. Membership duration: 90 days
5. Save

### Audience 2: Active Free Users
1. Go to **Configure → Audiences → New audience**
2. Name: `Active Free Users`
3. Include: Users where Event = `generate_content`
4. Exclude: Users where Event = `purchase`
5. Membership duration: 30 days
6. Save

### Audience 3: Cart Abandoners
1. Go to **Configure → Audiences → New audience**
2. Name: `Cart Abandoners`
3. Include: Users where Event = `begin_checkout`
4. Exclude: Users where Event = `purchase`
5. Membership duration: 7 days
6. Save

---

## Troubleshooting

### Events Not Appearing in Realtime?
1. **Wait 5-30 seconds** - GA4 has a delay
2. **Clear browser cache** - Old code might be cached
3. **Check browser console** - Look for `[GA4 Event]` logs
4. **Verify gtag is loaded** - Look for `gtag` in console

### "No stream data detected" in GA4?
This means events haven't been triggered yet. Perform the actions above to generate data.

### Events Showing Wrong Parameters?
Check the browser console for `[GA4 Event]` logs to see exact parameters being sent.

---

## Verification Complete

Once all checkboxes are marked:
1. All events are firing correctly ✅
2. Key Events are marked in GA4 ✅
3. Audiences are created ✅
4. Your analytics are production-ready! 🎉

---

## Contact

For issues with event tracking, check:
- Browser console for `[GA4 Event]` logs
- GA4 Event Tester at `/app/admin/ga4-tester`
- GA4 Realtime report for live data
