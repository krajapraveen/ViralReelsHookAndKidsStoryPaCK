import { useMutation } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import { useMemo, useState } from 'react';
import { Text, View } from 'react-native';

import { generationApi, type ToolSubmitPayload } from '@/api/generation';
import { normalizeApiError } from '@/api/client';
import { Button } from '@/components/Button';
import { Screen } from '@/components/Screen';
import { StateView } from '@/components/StateView';
import { TextField } from '@/components/TextField';
import { findTool } from '@/constants/features';
import type { ToolKey } from '@/types/api';

const fieldLabels: Record<keyof ToolSubmitPayload, string> = {
  title: 'Title',
  prompt: 'Prompt',
  audience: 'Audience',
  style: 'Style',
  duration: 'Duration',
  brand: 'Brand',
  characters: 'Characters',
};

export default function ToolScreen() {
  const params = useLocalSearchParams<{ tool: string }>();
  const tool = useMemo(() => findTool(params.tool), [params.tool]);
  const [form, setForm] = useState<ToolSubmitPayload>({
    duration: '30 seconds',
  });

  const mutation = useMutation({
    mutationFn: () => generationApi.submitTool(tool!.key, form),
    onSuccess: (job) => {
      const jobId = job.job_id || job.id || job._id;
      if (jobId) {
        router.push({ pathname: '/result/[jobId]', params: { jobId, tool: tool!.key } });
      }
    },
  });

  if (!tool) {
    return (
      <Screen title="Tool not found">
        <StateView title="Unknown tool" message="This mobile route is not mapped to an audited feature." />
      </Screen>
    );
  }

  const error = mutation.error ? normalizeApiError(mutation.error).message : null;

  return (
    <Screen title={tool.title} subtitle={tool.description}>
      {tool.uploadRequired ? (
        <View className="mb-5 rounded-3xl border border-amber-400/20 bg-amber-400/10 p-4">
          <Text className="font-bold text-amber-100">Native upload TODO</Text>
          <Text className="mt-2 leading-6 text-amber-100/80">
            The existing API is mapped, but this flow needs native image picker and multipart upload validation before
            enabling production submission.
          </Text>
        </View>
      ) : null}

      {tool.fields.map((field) => (
        <TextField
          key={field}
          label={fieldLabels[field]}
          value={form[field] || ''}
          onChangeText={(value) => setForm((current) => ({ ...current, [field]: value }))}
          multiline={field === 'prompt' || field === 'characters'}
        />
      ))}

      {tool.mobileNotes?.map((note) => (
        <Text key={note} className="mb-3 text-sm leading-5 text-slate-400">
          {note}
        </Text>
      ))}

      {error ? <Text className="mb-4 text-rose-300">{error}</Text> : null}
      <Button
        title={tool.uploadRequired ? 'API mapped - upload TODO' : 'Generate'}
        disabled={tool.uploadRequired || mutation.isPending || !form.prompt}
        loading={mutation.isPending}
        onPress={() => mutation.mutate()}
      />
      <View className="mt-3">
        <Button
          title="View related library"
          variant="secondary"
          onPress={() => router.push({ pathname: '/tool-library/[tool]', params: { tool: tool.key as ToolKey } })}
        />
      </View>
    </Screen>
  );
}
