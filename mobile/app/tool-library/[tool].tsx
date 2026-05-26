import { useQuery } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import { Pressable, Text } from 'react-native';

import { generationApi } from '@/api/generation';
import { Screen } from '@/components/Screen';
import { StateView } from '@/components/StateView';
import { findTool } from '@/constants/features';
import type { ToolKey } from '@/types/api';

export default function ToolLibraryScreen() {
  const params = useLocalSearchParams<{ tool: ToolKey; q?: string; audience?: string; style?: string }>();
  const tool = findTool(params.tool);
  const items = useQuery({
    queryKey: ['tool-library', params.tool, params.q, params.audience, params.style],
    queryFn: () => generationApi.listToolItems(params.tool, {
      q: params.q,
      audience: params.audience,
      style: params.style,
    }),
    enabled: Boolean(tool),
  });

  return (
    <Screen
      title={tool?.shortTitle || 'Tool library'}
      subtitle={params.q ? 'Related media matched by prompt keywords, audience, and style.' : 'Feature-specific results from the existing API.'}
    >
      {items.isLoading ? (
        <StateView title="Loading" loading />
      ) : items.isError ? (
        <StateView title="Unable to load" message="This feature may need a mobile-specific list endpoint." />
      ) : !items.data?.length ? (
        <StateView title="Nothing here yet" message="Create a new item to populate this library." />
      ) : (
        items.data.map((item, index) => {
          const id = item.job_id || item.id || item._id || `${index}`;
          return (
            <Pressable
              key={id}
              onPress={() => router.push({ pathname: '/result/[jobId]', params: { jobId: id, tool: params.tool } })}
              className="mb-3 rounded-3xl border border-white/10 bg-white/5 p-4"
            >
              <Text className="text-lg font-black text-white">{item.title || 'Untitled'}</Text>
              <Text className="mt-1 text-sm text-slate-400">{item.status || 'Saved'}</Text>
            </Pressable>
          );
        })
      )}
    </Screen>
  );
}
