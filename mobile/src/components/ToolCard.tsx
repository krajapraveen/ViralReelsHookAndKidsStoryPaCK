import { Pressable, Text, View } from 'react-native';

import type { ToolDefinition } from '@/constants/features';

type ToolCardProps = {
  tool: ToolDefinition;
  onPress: () => void;
};

export function ToolCard({ tool, onPress }: ToolCardProps) {
  return (
    <Pressable onPress={onPress} className="mb-4 overflow-hidden rounded-3xl border border-white/10 bg-white/5">
      <View className="h-1 bg-nebula" />
      <View className="p-5">
        <View className="mb-3 flex-row items-center justify-between">
          <Text className="text-xl font-black text-white">{tool.shortTitle}</Text>
          {tool.uploadRequired ? (
            <Text className="rounded-full bg-amber-400/15 px-3 py-1 text-xs font-bold text-amber-100">
              Upload TODO
            </Text>
          ) : (
            <Text className="rounded-full bg-emerald-400/15 px-3 py-1 text-xs font-bold text-emerald-100">
              API mapped
            </Text>
          )}
        </View>
        <Text className="text-base leading-6 text-slate-300">{tool.description}</Text>
      </View>
    </Pressable>
  );
}
