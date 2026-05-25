import { api } from './client';
import type { AuthResponse, User } from '@/types/api';

const unwrapAuth = (payload: AuthResponse) => ({
  token: payload.access_token || payload.token,
  user: payload.user,
});

export const authApi = {
  async login(email: string, password: string) {
    const response = await api.post<AuthResponse>('/api/auth/login', { email, password });
    return unwrapAuth(response.data);
  },
  async signup(name: string, email: string, password: string) {
    const response = await api.post<AuthResponse>('/api/auth/register', {
      name,
      email,
      password,
    });
    return unwrapAuth(response.data);
  },
  async me() {
    const response = await api.get<User>('/api/auth/me');
    return response.data;
  },
  async verifyEmail(email: string, code: string) {
    const response = await api.post('/api/auth/verify-email', { email, code });
    return response.data;
  },
  async resendVerification() {
    const response = await api.post('/api/auth/resend-verification');
    return response.data;
  },
  async forgotPassword(email: string) {
    const response = await api.post('/api/auth/forgot-password', { email });
    return response.data;
  },
  async resetPassword(token: string, password: string) {
    const response = await api.post('/api/auth/reset-password', { token, password });
    return response.data;
  },
  async updateProfile(data: Partial<User>) {
    const response = await api.put<User>('/api/auth/profile', data);
    return response.data;
  },
};
