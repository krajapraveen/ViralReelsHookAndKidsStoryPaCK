import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { Text, View } from 'react-native';

import { walletApi } from '@/api/wallet';
import { Button } from '@/components/Button';
import { Screen } from '@/components/Screen';
import { StateView } from '@/components/StateView';
import { ToolCard } from '@/components/ToolCard';
import { CREATOR_TOOLS } from '@/constants/features';
import { useAuth } from '@/providers/AuthProvider';

export default function HomeScreen() {
  const { user } = useAuth();
  const balance = useQuery({ queryKey: ['credits'], queryFn: walletApi.balance });
  const featured = CREATOR_TOOLS.slice(0, 4);

  return (
    <Screen
      title="Visionary Suite"
      subtitle={`Welcome${user?.name ? `, ${user.name}` : ''}. Create cinematic AI content from your phone.`}
      right={<Button title="Pricing" variant="secondary" onPress={() => router.push('/pricing')} />}
    >
      <View className="mb-5 rounded-3xl border border-white/10 bg-white/5 p-5">
        <Text className="text-sm font-semibold uppercase tracking-wide text-slate-400">Credits wallet</Text>
        {balance.isLoading ? (
          <StateView title="Loading credits" loading />
        ) : balance.isError ? (
          <StateView title="Credits unavailable" message="Pull to retry or open Wallet." />
        ) : (
          <Text className="mt-2 text-4xl font-black text-white">
            {balance.data?.balance ?? balance.data?.credits ?? balance.data?.available ?? 0}
          </Text>
        )}
      </View>

      <Text className="mb-3 text-lg font-black text-white">Continue creating</Text>
      {featured.map((tool) => (
        <ToolCard key={tool.key} tool={tool} onPress={() => router.push(tool.route as never)} />
      ))}
      <Button title="See all creator tools" variant="secondary" onPress={() => router.push('/create')} />
    </Screen>
  );
}
