import axios from 'axios';

// FORCE correct API URL at runtime - ignore env variable on production
const getApiBaseUrl = () => {
  // Check if we're running in browser
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    
    // PRODUCTION: Always use same origin for visionary-suite.com
    if (hostname === 'visionary-suite.com' || hostname === 'www.visionary-suite.com') {
      console.log('PRODUCTION detected - using visionary-suite.com');
      return 'https://visionary-suite.com';
    }
    
    // PREVIEW: Use the preview URL
    if (hostname.includes('preview.emergentagent.com')) {
      console.log('PREVIEW detected - using', window.location.origin);
      return window.location.origin;
    }
  }
  
  // Fallback to env variable or localhost
  const envUrl = process.env.REACT_APP_BACKEND_URL;
  console.log('Using env URL:', envUrl || 'http://localhost:8001');
  return envUrl || 'http://localhost:8001';
};

const API_BASE_URL = getApiBaseUrl();
console.log('=== API Base URL Set To:', API_BASE_URL, '===');

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
  forgotPassword: (data) => api.post('/api/auth/forgot-password', data),
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
  getProducts: () => api.get('/api/payments/products'),
  getCurrencies: () => api.get('/api/payments/currencies'),
  getExchangeRate: (currency) => api.get(`/api/payments/exchange-rate/${currency}`),
  createOrder: (productId, currency = 'INR') => api.post('/api/payments/create-order', { productId, currency }),
  verifyPayment: (data) => api.post('/api/payments/verify', data),
  getPaymentHistory: (page = 0, size = 20) => api.get(`/api/payments/history?page=${page}&size=${size}`),
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
