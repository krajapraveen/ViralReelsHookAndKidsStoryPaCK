import { ActivityIndicator, Text, View } from 'react-native';

import { Button } from './Button';

type StateViewProps = {
  title: string;
  message?: string;
  actionLabel?: string;
  onAction?: () => void;
  loading?: boolean;
};

export function StateView({ title, message, actionLabel, onAction, loading }: StateViewProps) {
  return (
    <View className="items-center justify-center rounded-3xl border border-white/10 bg-white/5 px-6 py-10">
      {loading ? <ActivityIndicator color="#22d3ee" size="large" /> : null}
      <Text className="mt-3 text-center text-xl font-black text-white">{title}</Text>
      {message ? <Text className="mt-2 text-center text-base leading-6 text-slate-300">{message}</Text> : null}
      {actionLabel && onAction ? (
        <View className="mt-5 w-full">
          <Button title={actionLabel} onPress={onAction} variant="secondary" />
        </View>
      ) : null}
    </View>
  );
}
