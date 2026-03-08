# Google Analytics 4 - Audiences & Goals Setup Guide

## Overview

This guide helps you create audiences and conversion goals in GA4 for Visionary Suite using the custom events we've implemented.

---

## Custom Events Now Tracked

| Event Name | When Fired | Parameters |
|------------|------------|------------|
| `sign_up` | User registers (email or Google) | `method` (email/google) |
| `login` | User logs in | `method` (email/google) |
| `begin_checkout` | User clicks Subscribe/Buy on Pricing page | `currency`, `value`, `items` |
| `purchase` | Payment completed via Cashfree | `transaction_id`, `currency`, `value`, `items` |
| `generate_content` | User generates any content | `feature` (gif_maker/comic_avatar/comic_strip/reel_generator/story_generator), `credits_used` |
| `download` | User downloads generated content | `content_type`, `feature` |

---

## How to Create Audiences in GA4

### Step 1: Access Audiences
1. Go to [Google Analytics](https://analytics.google.com)
2. Select your property: **Visionary Suite**
3. Click **Configure** (left sidebar)
4. Click **Audiences**
5. Click **New audience**

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
