import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { Text, View } from 'react-native';

import { walletApi } from '@/api/wallet';
import { Button } from '@/components/Button';
import { Screen } from '@/components/Screen';
import { StateView } from '@/components/StateView';

export default function PricingScreen() {
  const pricing = useQuery({ queryKey: ['pricing'], queryFn: walletApi.products });

  return (
    <Screen title="Pricing" subtitle="Subscription and credit options adapted for mobile purchase handoff.">
      {pricing.isLoading ? (
        <StateView title="Loading plans" loading />
      ) : pricing.isError || !pricing.data?.length ? (
        <StateView title="Pricing unavailable" message="No pricing data came back from the existing APIs." />
      ) : (
        pricing.data.map((plan, index) => (
          <View key={plan.id || plan.productId || index} className="mb-4 rounded-3xl border border-white/10 bg-white/5 p-5">
            <Text className="text-2xl font-black text-white">{plan.name || 'Visionary plan'}</Text>
            <Text className="mt-2 leading-6 text-slate-300">{plan.description || 'Credits for creative generation.'}</Text>
            <Text className="mt-4 text-3xl font-black text-aurora">
              {plan.currency || 'INR'} {plan.price ?? '--'}
            </Text>
            <View className="mt-4">
              <Button
                title="Choose plan"
                onPress={() =>
                  router.push({
                    pathname: '/payment',
                    params: { productId: plan.id || plan.productId || '' },
                  })
                }
              />
            </View>
          </View>
        ))
      )}
    </Screen>
  );
}
