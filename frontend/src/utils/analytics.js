// Google Analytics 4 Event Tracking Utility
// Measurement ID: G-X4Y9E4QSF8

// Debug mode - set to true to log events to console
const DEBUG_MODE = process.env.NODE_ENV === 'development';

// Helper function to track events
export const trackEvent = (eventName, parameters = {}) => {
  if (typeof window !== 'undefined' && window.gtag) {
    window.gtag('event', eventName, parameters);
    if (DEBUG_MODE) {
      console.log(`[GA4 Event] ${eventName}`, parameters);
    }
  }
};

// Pre-defined events for common actions
export const analytics = {
  // User Authentication Events
  trackSignup: (method = 'email') => {
    trackEvent('sign_up', { method });
  },

  trackLogin: (method = 'email') => {
    trackEvent('login', { method });
  },

  trackLogout: () => {
    trackEvent('logout');
  },

  // Content Generation Events
  trackGeneration: (featureName, creditsUsed = 0) => {
    trackEvent('generate_content', {
      feature: featureName,
      credits_used: creditsUsed,
    });
  },

  trackGenerationComplete: (featureName, success = true) => {
    trackEvent('generation_complete', {
      feature: featureName,
      success: success,
    });
  },

  // Feature Usage
  trackFeatureView: (featureName) => {
    trackEvent('view_feature', {
      feature: featureName,
    });
  },

  trackFeatureStart: (featureName) => {
    trackEvent('begin_feature', {
      feature: featureName,
    });
  },

  // ============================================
  // ENHANCED E-COMMERCE TRACKING (GA4 Standard)
  // ============================================

  // View Item - When user views a product/plan details
  trackViewItem: (item) => {
    trackEvent('view_item', {
      currency: item.currency || 'INR',
      value: item.price || 0,
      items: [{
        item_id: item.id,
        item_name: item.name,
        item_category: item.category || 'subscription',
        price: item.price || 0,
        quantity: 1
      }]
    });
  },

  // View Item List - When user views pricing page or product list
  trackViewItemList: (listName, items) => {
    trackEvent('view_item_list', {
      item_list_id: listName.toLowerCase().replace(/\s+/g, '_'),
      item_list_name: listName,
      items: items.map((item, index) => ({
        item_id: item.id,
        item_name: item.name,
        item_category: item.category || 'subscription',
        price: item.price || 0,
        index: index,
        quantity: 1
      }))
    });
  },

  // Select Item - When user clicks on a specific plan/product
  trackSelectItem: (listName, item) => {
    trackEvent('select_item', {
      item_list_id: listName.toLowerCase().replace(/\s+/g, '_'),
      item_list_name: listName,
      items: [{
        item_id: item.id,
        item_name: item.name,
        item_category: item.category || 'subscription',
        price: item.price || 0,
        quantity: 1
      }]
    });
  },

  // Add to Cart - When user selects a plan to purchase
  trackAddToCart: (item, currency = 'INR') => {
    trackEvent('add_to_cart', {
      currency: currency,
      value: item.price || 0,
      items: [{
        item_id: item.id,
        item_name: item.name,
        item_category: item.category || 'subscription',
        price: item.price || 0,
        quantity: 1
      }]
    });
  },

  // Begin Checkout - When user starts payment process
  trackBeginCheckout: (item, currency = 'INR', coupon = null) => {
    const params = {
      currency: currency,
      value: item.price || 0,
      items: [{
        item_id: item.id,
        item_name: item.name,
        item_category: item.category || 'subscription',
        price: item.price || 0,
        quantity: 1
      }]
    };
    if (coupon) params.coupon = coupon;
    trackEvent('begin_checkout', params);
  },

  // Add Payment Info - When user enters payment details
  trackAddPaymentInfo: (item, paymentType = 'cashfree', currency = 'INR') => {
    trackEvent('add_payment_info', {
      currency: currency,
      value: item.price || 0,
      payment_type: paymentType,
      items: [{
        item_id: item.id,
        item_name: item.name,
        item_category: item.category || 'subscription',
        price: item.price || 0,
        quantity: 1
      }]
    });
  },

  // Purchase - When payment is successful
  trackPurchase: (transactionId, item, currency = 'INR', coupon = null) => {
    const params = {
      transaction_id: transactionId,
      currency: currency,
      value: item.price || 0,
      tax: 0,
      shipping: 0,
      items: [{
        item_id: item.id,
        item_name: item.name,
        item_category: item.category || 'subscription',
        price: item.price || 0,
        quantity: 1
      }]
    };
    if (coupon) params.coupon = coupon;
    trackEvent('purchase', params);
  },

  // Refund - When a refund is processed
  trackRefund: (transactionId, item, currency = 'INR') => {
    trackEvent('refund', {
      transaction_id: transactionId,
      currency: currency,
      value: item.price || 0,
      items: [{
        item_id: item.id,
        item_name: item.name,
        item_category: item.category || 'subscription',
        price: item.price || 0,
        quantity: 1
      }]
    });
  },

  // ============================================
  // LEGACY PAYMENT EVENTS (for backward compatibility)
  // ============================================

  // Payment/Conversion Events
  trackPurchaseStart: (planName, amount, currency = 'INR') => {
    trackEvent('begin_checkout', {
      currency: currency,
      value: amount,
      items: [{ item_name: planName }],
    });
  },

  trackPurchaseComplete: (planName, amount, currency = 'INR', transactionId = '') => {
    trackEvent('purchase', {
      transaction_id: transactionId,
      currency: currency,
      value: amount,
      items: [{ item_name: planName }],
    });
  },

  // ============================================
  // ENGAGEMENT EVENTS
  // ============================================

  // Engagement Events
  trackDownload: (contentType, featureName) => {
    trackEvent('download', {
      content_type: contentType,
      feature: featureName,
    });
  },

  trackShare: (method, contentType) => {
    trackEvent('share', {
      method: method,
      content_type: contentType,
    });
  },

  // Button Click Tracking (for CTAs)
  trackButtonClick: (buttonName, location = 'unknown') => {
    trackEvent('button_click', {
      button_name: buttonName,
      location: location,
    });
  },

  // CTA Click Tracking
  trackCTAClick: (ctaText, ctaLocation) => {
    trackEvent('cta_click', {
      cta_text: ctaText,
      cta_location: ctaLocation,
    });
  },

  // Form Submission Tracking
  trackFormSubmit: (formName, success = true) => {
    trackEvent('form_submit', {
      form_name: formName,
      success: success,
    });
  },

  // Video Tracking
  trackVideoPlay: (videoTitle, videoLocation = 'unknown') => {
    trackEvent('video_start', {
      video_title: videoTitle,
      video_location: videoLocation,
    });
  },

  trackVideoComplete: (videoTitle, watchPercentage = 100) => {
    trackEvent('video_complete', {
      video_title: videoTitle,
      watch_percentage: watchPercentage,
    });
  },

  // Landing Page Specific Events
  trackLandingAction: (action, element) => {
    trackEvent('landing_page_action', {
      action: action,
      element: element,
    });
  },

  // Scroll Depth Tracking
  trackScrollDepth: (percentage) => {
    trackEvent('scroll_depth', {
      depth_percentage: percentage,
    });
  },

  // Page Views (automatic, but can be called manually for SPAs)
  trackPageView: (pagePath, pageTitle) => {
    trackEvent('page_view', {
      page_path: pagePath,
      page_title: pageTitle,
    });
  },

  // ============================================
  // BLOG & CONTENT EVENTS
  // ============================================

  // Blog article view
  trackBlogView: (articleSlug, articleTitle, category) => {
    trackEvent('blog_view', {
      article_slug: articleSlug,
      article_title: articleTitle,
      category: category
    });
  },

  // Blog article read complete (scrolled to bottom)
  trackBlogReadComplete: (articleSlug, readTime) => {
    trackEvent('blog_read_complete', {
      article_slug: articleSlug,
      read_time_seconds: readTime
    });
  },

  // ============================================
  // ERROR & EXCEPTION TRACKING
  // ============================================

  // Track errors
  trackError: (errorType, errorMessage, location) => {
    trackEvent('error', {
      error_type: errorType,
      error_message: errorMessage,
      location: location
    });
  },

  // Track generation failures
  trackGenerationError: (featureName, errorMessage) => {
    trackEvent('generation_error', {
      feature: featureName,
      error_message: errorMessage
    });
  },

  // ============================================
  // CUSTOM & UTILITY EVENTS
  // ============================================

  // Custom Events
  trackCustomEvent: (eventName, params) => {
    trackEvent(eventName, params);
  },

  // User Properties
  setUserProperties: (properties) => {
    if (typeof window !== 'undefined' && window.gtag) {
      window.gtag('set', 'user_properties', properties);
    }
  },

  // Set User ID (for logged-in users)
  setUserId: (userId) => {
    if (typeof window !== 'undefined' && window.gtag) {
      window.gtag('config', 'G-X4Y9E4QSF8', {
        user_id: userId,
      });
    }
  },

  // ============================================
  // DEBUG & VERIFICATION UTILITIES
  // ============================================

  // Verify GA is loaded and working
  verifyGALoaded: () => {
    const isLoaded = typeof window !== 'undefined' && typeof window.gtag === 'function';
    console.log(`[GA4 Verification] Google Analytics is ${isLoaded ? 'LOADED ✓' : 'NOT LOADED ✗'}`);
    return isLoaded;
  },

  // Send a test event to verify tracking
  sendTestEvent: () => {
    const testId = `test_${Date.now()}`;
    trackEvent('test_event', {
      test_id: testId,
      timestamp: new Date().toISOString()
    });
    console.log(`[GA4 Test] Test event sent with ID: ${testId}`);
    console.log('[GA4 Test] Check GA4 Realtime > Events to verify receipt');
    return testId;
  },

  // Get all tracked events summary
  getEventsSummary: () => {
    return {
      authentication: ['sign_up', 'login', 'logout'],
      ecommerce: ['view_item', 'view_item_list', 'select_item', 'add_to_cart', 'begin_checkout', 'add_payment_info', 'purchase', 'refund'],
      content: ['generate_content', 'generation_complete', 'download', 'share'],
      engagement: ['button_click', 'cta_click', 'form_submit', 'scroll_depth', 'page_view'],
      blog: ['blog_view', 'blog_read_complete'],
      errors: ['error', 'generation_error']
    };
  }
};

export default analytics;
