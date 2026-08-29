import Constants from 'expo-constants';

const trimTrailingSlash = (value: string) => value.replace(/\/+$/, '');
const extra = Constants.expoConfig?.extra || {};

export const env = {
  apiBaseUrl: trimTrailingSlash(
    process.env.EXPO_PUBLIC_API_URL || String(extra.apiBaseUrl || 'http://localhost:8001'),
  ),
  appEnv: process.env.EXPO_PUBLIC_APP_ENV || String(extra.appEnv || 'development'),
  googleClientId: process.env.EXPO_PUBLIC_GOOGLE_CLIENT_ID || '',
};

export function getApiUrl(path = '') {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${env.apiBaseUrl}${normalizedPath}`;
}
