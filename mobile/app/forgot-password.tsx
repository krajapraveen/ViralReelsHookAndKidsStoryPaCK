import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { Text, View } from 'react-native';

import { authApi } from '@/api/auth';
import { normalizeApiError } from '@/api/client';
import { Button } from '@/components/Button';
import { Screen } from '@/components/Screen';
import { TextField } from '@/components/TextField';

export default function ForgotPasswordScreen() {
  const [email, setEmail] = useState('');
  const mutation = useMutation({ mutationFn: () => authApi.forgotPassword(email.trim()) });
  const error = mutation.error ? normalizeApiError(mutation.error).message : null;

  return (
    <Screen title="Forgot password" subtitle="Request a reset email from the existing backend flow.">
      <TextField label="Email" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" />
      {error ? <Text className="mb-4 text-rose-300">{error}</Text> : null}
      {mutation.isSuccess ? (
        <View className="mb-4 rounded-2xl bg-emerald-400/10 p-4">
          <Text className="text-emerald-100">If that email exists, reset instructions were sent.</Text>
        </View>
      ) : null}
      <Button title="Send reset email" loading={mutation.isPending} disabled={!email} onPress={() => mutation.mutate()} />
    </Screen>
  );
}
