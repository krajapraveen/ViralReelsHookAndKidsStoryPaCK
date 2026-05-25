import { useMutation, useQuery } from '@tanstack/react-query';
import * as Clipboard from 'expo-clipboard';
import * as FileSystem from 'expo-file-system';
import * as Sharing from 'expo-sharing';
import { useLocalSearchParams } from 'expo-router';
import { Text, View } from 'react-native';

import { generationApi } from '@/api/generation';
import { Button } from '@/components/Button';
import { Screen } from '@/components/Screen';
import { StateView } from '@/components/StateView';
import { VideoPreview } from '@/components/VideoPreview';
import type { ToolKey } from '@/types/api';

function pickVideoUrl(job: any) {
  return job?.video_url || job?.output_url || job?.download_url || job?.result?.video_url || job?.result?.output_url;
}

export default function ResultScreen() {
  const params = useLocalSearchParams<{ jobId: string; tool?: ToolKey }>();
  const tool = params.tool || 'story-video';
  const jobId = params.jobId;

  const job = useQuery({
    queryKey: ['job', tool, jobId],
    queryFn: () => generationApi.getToolJob(tool, jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return generationApi.isTerminal(status) ? false : 5000;
    },
  });

  const share = useMutation({
    mutationFn: async () => {
      const existingUrl = job.data?.share_url || pickVideoUrl(job.data);
      const created = existingUrl ? null : await generationApi.createShareLink(jobId);
      const url = existingUrl || created?.share_url || created?.url || '';
      if (url) {
        await Clipboard.setStringAsync(url);
        if (await Sharing.isAvailableAsync()) {
          await Sharing.shareAsync(url);
        }
      }
      return url;
    },
  });

  const download = useMutation({
    mutationFn: async () => {
      const url = pickVideoUrl(job.data);
      if (!url) throw new Error('No downloadable media URL is available yet.');
      const target = `${FileSystem.documentDirectory}${jobId}.mp4`;
      const result = await FileSystem.downloadAsync(url, target);
      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(result.uri);
      }
      return result.uri;
    },
  });

  const videoUrl = pickVideoUrl(job.data);

  return (
    <Screen title="Video result" subtitle={`Job ${jobId}`}>
      {job.isLoading ? (
        <StateView title="Loading result" message="Checking job status." loading />
      ) : job.isError ? (
        <StateView title="Result unavailable" message="The status API failed or this job belongs to another tool." />
      ) : (
        <>
          <View className="mb-4 rounded-3xl border border-white/10 bg-white/5 p-4">
            <Text className="text-sm font-semibold uppercase tracking-wide text-slate-400">Status</Text>
            <Text className="mt-1 text-2xl font-black text-white">{job.data?.status || 'UNKNOWN'}</Text>
            {job.data?.error || job.data?.detail ? (
              <Text className="mt-2 text-rose-300">{job.data.error || job.data.detail}</Text>
            ) : null}
          </View>
          <VideoPreview uri={videoUrl} />
          <View className="mt-5 gap-3">
            <Button title="Copy/share link" variant="secondary" loading={share.isPending} onPress={() => share.mutate()} />
            <Button title="Download/share file" variant="secondary" loading={download.isPending} onPress={() => download.mutate()} />
            <Button title="Refresh status" onPress={() => job.refetch()} />
          </View>
          {share.data ? <Text className="mt-3 text-emerald-100">Link copied.</Text> : null}
          {download.data ? <Text className="mt-3 text-emerald-100">Downloaded to app documents.</Text> : null}
        </>
      )}
    </Screen>
  );
}
