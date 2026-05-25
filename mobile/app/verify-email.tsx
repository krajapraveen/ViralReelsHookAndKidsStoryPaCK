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
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const mutation = useMutation({
    mutationFn: () => authApi.verifyEmail(email.trim(), code.trim()),
    onSuccess: () => router.replace('/home'),
  });

  const error = mutation.error ? normalizeApiError(mutation.error).message : null;

  return (
    <Screen title="Verify email" subtitle="Enter the verification code sent by Visionary Suite.">
      <TextField label="Email" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" />
      <TextField label="Verification code" value={code} onChangeText={setCode} autoCapitalize="characters" />
      {error ? <Text className="mb-4 text-rose-300">{error}</Text> : null}
      <Button title="Verify" loading={mutation.isPending} disabled={!email || !code} onPress={() => mutation.mutate()} />
    </Screen>
  );
}
