import { router } from 'expo-router';
import { Text, View } from 'react-native';

import { Button } from '@/components/Button';
import { Screen } from '@/components/Screen';
import { useAuth } from '@/providers/AuthProvider';

export default function ProfileScreen() {
  const { user, logout } = useAuth();

  return (
    <Screen title="Profile" subtitle="Account, settings, support, and legal pages.">
      <View className="mb-5 rounded-3xl border border-white/10 bg-white/5 p-5">
        <Text className="text-2xl font-black text-white">{user?.name || user?.full_name || 'Visionary creator'}</Text>
        <Text className="mt-1 text-slate-300">{user?.email}</Text>
        <Text className="mt-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
          {user?.plan || 'Current plan unavailable'}
        </Text>
      </View>

      <View className="gap-3">
        <Button title="Settings" variant="secondary" onPress={() => router.push('/settings')} />
        <Button title="Help / support / contact" variant="secondary" onPress={() => router.push('/help')} />
        <Button title="Privacy policy" variant="secondary" onPress={() => router.push('/legal/privacy')} />
        <Button title="Terms of service" variant="secondary" onPress={() => router.push('/legal/terms')} />
        <Button title="Cookie policy" variant="secondary" onPress={() => router.push('/legal/cookies')} />
        <Button title="Security" variant="secondary" onPress={() => router.push('/legal/security')} />
        <Button
          title="Log out"
          variant="danger"
          onPress={async () => {
            await logout();
            router.replace('/login');
          }}
        />
      </View>
    </Screen>
  );
}
