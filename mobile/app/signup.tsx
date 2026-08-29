import { Link, router } from 'expo-router';
import { useState } from 'react';
import { Text } from 'react-native';

import { Button } from '@/components/Button';
import { Screen } from '@/components/Screen';
import { TextField } from '@/components/TextField';
import { useAuth } from '@/providers/AuthProvider';

export default function SignupScreen() {
  const { signup, error } = useAuth();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    setLoading(true);
    try {
      await signup(name.trim(), email.trim(), password);
      router.replace('/verify-email');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Screen title="Create account" subtitle="Start creating with the same Visionary Suite backend account.">
      <TextField label="Name" value={name} onChangeText={setName} />
      <TextField label="Email" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" />
      <TextField label="Password" value={password} onChangeText={setPassword} secureTextEntry />
      {error ? <Text className="mb-4 text-rose-300">{error}</Text> : null}
      <Button title="Sign up" loading={loading} disabled={!name || !email || !password} onPress={submit} />
      <Link href="/login" className="mt-5 text-center font-bold text-aurora">
        Already have an account?
      </Link>
    </Screen>
  );
}
