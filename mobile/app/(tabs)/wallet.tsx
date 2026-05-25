import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { Text, View } from 'react-native';

import { walletApi } from '@/api/wallet';
import { Button } from '@/components/Button';
import { Screen } from '@/components/Screen';
import { StateView } from '@/components/StateView';

export default function WalletScreen() {
  const balance = useQuery({ queryKey: ['credits'], queryFn: walletApi.balance });
  const products = useQuery({ queryKey: ['products'], queryFn: walletApi.products });

  return (
    <Screen title="Credits wallet" subtitle="Track credits, pricing, and mobile-safe payment handoff.">
      <View className="mb-5 rounded-3xl border border-white/10 bg-white/5 p-5">
        <Text className="text-sm font-semibold uppercase tracking-wide text-slate-400">Available credits</Text>
        {balance.isLoading ? (
          <StateView title="Loading balance" loading />
        ) : (
          <Text className="mt-2 text-5xl font-black text-white">
            {balance.data?.balance ?? balance.data?.credits ?? balance.data?.available ?? 0}
          </Text>
        )}
      </View>

      <View className="mb-5 rounded-3xl border border-amber-400/20 bg-amber-400/10 p-4">
        <Text className="font-bold text-amber-100">Payment flow note</Text>
        <Text className="mt-2 leading-6 text-amber-100/80">
          Existing APIs expose Cashfree web checkout. Native SDK or store-compliant IAP needs product decisions before
          production payment capture is enabled in mobile.
        </Text>
      </View>

      <Text className="mb-3 text-lg font-black text-white">Plans and credit packs</Text>
      {products.isLoading ? (
        <StateView title="Loading products" loading />
      ) : products.isError || !products.data?.length ? (
        <StateView title="No products available" message="Pricing APIs are mapped, but no products were returned." />
      ) : (
        products.data.map((product, index) => (
          <View key={product.id || product.productId || index} className="mb-3 rounded-3xl border border-white/10 bg-white/5 p-4">
            <Text className="text-xl font-black text-white">{product.name || 'Visionary plan'}</Text>
            <Text className="mt-1 text-slate-300">{product.description || `${product.credits || 0} credits`}</Text>
            <Text className="mt-3 text-2xl font-black text-aurora">
              {product.currency || 'INR'} {product.price ?? '--'}
            </Text>
            <View className="mt-4">
              <Button
                title="Continue to payment"
                onPress={() =>
                  router.push({
                    pathname: '/payment',
                    params: { productId: product.id || product.productId || '' },
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
