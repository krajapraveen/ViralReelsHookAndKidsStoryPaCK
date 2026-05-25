import { api } from './client';
import type { CreditBalance, PricingProduct } from '@/types/api';

export const walletApi = {
  async balance() {
    const response = await api.get<CreditBalance>('/api/credits/balance');
    return response.data;
  },
  async ledger() {
    const response = await api.get('/api/credits/ledger?page=0&size=25');
    return response.data;
  },
  async pricing() {
    const response = await api.get('/api/pricing-catalog/plans');
    return response.data;
  },
  async products() {
    const response = await api.get<PricingProduct[] | { products?: PricingProduct[] }>('/api/cashfree/products');
    return Array.isArray(response.data) ? response.data : response.data.products || [];
  },
  async createPaymentOrder(productId: string, currency = 'INR') {
    const response = await api.post('/api/cashfree/create-order', { productId, currency });
    return response.data;
  },
  async history() {
    const response = await api.get('/api/cashfree/payments/history?page=0&size=25');
    return response.data;
  },
};
