import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { Pressable, RefreshControl, ScrollView, Text } from 'react-native';

import { generationApi } from '@/api/generation';
import { Screen } from '@/components/Screen';
import { StateView } from '@/components/StateView';

export default function LibraryScreen() {
  const jobs = useQuery({ queryKey: ['library'], queryFn: generationApi.listLibrary });

  return (
    <Screen
      title="My videos"
      subtitle="Your generated videos, story jobs, and mobile-ready result links."
      scroll={false}
    >
      {jobs.isLoading ? (
        <StateView title="Loading library" loading />
      ) : jobs.isError ? (
        <StateView title="Library unavailable" message="The API request failed." actionLabel="Retry" onAction={() => jobs.refetch()} />
      ) : !jobs.data?.length ? (
        <StateView
          title="No creations yet"
          message="Start with Story Video, Reels, or Photo to Comic."
          actionLabel="Create something"
          onAction={() => router.push('/create')}
        />
      ) : (
        <ScrollView
          className="flex-1"
          refreshControl={<RefreshControl refreshing={jobs.isFetching} onRefresh={() => jobs.refetch()} />}
        >
          {jobs.data.map((job, index) => {
            const id = job.job_id || job.id || job._id || `${index}`;
            return (
              <Pressable
                key={id}
                onPress={() => router.push({ pathname: '/result/[jobId]', params: { jobId: id } })}
                className="mb-3 rounded-3xl border border-white/10 bg-white/5 p-4"
              >
                <Text className="text-lg font-black text-white">{job.title || job.type || 'Untitled creation'}</Text>
                <Text className="mt-1 text-sm text-slate-400">{job.status || 'UNKNOWN'}</Text>
                {job.prompt ? <Text className="mt-2 text-slate-300" numberOfLines={2}>{job.prompt}</Text> : null}
              </Pressable>
            );
          })}
        </ScrollView>
      )}
    </Screen>
  );
}
