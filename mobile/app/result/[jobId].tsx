import { useMutation, useQuery } from '@tanstack/react-query';
import * as Clipboard from 'expo-clipboard';
import * as FileSystem from 'expo-file-system/legacy';
import * as Sharing from 'expo-sharing';
import { router, useLocalSearchParams } from 'expo-router';
import { Linking, Pressable, Text, View } from 'react-native';

import { generationApi } from '@/api/generation';
import { Button } from '@/components/Button';
import { Screen } from '@/components/Screen';
import { StateView } from '@/components/StateView';
import { VideoPreview } from '@/components/VideoPreview';
import type { ToolKey } from '@/types/api';

function pickVideoUrl(job: any) {
  return job?.playback_url || job?.video_url || job?.output_url || job?.download_url || job?.preview_url || job?.result?.video_url || job?.result?.output_url;
}

function pickShareUrl(job: any) {
  return job?.share_url || job?.public_share_url || job?.result?.share_url;
}

const statusLabels: Record<string, string> = {
  INIT: 'Queued',
  QUEUED: 'Queued',
  PLANNING: 'Writing script',
  BUILDING_CHARACTER_CONTEXT: 'Creating storyboard',
  PLANNING_SCENE_MOTION: 'Creating storyboard',
  GENERATING_KEYFRAMES: 'Generating images',
  GENERATING_SCENE_CLIPS: 'Generating images',
  GENERATING_AUDIO: 'Adding narration',
  ASSEMBLING_VIDEO: 'Rendering video',
  VALIDATING: 'Uploading video',
  READY: 'Completed',
  PARTIAL_READY: 'Completed',
  FAILED: 'Failed',
  FAILED_PLANNING: 'Failed',
  FAILED_IMAGES: 'Failed',
  FAILED_TTS: 'Failed',
  FAILED_RENDER: 'Failed',
};

const waitingQuotes = [
  'Great stories take a moment to render.',
  'Your scenes are being stitched into something cinematic.',
  'Consistency, characters, narration, and motion are coming together.',
];

const relatedTools = [
  { label: 'Character Memory', route: 'character-memory' },
  { label: 'Comic Storybook', route: 'comic-storybook' },
  { label: 'Daily Viral Ideas', route: 'daily-viral-ideas' },
];

function getStatus(job: any, hasPlayableUrl: boolean) {
  const raw = job?.state || job?.status || '';
  const normalized = String(raw).toUpperCase();
  const rawProgress = Math.max(0, Math.min(100, Number(job?.progress ?? job?.progress_percent ?? 0)));
  const backendCompleted = ['READY', 'PARTIAL_READY', 'COMPLETED'].includes(normalized);
  const finalizing = backendCompleted && !hasPlayableUrl;
  const progress = finalizing ? Math.min(rawProgress || 98, 98) : rawProgress;
  return {
    raw: normalized,
    label: finalizing ? 'Finalizing video' : statusLabels[normalized] || job?.current_step || job?.current_stage || 'Queued',
    progress,
    terminal: !finalizing && ['READY', 'PARTIAL_READY', 'COMPLETED', 'FAILED', 'FAILED_PLANNING', 'FAILED_IMAGES', 'FAILED_TTS', 'FAILED_RENDER', 'CANCELLED'].includes(normalized),
    failed: normalized.startsWith('FAILED') || normalized === 'CANCELLED',
    completed: backendCompleted && hasPlayableUrl,
    finalizing,
  };
}

export default function ResultScreen() {
  const params = useLocalSearchParams<{ jobId: string; tool?: ToolKey }>();
  const tool = params.tool || 'story-video';
  const jobId = params.jobId;

  const job = useQuery({
    queryKey: ['job', tool, jobId],
    queryFn: () => generationApi.getToolJob(tool, jobId),
    refetchInterval: (query) => {
      const status = getStatus(query.state.data, Boolean(pickVideoUrl(query.state.data)));
      return status.terminal ? false : 2500;
    },
  });

  const share = useMutation({
    mutationFn: async () => {
      const created = pickShareUrl(job.data) ? null : await generationApi.createShareLink(jobId);
      const url = pickShareUrl(job.data) || created?.share_url || created?.url || '';
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
  const shareUrl = pickShareUrl(job.data);
  const hasValidVideoUrl = Boolean(videoUrl && /^https?:\/\//.test(videoUrl));
  const status = getStatus(job.data, hasValidVideoUrl);
  const canShare = Boolean(shareUrl);
  const canDownload = status.completed && Boolean(videoUrl);
  const quote = waitingQuotes[Math.abs(jobId.length + status.progress) % waitingQuotes.length];

  const openSocialShare = async (platform: 'whatsapp' | 'x' | 'facebook') => {
    const url = shareUrl || videoUrl;
    if (!url) return;
    const text = encodeURIComponent(`Watch my Visionary Suite video: ${url}`);
    const encodedUrl = encodeURIComponent(url);
    const targets = {
      whatsapp: `whatsapp://send?text=${text}`,
      x: `https://twitter.com/intent/tweet?text=${text}`,
      facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`,
    };
    await Linking.openURL(targets[platform]);
  };

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
            <Text className="mt-1 text-2xl font-black text-white">
              {status.label} - {status.progress}%
            </Text>
            <View className="mt-4 h-3 overflow-hidden rounded-full bg-white/10">
              <View className="h-full rounded-full bg-aurora" style={{ width: `${status.progress}%` }} />
            </View>
            {job.data?.render_queue?.position ? (
              <Text className="mt-2 text-sm text-slate-300">
                Render queue position: {job.data.render_queue.position}
              </Text>
            ) : null}
            {job.data?.error || job.data?.error_message || job.data?.detail ? (
              <Text className="mt-2 text-rose-300">{job.data.error || job.data.error_message || job.data.detail}</Text>
            ) : null}
          </View>
          {hasValidVideoUrl ? (
            <VideoPreview uri={videoUrl} onRetry={() => job.refetch()} />
          ) : (
            <VideoPreview onRetry={() => job.refetch()} />
          )}
          {!hasValidVideoUrl && status.finalizing ? (
            <Text className="mt-3 text-center text-slate-300">
              Finalizing video URL. We will keep checking every few seconds.
            </Text>
          ) : null}
          {!status.completed && !status.failed ? (
            <View className="mt-5 rounded-3xl border border-white/10 bg-white/5 p-4">
              <Text className="text-lg font-black text-white">{quote}</Text>
              <Text className="mt-2 leading-6 text-slate-300">
                We'll notify you when your video is completed. Explore other Visionary Suite tools while we generate your video.
              </Text>
              <View className="mt-4 flex-row flex-wrap gap-2">
                {relatedTools.map((toolCard) => (
                  <Pressable
                    key={toolCard.route}
                    onPress={() => router.push(`/tools/${toolCard.route}` as never)}
                    className="rounded-2xl border border-white/10 bg-white/5 px-3 py-2"
                  >
                    <Text className="font-semibold text-slate-200">{toolCard.label}</Text>
                  </Pressable>
                ))}
              </View>
            </View>
          ) : null}
          <View className="mt-5 gap-3">
            <Button title="Copy/share link" variant="secondary" disabled={!canShare} loading={share.isPending} onPress={() => share.mutate()} />
            <View className="flex-row gap-2">
              <View className="flex-1"><Button title="WhatsApp" variant="secondary" disabled={!canShare} onPress={() => openSocialShare('whatsapp')} /></View>
              <View className="flex-1"><Button title="X" variant="secondary" disabled={!canShare} onPress={() => openSocialShare('x')} /></View>
              <View className="flex-1"><Button title="Facebook" variant="secondary" disabled={!canShare} onPress={() => openSocialShare('facebook')} /></View>
            </View>
            <Button title="Download/share MP4" variant="secondary" disabled={!canDownload} loading={download.isPending} onPress={() => download.mutate()} />
            <Text className="text-center text-xs text-slate-400">
              Platform file sharing supports WhatsApp, Instagram, TikTok, YouTube, Facebook, X, and any app installed in the native share sheet.
            </Text>
            <Button title="Refresh status" onPress={() => job.refetch()} />
          </View>
          {share.data ? <Text className="mt-3 text-emerald-100">Link copied.</Text> : null}
          {download.data ? <Text className="mt-3 text-emerald-100">Downloaded to app documents.</Text> : null}
        </>
      )}
    </Screen>
  );
}
