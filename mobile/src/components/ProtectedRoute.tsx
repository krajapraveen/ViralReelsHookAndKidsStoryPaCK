import { Redirect } from 'expo-router';
import { PropsWithChildren } from 'react';

import { StateView } from './StateView';
import { useAuth } from '@/providers/AuthProvider';

export function ProtectedRoute({ children }: PropsWithChildren) {
  const { initializing, isAuthenticated } = useAuth();

  if (initializing) {
    return <StateView title="Restoring session" message="Checking your secure mobile token." loading />;
  }

  if (!isAuthenticated) {
    return <Redirect href="/login" />;
  }

  return <>{children}</>;
}
