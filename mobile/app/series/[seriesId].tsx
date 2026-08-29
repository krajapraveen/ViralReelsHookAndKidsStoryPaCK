import { useMutation, useQuery } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';

import { normalizeApiError } from '@/api/client';
import { storySeriesApi, type SeriesDirection, type StoryEpisode } from '@/api/storySeries';
import { Button } from '@/components/Button';
import { Screen } from '@/components/Screen';
import { SelectField } from '@/components/SelectField';
import { StateView } from '@/components/StateView';
import { TextField } from '@/components/TextField';
import { SERIES_DIRECTION_OPTIONS, fieldErrorsFromZod, planEpisodeSchema } from '@/contracts/storySeries';

const terminalStatuses = new Set(['ready', 'failed']);

function EpisodeCard({
  episode,
  seriesId,
  onGenerated,
  onMemory,
}: {
  episode: StoryEpisode;
  seriesId: string;
  onGenerated: () => void;
  onMemory: (episodeId: string) => void;
}) {
  const status = useQuery({
    queryKey: ['story-series-episode-status', seriesId, episode.episode_id],
    queryFn: () => storySeriesApi.episodeStatus(seriesId, episode.episode_id),
    enabled: Boolean(episode.episode_id) && !terminalStatuses.has(String(episode.status || '').toLowerCase()),
    refetchInterval: (query) => {
      const nextStatus = String(query.state.data?.status || episode.status || '').toLowerCase();
      return terminalStatuses.has(nextStatus) ? false : 4000;
    },
  });
  const current = status.data || episode;
  const generate = useMutation({
    mutationFn: () => storySeriesApi.generateEpisode(seriesId, episode.episode_id),
    onSuccess: onGenerated,
  });

  return (
    <View className="mb-3 rounded-3xl border border-white/10 bg-white/5 p-4">
      <Text className="text-lg font-black text-white">
        Ep {episode.episode_number ?? '?'} - {episode.title || 'Untitled episode'}
      </Text>
      <Text className="mt-1 text-sm font-semibold uppercase tracking-wide text-slate-400">
        {current.status || 'planned'} {typeof current.progress === 'number' ? `- ${current.progress}%` : ''}
      </Text>
      {episode.summary ? <Text className="mt-2 leading-6 text-slate-300">{episode.summary}</Text> : null}
      {episode.cliffhanger ? <Text className="mt-2 text-amber-100">Cliffhanger: {episode.cliffhanger}</Text> : null}
      {current.error_message ? <Text className="mt-2 text-rose-300">{current.error_message}</Text> : null}
      {current.output_asset_url ? (
        <Text className="mt-2 text-emerald-100">Output ready</Text>
      ) : null}
      <View className="mt-4 gap-2">
        {String(current.status || '').toLowerCase() === 'planned' || String(current.status || '').toLowerCase() === 'failed' ? (
          <Button title="Generate episode" loading={generate.isPending} onPress={() => generate.mutate()} />
        ) : null}
        {current.pipeline_job_id ? (
          <Button
            title="Open video job"
            variant="secondary"
            onPress={() => router.push({ pathname: '/result/[jobId]', params: { jobId: current.pipeline_job_id || '', tool: 'story-video' } })}
          />
        ) : null}
        {String(current.status || '').toLowerCase() === 'ready' ? (
          <Button title="Update memory" variant="secondary" onPress={() => onMemory(episode.episode_id)} />
        ) : null}
      </View>
    </View>
  );
}

export default function SeriesDetailScreen() {
  const params = useLocalSearchParams<{ seriesId: string }>();
  const seriesId = params.seriesId || '';
  const [direction, setDirection] = useState<SeriesDirection>('continue');
  const [customPrompt, setCustomPrompt] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState<string | null>(null);

  const detail = useQuery({
    queryKey: ['story-series-detail', seriesId],
    queryFn: () => storySeriesApi.get(seriesId),
    enabled: Boolean(seriesId),
  });
  const suggestions = useQuery({
    queryKey: ['story-series-suggestions', seriesId],
    queryFn: () => storySeriesApi.suggestions(seriesId),
    enabled: Boolean(seriesId),
  });
  const rewards = useQuery({
    queryKey: ['story-series-rewards', seriesId],
    queryFn: () => storySeriesApi.rewards(seriesId),
    enabled: Boolean(seriesId),
  });
  const extracted = useQuery({
    queryKey: ['story-series-extracted', seriesId],
    queryFn: () => storySeriesApi.extractedCharacters(seriesId),
    enabled: Boolean(seriesId),
  });

  const plan = useMutation({
    mutationFn: async () => {
      const parsed = planEpisodeSchema.safeParse({
        direction_type: direction,
        custom_prompt: customPrompt || undefined,
      });
      if (!parsed.success) {
        setFieldErrors(fieldErrorsFromZod(parsed.error));
        throw new Error('Please fix the highlighted fields.');
      }
      setFieldErrors({});
      return storySeriesApi.planEpisode(seriesId, parsed.data as { direction_type: SeriesDirection; custom_prompt?: string });
    },
    onSuccess: async (data) => {
      setMessage(`Episode ${data.episode_number || ''} planned${data.plan?._fallback ? ' using fallback planner' : ''}.`);
      setCustomPrompt('');
      await detail.refetch();
    },
  });
  const share = useMutation({
    mutationFn: () => storySeriesApi.share(seriesId, !(detail.data?.series?.is_public)),
    onSuccess: async (data) => {
      setMessage(data.share_url ? `Public share: ${data.share_url}` : 'Series sharing updated.');
      await detail.refetch();
    },
  });
  const memory = useMutation({
    mutationFn: (episodeId: string) => storySeriesApi.updateMemory(seriesId, episodeId),
    onSuccess: () => setMessage('Story memory updated.'),
  });
  const confirmCharacters = useMutation({
    mutationFn: () => {
      const ids = (extracted.data?.extracted_characters || [])
        .map((char: any) => char.character_id || char.id || char.name)
        .filter(Boolean);
      return storySeriesApi.confirmCharacters(seriesId, ids);
    },
    onSuccess: async () => {
      setMessage('Extracted characters confirmed.');
      await Promise.all([detail.refetch(), extracted.refetch()]);
    },
  });
  const dismissExtraction = useMutation({
    mutationFn: () => storySeriesApi.dismissExtraction(seriesId),
    onSuccess: async () => {
      setMessage('Character suggestions dismissed.');
      await extracted.refetch();
    },
  });

  const error = plan.error ? normalizeApiError(plan.error).message : null;

  return (
    <Screen title={detail.data?.series?.title || 'Story Series'} subtitle="Plan, generate, validate, save, and update story memory.">
      {detail.isLoading ? (
        <StateView title="Loading series" loading />
      ) : detail.isError || !detail.data ? (
        <StateView title="Unable to load series" actionLabel="Retry" onAction={() => detail.refetch()} />
      ) : (
        <>
          <View className="mb-5 rounded-3xl border border-white/10 bg-white/5 p-4">
            <Text className="text-sm font-semibold uppercase tracking-wide text-slate-400">Universe</Text>
            <Text className="mt-2 text-white">
              {detail.data.series.genre || 'genre'} · {detail.data.series.audience || detail.data.series.audience_type || 'audience'} · {detail.data.series.style || 'style'}
            </Text>
            <Text className="mt-2 text-slate-300">
              Episodes: {detail.data.episodes.length} · Branches: {detail.data.series.branch_count || 0} · Status: {detail.data.series.status || 'active'}
            </Text>
            <View className="mt-4">
              <Button
                title={detail.data.series.is_public ? 'Make private' : 'Share series publicly'}
                variant="secondary"
                loading={share.isPending}
                onPress={() => share.mutate()}
              />
            </View>
          </View>

          <View className="mb-5 rounded-3xl border border-white/10 bg-white/5 p-4">
            <Text className="mb-4 text-xl font-black text-white">Plan next episode</Text>
            <SelectField
              label="Direction"
              value={direction}
              options={SERIES_DIRECTION_OPTIONS}
              error={fieldErrors.direction_type}
              onChange={(value) => setDirection(value as SeriesDirection)}
            />
            <TextField
              label="Custom prompt"
              value={customPrompt}
              onChangeText={setCustomPrompt}
              multiline
              error={fieldErrors.custom_prompt}
              placeholder="Optional direction, suggestion, or open loop to explore"
            />
            {error ? <Text className="mb-3 text-rose-300">{error}</Text> : null}
            <Button title="Plan episode" loading={plan.isPending} onPress={() => plan.mutate()} />
          </View>

          {message ? <Text className="mb-4 text-center text-emerald-100">{message}</Text> : null}

          <Text className="mb-3 text-lg font-black text-white">Episodes</Text>
          {detail.data.episodes.length ? (
            detail.data.episodes.map((episode) => (
              <EpisodeCard
                key={episode.episode_id}
                episode={episode}
                seriesId={seriesId}
                onGenerated={() => detail.refetch()}
                onMemory={(episodeId) => memory.mutate(episodeId)}
              />
            ))
          ) : (
            <StateView title="No episodes yet" message="Plan the next episode to continue this universe." />
          )}

          <Text className="mb-3 mt-3 text-lg font-black text-white">Suggestions</Text>
          {suggestions.isLoading ? (
            <StateView title="Loading suggestions" loading />
          ) : suggestions.data?.length ? (
            suggestions.data.map((suggestion, index) => (
              <Pressable
                key={`${suggestion.title}-${index}`}
                onPress={() => {
                  setDirection((suggestion.direction_type || 'custom') as SeriesDirection);
                  setCustomPrompt(`${suggestion.title}: ${suggestion.description || ''}`);
                }}
                className="mb-3 rounded-3xl border border-white/10 bg-white/5 p-4"
              >
                <Text className="font-black text-white">{suggestion.title || 'Next episode idea'}</Text>
                <Text className="mt-2 text-slate-300">{suggestion.description}</Text>
              </Pressable>
            ))
          ) : (
            <StateView title="No suggestions yet" message="Suggestions appear from open loops and cliffhangers." />
          )}

          <Text className="mb-3 mt-3 text-lg font-black text-white">Characters and rewards</Text>
          {extracted.data?.extracted_characters?.length ? (
            <View className="mb-4 rounded-3xl border border-white/10 bg-white/5 p-4">
              <Text className="font-black text-white">Extracted characters ready for review</Text>
              <Text className="mt-2 text-slate-300">{extracted.data.extracted_characters.length} suggested characters</Text>
              <View className="mt-4 gap-2">
                <Button title="Confirm all suggestions" loading={confirmCharacters.isPending} onPress={() => confirmCharacters.mutate()} />
                <Button title="Dismiss extraction" variant="secondary" loading={dismissExtraction.isPending} onPress={() => dismissExtraction.mutate()} />
              </View>
            </View>
          ) : null}
          <View className="rounded-3xl border border-white/10 bg-white/5 p-4">
            <Text className="font-black text-white">Rewards</Text>
            <Text className="mt-2 text-slate-300">
              Episode count: {rewards.data?.episode_count ?? detail.data.episodes.length}
            </Text>
            {rewards.data?.next_milestone ? (
              <Text className="mt-2 text-amber-100">Next milestone: {JSON.stringify(rewards.data.next_milestone)}</Text>
            ) : null}
          </View>
        </>
      )}
    </Screen>
  );
}
