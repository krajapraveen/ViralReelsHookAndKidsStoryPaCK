import { useMutation } from '@tanstack/react-query';
import { Link, router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Text } from 'react-native';

import { authApi } from '@/api/auth';
import { normalizeApiError } from '@/api/client';
import { Button } from '@/components/Button';
import { Screen } from '@/components/Screen';
import { TextField } from '@/components/TextField';

export default function ResetPasswordScreen() {
  const params = useLocalSearchParams<{ token?: string }>();
  const [token, setToken] = useState(params.token || '');
  const [password, setPassword] = useState('');
  const mutation = useMutation({
    mutationFn: () => authApi.resetPassword(token.trim(), password),
    onSuccess: () => router.replace('/login'),
  });
  const error = mutation.error ? normalizeApiError(mutation.error).message : null;

  return (
    <Screen title="Reset password" subtitle="Complete the existing backend reset-password flow.">
      <TextField label="Reset token" value={token} onChangeText={setToken} autoCapitalize="none" />
      <TextField label="New password" value={password} onChangeText={setPassword} secureTextEntry />
      {error ? <Text className="mb-4 text-rose-300">{error}</Text> : null}
      <Button
        title="Reset password"
        loading={mutation.isPending}
        disabled={!token || !password}
        onPress={() => mutation.mutate()}
      />
      <Link href="/login" className="mt-5 text-center font-bold text-aurora">
        Back to login
      </Link>
    </Screen>
  );
}
