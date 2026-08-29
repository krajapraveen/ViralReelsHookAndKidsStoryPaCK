import { useMutation, useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';

import { storySeriesApi, type CreateSeriesPayload } from '@/api/storySeries';
import { normalizeApiError } from '@/api/client';
import { Button } from '@/components/Button';
import { Screen } from '@/components/Screen';
import { SelectField } from '@/components/SelectField';
import { StateView } from '@/components/StateView';
import { TextField } from '@/components/TextField';
import {
  SERIES_AUDIENCE_OPTIONS,
  SERIES_GENRE_OPTIONS,
  SERIES_STYLE_OPTIONS,
  SERIES_TOOL_OPTIONS,
  createSeriesSchema,
  fieldErrorsFromZod,
} from '@/contracts/storySeries';

export default function StorySeriesScreen() {
  const series = useQuery({ queryKey: ['story-series'], queryFn: storySeriesApi.list });
  const [form, setForm] = useState<CreateSeriesPayload>({
    title: '',
    initial_prompt: '',
    genre: 'adventure',
    audience: 'kids_5_8',
    style: 'cartoon_2d',
    tool: 'story_video',
  });
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const create = useMutation({
    mutationFn: async () => {
      const parsed = createSeriesSchema.safeParse(form);
      if (!parsed.success) {
        const errors = fieldErrorsFromZod(parsed.error);
        setFieldErrors(errors);
        throw new Error('Please fix the highlighted fields.');
      }
      setFieldErrors({});
      return storySeriesApi.create(parsed.data as CreateSeriesPayload);
    },
    onSuccess: async (data) => {
      await series.refetch();
      if (data.series_id) {
        router.push({ pathname: '/series/[seriesId]', params: { seriesId: data.series_id } });
      }
    },
  });

  const updateField = (field: keyof CreateSeriesPayload, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
    setFieldErrors((current) => {
      if (!current[field]) return current;
      const next = { ...current };
      delete next[field];
      return next;
    });
  };

  const error = create.error ? normalizeApiError(create.error).message : null;

  return (
    <Screen
      title="Story Series"
      subtitle="Build ongoing story universes with persistent characters, world bible, memory, and PLAN -> GENERATE episodes."
    >
      <View className="mb-6 rounded-3xl border border-white/10 bg-white/5 p-4">
        <Text className="mb-4 text-xl font-black text-white">Create series</Text>
        <TextField label="Title" value={form.title} onChangeText={(value) => updateField('title', value)} error={fieldErrors.title} />
        <TextField
          label="Initial prompt"
          value={form.initial_prompt}
          onChangeText={(value) => updateField('initial_prompt', value)}
          multiline
          error={fieldErrors.initial_prompt}
        />
        <SelectField label="Genre" value={form.genre} options={SERIES_GENRE_OPTIONS} error={fieldErrors.genre} onChange={(value) => updateField('genre', value)} />
        <SelectField label="Audience" value={form.audience} options={SERIES_AUDIENCE_OPTIONS} error={fieldErrors.audience} onChange={(value) => updateField('audience', value)} />
        <SelectField label="Style" value={form.style} options={SERIES_STYLE_OPTIONS} error={fieldErrors.style} onChange={(value) => updateField('style', value)} />
        <SelectField label="Tool" value={form.tool} options={SERIES_TOOL_OPTIONS} error={fieldErrors.tool} onChange={(value) => updateField('tool', value)} />
        {error ? <Text className="mb-3 text-rose-300">{error}</Text> : null}
        <Button title="Create Story Series" loading={create.isPending} onPress={() => create.mutate()} />
      </View>

      <Text className="mb-3 text-lg font-black text-white">My series</Text>
      {series.isLoading ? (
        <StateView title="Loading series" loading />
      ) : series.isError ? (
        <StateView title="Unable to load series" actionLabel="Retry" onAction={() => series.refetch()} />
      ) : !series.data?.series.length ? (
        <StateView title="No series yet" message="Create your first ongoing universe above." />
      ) : (
        series.data.series.map((item) => (
          <Pressable
            key={item.series_id}
            onPress={() => router.push({ pathname: '/series/[seriesId]', params: { seriesId: item.series_id } })}
            className="mb-3 rounded-3xl border border-white/10 bg-white/5 p-4"
          >
            <Text className="text-xl font-black text-white">{item.title}</Text>
            <Text className="mt-1 text-slate-300">
              {item.genre || 'series'} · {item.audience || item.audience_type || 'audience'} · {item.style || 'style'}
            </Text>
            <Text className="mt-2 text-sm text-slate-400">
              Episodes: {item.episode_count ?? item.total_episodes ?? 0} · Branches: {item.branch_count ?? 0} · Views: {item.view_count ?? 0}
            </Text>
            {item.latest_episode ? (
              <Text className="mt-2 text-sm text-aurora">
                Latest: Ep {item.latest_episode.episode_number} - {item.latest_episode.title || item.latest_episode.status}
              </Text>
            ) : null}
          </Pressable>
        ))
      )}
    </Screen>
  );
}
