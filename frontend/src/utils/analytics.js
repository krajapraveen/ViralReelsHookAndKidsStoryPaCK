// Google Analytics 4 Event Tracking Utility
// Measurement ID: G-X4Y9E4QSF8

// Helper function to track events
export const trackEvent = (eventName, parameters = {}) => {
  if (typeof window !== 'undefined' && window.gtag) {
    window.gtag('event', eventName, parameters);
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

  // Page Views (automatic, but can be called manually for SPAs)
  trackPageView: (pagePath, pageTitle) => {
    trackEvent('page_view', {
      page_path: pagePath,
      page_title: pageTitle,
    });
  },

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
};

export default analytics;
