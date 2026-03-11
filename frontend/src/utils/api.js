import axios from 'axios';

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
  // Remove Content-Type for FormData to let browser set it with boundary
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type'];
  }
  return config;
});

// Handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
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
