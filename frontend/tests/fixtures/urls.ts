export const BASE = process.env.BASE_URL ?? "https://avatar-comic-builder.preview.emergentagent.com";

export const URLS = {
  // Public pages
  landing: `${BASE}/`,
  login: `${BASE}/login`,
  register: `${BASE}/signup`,
  forgotPassword: `${BASE}/forgot-password`,
  resetPassword: `${BASE}/reset-password`,
  verifyEmail: `${BASE}/verify-email`,
  privacy: `${BASE}/privacy-policy`,
  terms: `${BASE}/terms`,
  pricing: `${BASE}/pricing`,
  reviews: `${BASE}/reviews`,
  contact: `${BASE}/contact`,
  userManual: `${BASE}/user-manual`,
  
  // Protected App pages
  app: `${BASE}/app`,
  billing: `${BASE}/app/billing`,
  profile: `${BASE}/app/profile`,
  privacySettings: `${BASE}/app/privacy`,
  paymentHistory: `${BASE}/app/payment-history`,
  subscription: `${BASE}/app/subscription`,
  analytics: `${BASE}/app/analytics`,
  contentVault: `${BASE}/app/content-vault`,
  copyright: `${BASE}/app/copyright`,
  
  // GenStudio
  genStudio: `${BASE}/app/gen-studio`,
  t2i: `${BASE}/app/gen-studio/text-to-image`,
  t2v: `${BASE}/app/gen-studio/text-to-video`,
  i2v: `${BASE}/app/gen-studio/image-to-video`,
  videoRemix: `${BASE}/app/gen-studio/video-remix`,
  styleProfiles: `${BASE}/app/gen-studio/style-profiles`,
  genHistory: `${BASE}/app/gen-studio/history`,
  
  // Content Generators
  reelGen: `${BASE}/app/reel-generator`,
  storyGen: `${BASE}/app/story-generator`,
  storySeries: `${BASE}/app/story-series`,
  challengeGen: `${BASE}/app/challenge-generator`,
  toneSwitcher: `${BASE}/app/tone-switcher`,
  coloringBook: `${BASE}/app/coloring-book`,
  twinFinder: `${BASE}/app/twinfinder`,
  
  // Creator Tools
  creatorTools: `${BASE}/app/creator-tools`,
  calendar: `${BASE}/app/creator-tools/calendar`,
  hashtags: `${BASE}/app/creator-tools/hashtags`,
  thumbnails: `${BASE}/app/creator-tools/thumbnails`,
  carousel: `${BASE}/app/creator-tools/carousel`,
  trending: `${BASE}/app/creator-tools/trending`,
  
  // Admin
  admin: `${BASE}/app/admin`,
  adminMonitoring: `${BASE}/app/admin/monitoring`,
  
  // API endpoints for testing
  api: {
    health: `${BASE}/api/health/`,
    login: `${BASE}/api/auth/login`,
    register: `${BASE}/api/auth/register`,
    profile: `${BASE}/api/auth/me`,
    credits: `${BASE}/api/credits/balance`,
    userManual: `${BASE}/api/help/manual`,
    subscriptionPlans: `${BASE}/api/subscriptions/plans`,
    cashfreeHealth: `${BASE}/api/cashfree/health`,
    cashfreeCreateOrder: `${BASE}/api/cashfree/create-order`,
  },
};

export const PUBLIC_URLS = [
  URLS.landing,
  URLS.login,
  URLS.register,
  URLS.forgotPassword,
  URLS.privacy,
  URLS.terms,
  URLS.pricing,
  URLS.reviews,
  URLS.contact,
  URLS.userManual,
];

export const PROTECTED_URLS = [
  URLS.app,
  URLS.billing,
  URLS.profile,
  URLS.privacySettings,
  URLS.paymentHistory,
  URLS.subscription,
  URLS.analytics,
  URLS.genStudio,
  URLS.t2i,
  URLS.t2v,
  URLS.i2v,
  URLS.storyGen,
  URLS.reelGen,
  URLS.creatorTools,
];

export const ADMIN_URLS = [
  URLS.admin,
  URLS.adminMonitoring,
];
