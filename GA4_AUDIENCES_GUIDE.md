# Google Analytics 4 - Audiences & Goals Setup Guide

## Overview

This guide helps you create audiences and conversion goals in GA4 for Visionary Suite using the custom events we've implemented.

---

## Custom Events Now Tracked

### Authentication Events
| Event Name | When Fired | Parameters |
|------------|------------|------------|
| `sign_up` | User registers (email or Google) | `method` (email/google) |
| `login` | User logs in | `method` (email/google) |
| `logout` | User logs out | - |

### Enhanced E-Commerce Events (GA4 Standard)
| Event Name | When Fired | Parameters |
|------------|------------|------------|
| `view_item_list` | User views pricing page | `item_list_name`, `items[]` |
| `view_item` | User views product details | `currency`, `value`, `items[]` |
| `select_item` | User clicks on a product | `item_list_name`, `items[]` |
| `add_to_cart` | User selects plan to purchase | `currency`, `value`, `items[]` |
| `begin_checkout` | User starts payment | `currency`, `value`, `items[]` |
| `add_payment_info` | User enters payment details | `payment_type`, `currency`, `value` |
| `purchase` | Payment completed | `transaction_id`, `currency`, `value`, `items[]` |
| `refund` | Refund processed | `transaction_id`, `value` |

### Content Events
| Event Name | When Fired | Parameters |
|------------|------------|------------|
| `generate_content` | User starts generation | `feature`, `credits_used` |
| `generation_complete` | Generation finishes | `feature`, `success` |
| `download` | User downloads content | `content_type`, `feature` |

### Engagement Events
| Event Name | When Fired | Parameters |
|------------|------------|------------|
| `button_click` | CTA clicked | `button_name`, `location` |
| `cta_click` | Call-to-action clicked | `cta_text`, `cta_location` |
| `form_submit` | Form submitted | `form_name`, `success` |
| `scroll_depth` | Scroll milestone | `depth_percentage` |
| `share` | Content shared | `method`, `content_type` |

### Blog Events
| Event Name | When Fired | Parameters |
|------------|------------|------------|
| `blog_view` | Article opened | `article_slug`, `article_title`, `category` |
| `blog_read_complete` | Article fully read | `article_slug`, `read_time_seconds` |

### Error Events
| Event Name | When Fired | Parameters |
|------------|------------|------------|
| `error` | General error | `error_type`, `error_message`, `location` |
| `generation_error` | Generation failed | `feature`, `error_message` |

---

## How to Verify Events are Working

### Option 1: Use the GA4 Event Tester (Admin Tool)
1. Login to Visionary Suite as admin
2. Go to `/app/admin/ga4-tester`
3. Click "Check Status" to verify GA4 is loaded
4. Click individual event buttons to fire test events
5. Open GA4 Realtime to verify receipt

### Option 2: GA4 Realtime Report
1. Go to [Google Analytics](https://analytics.google.com)
2. Select your property: **Visionary Suite**
3. Go to **Reports → Realtime**
4. Perform actions on the website
5. Watch events appear in realtime (5-30 second delay)

---

### Audience 1: Paid Users
**Purpose:** Users who have made at least one purchase

**Configuration:**
1. Click **Create a custom audience**
2. Name: `Paid Users`
3. Add condition:
   - **Events** > `purchase`
   - Parameter: `value` > 0
4. Membership duration: 90 days
5. Click **Save**

---

### Audience 2: Active Free Users
**Purpose:** Users who generate content but haven't purchased

**Configuration:**
1. Click **Create a custom audience**
2. Name: `Active Free Users`
3. Add condition group (Include):
   - **Events** > `generate_content`
4. Add exclusion (Exclude):
   - **Events** > `purchase`
5. Membership duration: 30 days
6. Click **Save**

---

### Audience 3: High-Intent Users
**Purpose:** Users who started checkout but didn't complete

**Configuration:**
1. Click **Create a custom audience**
2. Name: `Cart Abandoners`
3. Add condition group (Include):
   - **Events** > `begin_checkout`
4. Add exclusion (Exclude):
   - **Events** > `purchase` (within same session)
5. Membership duration: 7 days
6. Click **Save**

---

### Audience 4: Power Creators
**Purpose:** Users who generate content frequently

**Configuration:**
1. Click **Create a custom audience**
2. Name: `Power Creators`
3. Add condition:
   - **Events** > `generate_content`
   - Event count > 5 (in last 7 days)
4. Membership duration: 30 days
5. Click **Save**

---

## How to Set Up Conversion Goals

### Step 1: Access Conversions
1. In GA4, go to **Configure** > **Events**
2. Find your custom events
3. Toggle the **Mark as conversion** switch for:
   - `sign_up`
   - `purchase`
   - `begin_checkout`

### Step 2: View Conversions
1. Go to **Reports** > **Engagement** > **Conversions**
2. You'll see conversion data for marked events

---

## Feature Usage Tracking

To see which features are most used:

1. Go to **Explore** (left sidebar)
2. Click **Blank** exploration
3. Add dimension: `Event name` and `feature` (custom parameter)
4. Add metric: `Event count`
5. Filter to `generate_content` events
6. Create a pie chart or bar chart

---

## Revenue Tracking

The `purchase` event includes:
- `transaction_id`: Unique Cashfree order ID
- `value`: Amount in INR
- `currency`: INR
- `items`: Product purchased

To view revenue:
1. Go to **Reports** > **Monetization** > **Overview**
2. Or create a custom report in **Explore**

---

## Realtime Testing

To verify events are firing:
1. Go to **Reports** > **Realtime**
2. Open Visionary Suite in another tab
3. Perform actions (signup, generate, purchase)
4. Watch events appear in realtime

---

## Next Steps

1. **Set up Google Ads remarketing:** Link GA4 to Google Ads and use audiences for retargeting
2. **Enhanced e-commerce:** Implement detailed product/item tracking
3. **Custom funnel analysis:** Track user journey from visit to purchase

---

## Questions?

Contact the development team if you need additional events tracked.
