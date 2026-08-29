import { useMutation } from '@tanstack/react-query';
import { useLocalSearchParams } from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import { Text, View } from 'react-native';

import { walletApi } from '@/api/wallet';
import { Button } from '@/components/Button';
import { Screen } from '@/components/Screen';

export default function PaymentScreen() {
  const params = useLocalSearchParams<{ productId?: string }>();
  const createOrder = useMutation({
    mutationFn: () => walletApi.createPaymentOrder(params.productId || ''),
    onSuccess: async (data: any) => {
      const checkoutUrl = data?.payment_link || data?.checkout_url || data?.url;
      if (checkoutUrl) {
        await WebBrowser.openBrowserAsync(checkoutUrl);
      }
    },
  });

  return (
    <Screen title="Payment" subtitle="Mobile-safe checkout handoff for existing payment APIs.">
      <View className="mb-5 rounded-3xl border border-amber-400/20 bg-amber-400/10 p-4">
        <Text className="font-bold text-amber-100">Production payment TODO</Text>
        <Text className="mt-2 leading-6 text-amber-100/80">
          The repository currently uses web-oriented Cashfree checkout APIs. This screen can create a backend order and
          open a hosted checkout if returned, but native SDK/IAP compliance must be finalized before app-store release.
        </Text>
      </View>
      <Text className="mb-4 text-slate-300">Product ID: {params.productId || 'not selected'}</Text>
      <Button
        title="Create payment order"
        disabled={!params.productId}
        loading={createOrder.isPending}
        onPress={() => createOrder.mutate()}
      />
      {createOrder.error ? (
        <Text className="mt-4 text-rose-300">Unable to start checkout. Confirm the product and mobile payment contract.</Text>
      ) : null}
    </Screen>
  );
}
