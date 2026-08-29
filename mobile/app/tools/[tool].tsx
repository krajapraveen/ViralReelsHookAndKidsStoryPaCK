import { useMutation } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import { useMemo, useState } from 'react';
import { Text, View } from 'react-native';

import { generationApi, type ToolSubmitPayload } from '@/api/generation';
import { normalizeApiError } from '@/api/client';
import { Button } from '@/components/Button';
import { Screen } from '@/components/Screen';
import { SelectField } from '@/components/SelectField';
import { StateView } from '@/components/StateView';
import { TextField } from '@/components/TextField';
import { findTool } from '@/constants/features';
import {
  STORY_VIDEO_AUDIENCE_OPTIONS,
  STORY_VIDEO_DURATION_OPTIONS,
  STORY_VIDEO_QUALITY_OPTIONS,
  STORY_VIDEO_STYLE_OPTIONS,
  type FieldErrors,
} from '@/contracts/storyVideo';
import type { ToolKey } from '@/types/api';

const fieldLabels: Record<keyof ToolSubmitPayload, string> = {
  title: 'Title',
  prompt: 'Prompt / Story',
  audience: 'Audience',
  style: 'Style',
  duration: 'Duration',
  quality_mode: 'Quality Mode',
  brand: 'Brand',
  characters: 'Characters',
};

const backendToFormField: Record<string, keyof ToolSubmitPayload> = {
  story_text: 'prompt',
  animation_style: 'style',
  age_group: 'audience',
  quality_mode: 'quality_mode',
};

const toFormFieldErrors = (fields: FieldErrors): FieldErrors =>
  Object.entries(fields).reduce<FieldErrors>((acc, [field, message]) => {
    acc[backendToFormField[field] || field] = message;
    return acc;
  }, {});

export default function ToolScreen() {
  const params = useLocalSearchParams<{ tool: string }>();
  const tool = useMemo(() => findTool(params.tool), [params.tool]);
  const [form, setForm] = useState<ToolSubmitPayload>({
    duration: '30',
    quality_mode: 'balanced',
    audience: 'kids_6_10',
    style: 'cartoon',
  });
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});

  const mutation = useMutation({
    mutationFn: () => {
      setFieldErrors({});
      return generationApi.submitTool(tool!.key, form);
    },
    onSuccess: (job) => {
      const jobId = job.job_id || job.id || job._id;
      if (jobId) {
        router.push({ pathname: '/result/[jobId]', params: { jobId, tool: tool!.key } });
      }
    },
    onError: (err) => {
      const normalized = normalizeApiError(err);
      const nextFields = normalized.fields ? toFormFieldErrors(normalized.fields) : {};
      setFieldErrors(nextFields);
      if (normalized.fields) {
        console.warn('[mobile.generate.validation_failed]', {
          tool: tool?.key,
          fields: nextFields,
          status: normalized.status,
          requestId: normalized.requestId,
        });
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

  const normalizedError = mutation.error ? normalizeApiError(mutation.error) : null;
  const error = normalizedError && !normalizedError.fields ? normalizedError.message : null;
  const hasRequiredFields = tool.fields.every((field) => (form[field] || '').trim().length > 0);
  const hasFieldErrors = Object.keys(fieldErrors).length > 0;
  const updateField = (field: keyof ToolSubmitPayload, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
    setFieldErrors((current) => {
      if (!current[field]) return current;
      const next = { ...current };
      delete next[field];
      return next;
    });
  };

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
        tool.key === 'story-video' && field === 'audience' ? (
          <SelectField
            key={field}
            label={fieldLabels[field]}
            value={form[field]}
            options={STORY_VIDEO_AUDIENCE_OPTIONS}
            error={fieldErrors[field]}
            onChange={(value) => updateField(field, value)}
          />
        ) : tool.key === 'story-video' && field === 'style' ? (
          <SelectField
            key={field}
            label={fieldLabels[field]}
            value={form[field]}
            options={STORY_VIDEO_STYLE_OPTIONS}
            error={fieldErrors[field]}
            onChange={(value) => updateField(field, value)}
          />
        ) : tool.key === 'story-video' && field === 'duration' ? (
          <SelectField
            key={field}
            label={fieldLabels[field]}
            value={form[field]}
            options={STORY_VIDEO_DURATION_OPTIONS}
            error={fieldErrors[field]}
            onChange={(value) => updateField(field, value)}
          />
        ) : tool.key === 'story-video' && field === 'quality_mode' ? (
          <SelectField
            key={field}
            label={fieldLabels[field]}
            value={form[field]}
            options={STORY_VIDEO_QUALITY_OPTIONS}
            error={fieldErrors[field]}
            onChange={(value) => updateField(field, value)}
          />
        ) : (
          <TextField
            key={field}
            label={fieldLabels[field]}
            value={form[field] || ''}
            onChangeText={(value) => updateField(field, value)}
            multiline={field === 'prompt' || field === 'characters'}
            error={fieldErrors[field]}
          />
        )
      ))}

      {tool.mobileNotes?.map((note) => (
        <Text key={note} className="mb-3 text-sm leading-5 text-slate-400">
          {note}
        </Text>
      ))}

      {error ? <Text className="mb-4 text-rose-300">{error}</Text> : null}
      <Button
        title={tool.uploadRequired ? 'API mapped - upload TODO' : 'Generate'}
        disabled={tool.uploadRequired || mutation.isPending || !hasRequiredFields || hasFieldErrors}
        loading={mutation.isPending}
        onPress={() => mutation.mutate()}
      />
      <View className="mt-3">
        <Button
          title="View related library"
          variant="secondary"
          onPress={() =>
            router.push({
              pathname: '/tool-library/[tool]',
              params: {
                tool: tool.key as ToolKey,
                q: form.prompt || '',
                audience: form.audience || '',
                style: form.style || '',
              },
            })
          }
        />
      </View>
    </Screen>
  );
}
