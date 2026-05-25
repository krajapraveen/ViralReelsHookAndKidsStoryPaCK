import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { Text, View } from 'react-native';

import { authApi } from '@/api/auth';
import { Button } from '@/components/Button';
import { Screen } from '@/components/Screen';
import { TextField } from '@/components/TextField';
import { preparePushNotifications } from '@/lib/mobileCapabilities';
import { useAuth } from '@/providers/AuthProvider';

export default function SettingsScreen() {
  const { user, refreshUser } = useAuth();
  const [name, setName] = useState(user?.name || user?.full_name || '');
  const [pushMessage, setPushMessage] = useState<string | null>(null);
  const updateProfile = useMutation({
    mutationFn: () => authApi.updateProfile({ name }),
    onSuccess: refreshUser,
  });

  return (
    <Screen title="Settings" subtitle="Profile, privacy, push-ready structure, and mobile account controls.">
      <TextField label="Display name" value={name} onChangeText={setName} />
      <Button title="Save profile" loading={updateProfile.isPending} onPress={() => updateProfile.mutate()} />

      <View className="mt-5 rounded-3xl border border-white/10 bg-white/5 p-4">
        <Text className="text-lg font-black text-white">Push notifications</Text>
        <Text className="mt-2 leading-6 text-slate-300">
          Expo Notifications is installed and app config is ready. Backend-native token registration is a documented TODO.
        </Text>
        <View className="mt-4">
          <Button
            title="Check push readiness"
            variant="secondary"
            onPress={async () => {
              const result = await preparePushNotifications();
              setPushMessage(result.reason || result.todo || (result.ready ? 'Ready' : 'Not ready'));
            }}
          />
        </View>
        {pushMessage ? <Text className="mt-3 text-slate-300">{pushMessage}</Text> : null}
      </View>

      <View className="mt-5 rounded-3xl border border-white/10 bg-white/5 p-4">
        <Text className="text-lg font-black text-white">Privacy and account</Text>
        <Text className="mt-2 leading-6 text-slate-300">
          Existing backend routes include data export, delete account, consent, and privacy requests. Destructive actions
          should add confirmation UX before being enabled.
        </Text>
      </View>
    </Screen>
  );
}
