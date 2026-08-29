import type { PropsWithChildren, ReactNode } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useNetworkStatus } from '@/hooks/useNetworkStatus';

type ScreenProps = PropsWithChildren<{
  title?: string;
  subtitle?: string;
  scroll?: boolean;
  right?: ReactNode;
}>;

export function Screen({ children, title, subtitle, scroll = true, right }: ScreenProps) {
  const { isOffline } = useNetworkStatus();
  const content = (
    <View className="flex-1 px-5 pb-6">
      {isOffline ? (
        <View className="mb-4 rounded-2xl border border-amber-400/30 bg-amber-400/10 px-4 py-3">
          <Text className="font-semibold text-amber-100">Offline mode</Text>
          <Text className="mt-1 text-sm text-amber-100/80">
            Network access is unavailable. You can browse cached screens, but API actions may fail.
          </Text>
        </View>
      ) : null}
      {title ? (
        <View className="mb-5 flex-row items-start justify-between gap-4">
          <View className="flex-1">
            <Text className="text-3xl font-black tracking-tight text-white">{title}</Text>
            {subtitle ? <Text className="mt-2 text-base leading-6 text-slate-300">{subtitle}</Text> : null}
          </View>
          {right}
        </View>
      ) : null}
      {children}
    </View>
  );

  return (
    <SafeAreaView className="flex-1 bg-void" edges={['top', 'left', 'right']}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        className="flex-1"
      >
        {scroll ? (
          <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{ flexGrow: 1 }}>
            {content}
          </ScrollView>
        ) : (
          content
        )}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
