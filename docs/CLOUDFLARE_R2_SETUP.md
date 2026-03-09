# Cloudflare R2 Setup Guide for Visionary Suite

## Step 1: Create Cloudflare Account (if you don't have one)

1. Go to https://dash.cloudflare.com/sign-up
2. Sign up with your email
3. Verify your email address

## Step 2: Enable R2 Storage

1. Log into Cloudflare Dashboard: https://dash.cloudflare.com
2. In the left sidebar, click **"R2 Object Storage"**
3. Click **"Get Started"** or **"Create bucket"**
4. You may need to add a payment method (R2 has a generous free tier: 10GB storage, 1M requests/month FREE)

## Step 3: Create R2 Bucket

1. Click **"Create bucket"**
2. Bucket name: `visionary-suite-assets` (must be globally unique, try adding random numbers if taken)
3. Location: Choose closest to your users (Auto is fine)
4. Click **"Create bucket"**

## Step 4: Get API Credentials

1. Go to **R2 Overview** page
2. Click **"Manage R2 API Tokens"** on the right side
3. Click **"Create API Token"**
4. Token name: `visionary-suite-production`
5. Permissions: **"Object Read & Write"**
6. Specify bucket: Select your `visionary-suite-assets` bucket
7. TTL: Leave as "Forever" for production
8. Click **"Create API Token"**

**IMPORTANT: Copy these values immediately (shown only once):**
- Access Key ID: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- Secret Access Key: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

## Step 5: Get Account ID and Bucket URL

1. Go back to R2 Overview
2. Your **Account ID** is in the URL: `https://dash.cloudflare.com/ACCOUNT_ID/r2/overview`
3. Or find it in the right sidebar under "Account ID"

Your R2 endpoint will be:
```
https://ACCOUNT_ID.r2.cloudflarestorage.com
```

## Step 6: Enable Public Access (Optional but Recommended)

For serving images/videos directly to users:

1. Click on your bucket name
2. Go to **"Settings"** tab
3. Under **"Public access"**, click **"Allow Access"**
4. You'll get a public URL like: `https://pub-xxxxx.r2.dev`

OR use a custom domain:
1. Under **"Custom Domains"**, click **"Connect Domain"**
2. Add: `assets.visionary-suite.com` (or similar)
3. Cloudflare will auto-configure DNS and SSL

## Step 7: Provide Credentials to Emergent

After completing the above, provide these values:

```
CLOUDFLARE_R2_ACCESS_KEY_ID=your_access_key_id
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your_secret_access_key
CLOUDFLARE_R2_BUCKET_NAME=visionary-suite-assets
CLOUDFLARE_R2_ACCOUNT_ID=your_account_id
CLOUDFLARE_R2_PUBLIC_URL=https://pub-xxxxx.r2.dev (or your custom domain)
```

## Pricing (Very Affordable)

| Resource | Free Tier | Paid |
|----------|-----------|------|
| Storage | 10 GB/month | $0.015/GB |
| Class A ops (write) | 1M/month | $4.50/M |
| Class B ops (read) | 10M/month | $0.36/M |
| Egress | FREE | FREE |

For Visionary Suite typical usage:
- 1000 videos/month = ~50GB storage = ~$0.60/month
- Egress is FREE (unlike AWS S3!)

## Security Notes

- Never commit credentials to git
- Use environment variables only
- Rotate keys periodically
- Enable bucket versioning for recovery

## Testing Your Setup

After providing credentials, I will test with:
```bash
# Upload test
aws s3 cp test.txt s3://visionary-suite-assets/test.txt --endpoint-url https://ACCOUNT_ID.r2.cloudflarestorage.com

# Download test  
curl https://pub-xxxxx.r2.dev/test.txt
```
