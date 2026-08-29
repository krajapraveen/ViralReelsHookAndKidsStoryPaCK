import { useMutation } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useState } from 'react';
import { Text } from 'react-native';

import { authApi } from '@/api/auth';
import { normalizeApiError } from '@/api/client';
import { Button } from '@/components/Button';
import { Screen } from '@/components/Screen';
import { TextField } from '@/components/TextField';

export default function VerifyEmailScreen() {
  const [token, setToken] = useState('');
  const mutation = useMutation({
    mutationFn: () => authApi.verifyEmail(token.trim()),
    onSuccess: () => router.replace('/home'),
  });

  const error = mutation.error ? normalizeApiError(mutation.error).message : null;

  return (
    <Screen title="Verify email" subtitle="Enter or paste the email verification token sent by Visionary Suite.">
      <TextField label="Verification token" value={token} onChangeText={setToken} autoCapitalize="none" />
      {error ? <Text className="mb-4 text-rose-300">{error}</Text> : null}
      <Button title="Verify" loading={mutation.isPending} disabled={!token} onPress={() => mutation.mutate()} />
    </Screen>
  );
}
