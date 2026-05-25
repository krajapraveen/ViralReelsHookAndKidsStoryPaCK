import { Link, router } from 'expo-router';
import { useState } from 'react';
import { Text, View } from 'react-native';

import { Button } from '@/components/Button';
import { Screen } from '@/components/Screen';
import { TextField } from '@/components/TextField';
import { useAuth } from '@/providers/AuthProvider';

export default function LoginScreen() {
  const { login, error } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    setLoading(true);
    try {
      await login(email.trim(), password);
      router.replace('/home');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Screen title="Log in" subtitle="Secure JWT auth is persisted with Expo SecureStore.">
      <TextField label="Email" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" />
      <TextField label="Password" value={password} onChangeText={setPassword} secureTextEntry />
      {error ? <Text className="mb-4 text-rose-300">{error}</Text> : null}
      <Button title="Log in" loading={loading} disabled={!email || !password} onPress={submit} />
      <View className="mt-5 gap-3">
        <Link href="/signup" className="text-center font-bold text-aurora">
          Create an account
        </Link>
        <Link href="/forgot-password" className="text-center font-bold text-slate-300">
          Forgot password?
        </Link>
      </View>
    </Screen>
  );
}
