import { api } from './client';

export const supportApi = {
  async helpManual() {
    const response = await api.get('/api/help/manual');
    return response.data;
  },
  async searchHelp(query: string) {
    const response = await api.get('/api/help/search', { params: { q: query } });
    return response.data;
  },
  async contact(payload: { name?: string; email?: string; message: string }) {
    const response = await api.post('/api/feedback/contact', payload);
    return response.data;
  },
};
