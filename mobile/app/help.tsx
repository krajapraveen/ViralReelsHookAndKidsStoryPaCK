import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { Text, View } from 'react-native';

import { supportApi } from '@/api/support';
import { Button } from '@/components/Button';
import { Screen } from '@/components/Screen';
import { TextField } from '@/components/TextField';
import { useAuth } from '@/providers/AuthProvider';

export default function HelpScreen() {
  const { user } = useAuth();
  const [message, setMessage] = useState('');
  const contact = useMutation({
    mutationFn: () => supportApi.contact({ email: user?.email, name: user?.name, message }),
    onSuccess: () => setMessage(''),
  });

  return (
    <Screen title="Help and support" subtitle="Contact support and keep common help routes mobile-accessible.">
      <View className="mb-5 rounded-3xl border border-white/10 bg-white/5 p-4">
        <Text className="text-lg font-black text-white">Support coverage</Text>
        <Text className="mt-2 leading-6 text-slate-300">
          Existing APIs include help manual, help search, feedback/contact, feature requests, reviews, and security
          reporting. This screen wires contact first and keeps the remaining routes explicit for future expansion.
        </Text>
      </View>

      <TextField label="Message" value={message} onChangeText={setMessage} multiline />
      <Button title="Send message" loading={contact.isPending} disabled={!message} onPress={() => contact.mutate()} />
      {contact.isSuccess ? <Text className="mt-4 text-emerald-100">Message sent.</Text> : null}
      {contact.isError ? <Text className="mt-4 text-rose-300">Unable to send message.</Text> : null}
    </Screen>
  );
}
