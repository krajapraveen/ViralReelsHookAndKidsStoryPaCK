import axios from 'axios';
import { toast } from 'sonner';
import { BUILD_HASH } from './buildInfo';

// USE RELATIVE URLs - This ALWAYS works regardless of deployment
// The browser will automatically use the current domain
const getApiBaseUrl = () => {
  // Check if we're in browser
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    const origin = window.location.origin;
    
    // For production domains, use same origin (relative URLs)
    if (hostname === 'visionary-suite.com' || 
        hostname === 'www.visionary-suite.com' ||
        hostname.includes('emergentagent.com') ||
        hostname.includes('emergent.host')) {
      console.log('Using same-origin API calls from:', origin);
      return origin; // Use the CURRENT page's origin
    }
  }
  
  // Local development
  return process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
};

// CRITICAL: Use window.location.origin directly for production
const isProduction = typeof window !== 'undefined' && 
  (window.location.hostname === 'visionary-suite.com' || 
   window.location.hostname === 'www.visionary-suite.com');

const API_BASE_URL = isProduction ? window.location.origin : getApiBaseUrl();

console.log('=== FINAL API URL:', API_BASE_URL, '===');
console.log('=== Current hostname:', typeof window !== 'undefined' ? window.location.hostname : 'SSR', '===');

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  // P1 2026-05-19 — surface running frontend build in every request so
  // backend logs / metrics can correlate stale-bundle reports.
  config.headers['X-Frontend-Build'] = BUILD_HASH;
  // Remove Content-Type for FormData to let browser set it with boundary
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type'];
  }
  // Capture request-start timestamp for duration tracking
  config.metadata = { startTs: Date.now() };
  return config;
});

// Handle errors
api.interceptors.response.use(
  (response) => {
    // Surface safety metadata as a soft toast when the backend rewrote the input
    const meta = response.data?._safety_meta;
    if (meta?.was_rewritten) {
      toast.info(
        meta.safety_note || 'We adjusted parts of your request to keep it original.',
        { duration: 4000, id: 'safety-rewrite-notice' }
      );
    }
    // Activation sentinel: surface slow successes as spinner_over_8s signal
    try {
      const dur = Date.now() - (response.config?.metadata?.startTs || Date.now());
      if (dur > 8000 && response.config?.url && !response.config.url.includes('/funnel/')) {
        // Lazy import to avoid circular dep
        import('./activationSentinel').then((mod) => {
          mod.reportApiResponse({ status: response.status, url: response.config.url, durationMs: dur });
        }).catch(() => {});
      }
    } catch (_) { /* never break UX */ }
    return response;
  },
  (error) => {
    // ─── 2026-05 P0 — Gateway / non-JSON safety net ─────────────────────
    // If the error response body is raw HTML (nginx 502/504 pages, etc.),
    // strip it so callers can never accidentally render upstream HTML in
    // a toast. We replace `response.data` with a normalized JSON shape.
    //
    // 2026-05-18 P0 fix — ALWAYS preserve `X-Request-Id` from the response
    // header and surface it in the rewritten envelope. Previously the
    // gateway path silently dropped the correlation id, so users saw a
    // generic "service temporarily unavailable" toast with no reference,
    // breaking the founder-mandated request_id contract.
    try {
      const raw = error?.response?.data;
      const code = error?.response?.status || 0;
      const hdrs = error?.response?.headers || {};
      // Header key is lowercased by axios/node; cover both shapes.
      const requestId = hdrs['x-request-id'] || hdrs['X-Request-Id'] || null;
      const looksLikeHtml = (v) =>
        typeof v === 'string' && /^\s*<(?:!doctype|html|head|body|center|h1)/i.test(v);
      const isGateway = code === 502 || code === 503 || code === 504;
      if (looksLikeHtml(raw) || (isGateway && typeof raw === 'string')) {
        error.response.data = {
          detail: {
            // Keep the human-readable summary as before so existing pages
            // that don't yet map structured codes still render something
            // sensible — but in object form so callers can pull request_id.
            code: isGateway ? 'GATEWAY_ERROR' : 'UPSTREAM_ERROR',
            message:
              'The service is temporarily unavailable. Please try again.',
            http_status: code,
            gateway: true,
            request_id: requestId,
            retryable: true,
          },
          // Legacy callers that read `data.detail` as a string still work —
          // they get the raw message; new callers read `data.detail.message`
          // and `data.detail.request_id`.
          gateway: true,
          request_id: requestId,
        };
      }
    } catch (_) { /* noop */ }

    // Activation sentinel — log 4xx/5xx + slow failures (skip self-tracking endpoints)
    try {
      const dur = Date.now() - (error.config?.metadata?.startTs || Date.now());
      const url = error.config?.url || '';
      const status = error.response?.status || 0;
      if (!url.includes('/funnel/')) {
        import('./activationSentinel').then((mod) => {
          mod.reportApiResponse({ status, url, durationMs: dur });
        }).catch(() => {});
      }
    } catch (_) { /* noop */ }
    if (error.response?.status === 401) {
      // Don't redirect for open-access pages (growth funnel) or auth endpoints
      const path = window.location.pathname;
      const url = error.config?.url || '';
      const openAccessPaths = ['/app/story-video-studio', '/app/story-preview', '/v/', '/character/'];
      const isOpenAccess = openAccessPaths.some(p => path.startsWith(p));
      const isAuthEndpoint = url.includes('/auth/google-signin') || url.includes('/auth/login') || url.includes('/auth/register');
      if (!isOpenAccess && !isAuthEndpoint) {
        // P0 2026-05-16 — generation-in-flight 401 deferral.
        // Token can expire DURING a 30-60s reel/trailer/story render.
        // Yanking the user to /login the moment their result is about to
        // land destroys the reward moment. Defer the hard redirect: show
        // a non-blocking toast, keep the page mounted, and let the page's
        // own finally{} flush the pending login AFTER the result has
        // rendered (or the generation has cleanly failed).
        try {
          // Dynamic import keeps generationLifecycle out of the api.js
          // dependency graph at module load (avoids any TDZ/circular risk).
          // eslint-disable-next-line global-require
          const lifecycle = require('./generationLifecycle');
          if (lifecycle.isGenerationInFlight()) {
            lifecycle.deferLogin(window.location.pathname + window.location.search);
            toast.error('Session expired. Please log in again to continue.', {
              duration: 6000,
              id: 'session-expired-deferred',
            });
            return Promise.reject(error);
          }
        } catch (_) { /* fall through to hard redirect */ }

        localStorage.removeItem('token');
        localStorage.removeItem('user');
        const returnPath = window.location.pathname + window.location.search;
        const loginUrl = returnPath && returnPath !== '/' && returnPath !== '/login'
          ? `/login?return=${encodeURIComponent(returnPath)}`
          : '/login';
        window.location.href = loginUrl;
      }
    }

    // Kill switch 503 — honest user messaging, no retry storm.
    // P0 2026-05-16 — but suppress for the two pages that own their own
    // structured error mapping (Create Series + Photo-to-Comic). These
    // pages map backend `{code, message}` envelopes to actionable copy and
    // the global toast was creating a duplicate, less helpful overlay.
    if (error.response?.status === 503) {
      const reqUrl = error.config?.url || '';
      const pagePath = window.location.pathname || '';
      const SELF_HANDLED_URLS = [
        '/api/photo-to-comic/',
        '/api/story-series/',
      ];
      const SELF_HANDLED_PAGES = [
        '/app/photo-to-comic',
        '/app/create-series',
        '/app/story-series',
      ];
      const isSelfHandled =
        SELF_HANDLED_URLS.some((u) => reqUrl.includes(u)) ||
        SELF_HANDLED_PAGES.some((p) => pagePath.startsWith(p));
      if (!isSelfHandled) {
        // P1 2026-05-19 — replace generic gateway toast with safe form
        // that always carries a Reference ID. Detail message stays
        // user-readable; structured detail.message is preferred over
        // the legacy stringified detail.
        const detail = error.response?.data?.detail;
        const safeMsg = (typeof detail === 'object' && detail?.message) ||
          (typeof detail === 'string' && detail) ||
          'This feature is temporarily unavailable. Please try again shortly.';
        const requestId = (typeof detail === 'object' && detail?.request_id) ||
          error.response?.data?.request_id ||
          error.response?.headers?.['x-request-id'] ||
          null;
        // Lazy import to avoid circular dep with toastSafe → api.
        import('./toastSafe').then(({ toastErrorSafe }) => {
          toastErrorSafe(safeMsg, {
            requestId,
            code: (typeof detail === 'object' && detail?.code) || 'GATEWAY_ERROR',
            page: window.location?.pathname,
            duration: 5000,
            id: 'service-unavailable',
          });
        }).catch(() => {
          // Fallback if dynamic import fails — still safe text.
          toast.error('Service temporarily unavailable. Please try again.', {
            duration: 5000, id: 'service-unavailable',
          });
        });
      }
    }

    // ─── 2026-05 Mandatory Subscription / Zero Free Credits ──────────────
    // Surface the global SubscribeRequiredModal whenever the backend signals
    // a credit / plan block. Toast + modal per founder directive.
    try {
      const status = error.response?.status || 0;
      const data = error.response?.data || {};
      const detail = data.detail || data;
      const code = (detail && (detail.code || detail.error)) || data.error || data.code;
      const url = error.config?.url || '';
      const isAuthEndpoint = url.includes('/auth/');
      const isFunnelEndpoint = url.includes('/funnel/');
      const isBlockingError =
        !isAuthEndpoint && !isFunnelEndpoint && (
          (status === 402) ||
          code === 'INSUFFICIENT_CREDITS' ||
          code === 'insufficient_credits' ||
          code === 'UPGRADE_REQUIRED' ||
          code === 'FREE_QUOTA_EXCEEDED' ||
          code === 'subscription_required'
        );
      if (isBlockingError) {
        toast.error('Free credits have been removed. Subscribe to continue creating.', {
          duration: 6000,
          id: 'subscribe-required-toast',
        });
        const feature = (() => {
          if (url.includes('/photo-trailer')) return 'photo_trailer';
          if (url.includes('/pipeline') || url.includes('/story-video')) return 'story_video';
          if (url.includes('/reel')) return 'reel';
          if (url.includes('/comix') || url.includes('/comic')) return 'comix';
          if (url.includes('/gif')) return 'gif';
          if (url.includes('/coloring')) return 'coloring_book';
          if (url.includes('/bedtime')) return 'bedtime_story';
          return 'generic';
        })();
        window.dispatchEvent(new CustomEvent('subscribe-required-modal', {
          detail: { feature, source: 'api_interceptor', http_status: status, code: code || null },
        }));
      }
    } catch (_) { /* never break UX */ }

    return Promise.reject(error);
  }
);

export const authAPI = {
  register: (data) => api.post('/api/auth/register', data),
  login: (data) => api.post('/api/auth/login', data),
  getCurrentUser: () => api.get('/api/auth/me'),
  verifyEmail: (data) => api.post('/api/auth/verify-email', data),
  resendVerification: () => api.post('/api/auth/resend-verification'),
  forgotPassword: (data, config) => api.post('/api/auth/forgot-password', data, config),
  resetPassword: (data) => api.post('/api/auth/reset-password', data),
  changePassword: (data) => api.put('/api/auth/password', data),
  updateProfile: (data) => api.put('/api/auth/profile', data),
  exportData: () => api.get('/api/auth/export-data'),
  deleteAccount: () => api.delete('/api/auth/account'),
};

export const creditAPI = {
  getBalance: () => api.get('/api/credits/balance'),
  getLedger: (page = 0, size = 20) => api.get(`/api/credits/ledger?page=${page}&size=${size}`),
};

export const generationAPI = {
  generateReel: (data) => api.post('/api/generate/reel', data),
  generateStory: (data) => api.post('/api/generate/story', data),
  getGeneration: (id) => api.get(`/api/generate/${id}`),
  getGenerations: (type, page = 0, size = 20) => {
    const typeParam = type ? `type=${type}&` : '';
    return api.get(`/api/generate/?${typeParam}page=${page}&size=${size}`);
  },
  downloadPDF: (id) => {
    return api.get(`/api/generate/${id}/pdf`, {
      responseType: 'blob'
    });
  }
};

export const paymentAPI = {
  getProducts: () => api.get('/api/cashfree/products'),
  getCurrencies: () => api.get('/api/cashfree/currencies'),
  getExchangeRate: (currency) => api.get(`/api/cashfree/exchange-rate/${currency}`),
  createOrder: (productId, currency = 'INR') => api.post('/api/cashfree/create-order', { productId, currency }),
  verifyPayment: (data) => api.post('/api/cashfree/verify', data),
  getPaymentHistory: (page = 0, size = 20) => api.get(`/api/cashfree/payments/history?page=${page}&size=${size}`),
};

// Wallet & Job Pipeline API
export const walletAPI = {
  getWallet: () => api.get('/api/wallet/me'),
  getPricing: () => api.get('/api/wallet/pricing'),
  createJob: (data, idempotencyKey = null) => {
    const headers = idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {};
    return api.post('/api/wallet/jobs', data, { headers });
  },
  getJob: (jobId) => api.get(`/api/wallet/jobs/${jobId}`),
  getJobResult: (jobId) => api.get(`/api/wallet/jobs/${jobId}/result`),
  listJobs: (params = {}) => api.get('/api/wallet/jobs', { params }),
  cancelJob: (jobId) => api.post(`/api/wallet/jobs/${jobId}/cancel`),
  getLedger: (limit = 50, skip = 0) => api.get(`/api/wallet/ledger?limit=${limit}&skip=${skip}`),
};

export default api;
