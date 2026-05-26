import axios, { AxiosError } from 'axios';
import Constants from 'expo-constants';

import { tokenStore } from './tokenStore';
import { env } from '@/config/env';

export const API_BASE_URL = env.apiBaseUrl;

export type NormalizedApiError = {
  message: string;
  code?: string;
  requestId?: string;
  status?: number;
  retryable?: boolean;
  fields?: Record<string, string>;
};

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 45000,
  headers: {
    'Content-Type': 'application/json',
    'X-App-Client': 'visionary-suite-mobile',
  },
});

api.interceptors.request.use(async (config) => {
  const token = await tokenStore.getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  config.headers['X-App-Build'] = Constants.expoConfig?.version || 'dev';
  return config;
});

export function normalizeApiError(error: unknown): NormalizedApiError {
  if (!axios.isAxiosError(error)) {
    const fields = typeof error === 'object' && error && 'fields' in error
      ? (error as { fields?: Record<string, string> }).fields
      : undefined;
    return {
      message: error instanceof Error ? error.message : 'Something went wrong.',
      fields,
    };
  }

  const axiosError = error as AxiosError<any>;
  const detail = axiosError.response?.data?.detail;
  const responseFields = axiosError.response?.data?.fields;
  const requestId =
    axiosError.response?.headers?.['x-request-id'] ||
    axiosError.response?.data?.request_id ||
    (typeof detail === 'object' ? detail?.request_id : undefined);

  if (Array.isArray(detail)) {
    const fields = detail.reduce<Record<string, string>>((acc, item) => {
      const loc = Array.isArray(item?.loc) ? item.loc : [];
      const field = String(loc[loc.length - 1] || 'form');
      acc[field] = item?.msg || 'Invalid value.';
      return acc;
    }, {});
    console.warn('[api.validation_failed]', {
      status: axiosError.response?.status,
      url: axiosError.config?.url,
      fields,
      requestId,
    });
    return {
      message: 'Please fix the highlighted fields.',
      code: 'validation_failed',
      requestId,
      status: axiosError.response?.status,
      fields,
    };
  }

  if (typeof detail === 'object' && detail) {
    return {
      message: detail.message || 'The request failed. Please try again.',
      code: detail.code,
      requestId,
      status: axiosError.response?.status,
      retryable: detail.retryable,
      fields: responseFields || detail.fields,
    };
  }

  return {
    message:
      (typeof detail === 'string' && detail) ||
      axiosError.response?.data?.message ||
      axiosError.message ||
      'The request failed. Please try again.',
    code: axiosError.response?.data?.code,
    requestId,
    status: axiosError.response?.status,
    fields: responseFields,
  };
}

export const withJobId = (path: string, jobId: string) => path.replace('{jobId}', encodeURIComponent(jobId));
