import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

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
  return config;
});

// Handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  register: (data) => api.post('/api/auth/register', data),
  login: (data) => api.post('/api/auth/login', data),
  getCurrentUser: () => api.get('/api/auth/me'),
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

export default api;
