import { createContext, PropsWithChildren, useContext, useEffect, useMemo, useState } from 'react';

import { authApi } from '@/api/auth';
import { normalizeApiError } from '@/api/client';
import { tokenStore } from '@/api/tokenStore';
import type { User } from '@/types/api';

type AuthContextValue = {
  user: User | null;
  token: string | null;
  initializing: boolean;
  error: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (name: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [initializing, setInitializing] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function restore() {
      try {
        const [storedToken, storedUser] = await Promise.all([
          tokenStore.getToken(),
          tokenStore.getUser<User>(),
        ]);
        if (!mounted) return;
        setToken(storedToken);
        setUser(storedUser);

        if (storedToken) {
          try {
            const freshUser = await authApi.me();
            if (mounted) {
              setUser(freshUser);
              await tokenStore.setUser(freshUser);
            }
          } catch {
            await tokenStore.clearSession();
            if (mounted) {
              setToken(null);
              setUser(null);
            }
          }
        }
      } finally {
        if (mounted) setInitializing(false);
      }
    }

    restore();
    return () => {
      mounted = false;
    };
  }, []);

  const persistSession = async (nextToken?: string, nextUser?: User) => {
    if (!nextToken) {
      throw new Error('Login succeeded but no JWT was returned by the API.');
    }
    await tokenStore.setToken(nextToken);
    setToken(nextToken);

    const resolvedUser = nextUser || (await authApi.me());
    await tokenStore.setUser(resolvedUser);
    setUser(resolvedUser);
  };

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      initializing,
      error,
      isAuthenticated: Boolean(token),
      async login(email, password) {
        setError(null);
        try {
          const session = await authApi.login(email, password);
          await persistSession(session.token, session.user);
        } catch (err) {
          const normalized = normalizeApiError(err);
          setError(normalized.message);
          throw err;
        }
      },
      async signup(name, email, password) {
        setError(null);
        try {
          const session = await authApi.signup(name, email, password);
          await persistSession(session.token, session.user);
        } catch (err) {
          const normalized = normalizeApiError(err);
          setError(normalized.message);
          throw err;
        }
      },
      async logout() {
        await tokenStore.clearSession();
        setToken(null);
        setUser(null);
      },
      async refreshUser() {
        const freshUser = await authApi.me();
        await tokenStore.setUser(freshUser);
        setUser(freshUser);
      },
    }),
    [error, initializing, token, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
