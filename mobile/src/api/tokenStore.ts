import * as SecureStore from 'expo-secure-store';

const TOKEN_KEY = 'visionary.jwt';
const USER_KEY = 'visionary.user';

export const tokenStore = {
  async getToken() {
    return SecureStore.getItemAsync(TOKEN_KEY);
  },
  async setToken(token: string) {
    await SecureStore.setItemAsync(TOKEN_KEY, token);
  },
  async clearToken() {
    await SecureStore.deleteItemAsync(TOKEN_KEY);
  },
  async getUser<T>() {
    const raw = await SecureStore.getItemAsync(USER_KEY);
    return raw ? (JSON.parse(raw) as T) : null;
  },
  async setUser<T>(user: T) {
    await SecureStore.setItemAsync(USER_KEY, JSON.stringify(user));
  },
  async clearUser() {
    await SecureStore.deleteItemAsync(USER_KEY);
  },
  async clearSession() {
    await Promise.all([this.clearToken(), this.clearUser()]);
  },
};
