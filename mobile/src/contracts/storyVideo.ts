import { z } from 'zod';

import type { ToolSubmitPayload } from '@/api/generation';

export const STORY_VIDEO_API_CONTRACT = {
  endpoint: '/api/story-engine/create',
  requiredFields: ['title', 'story_text', 'animation_style', 'age_group', 'voice_preset', 'quality_mode'],
  stateMachine: [
    'queued',
    'scripting',
    'storyboard',
    'image_generation',
    'narration',
    'soundtrack',
    'rendering',
    'uploading',
    'completed',
  ],
  failureStates: ['moderation_failed', 'render_failed', 'timeout', 'insufficient_credits'],
} as const;

export type StoryVideoOption = {
  label: string;
  value: string;
};

export const STORY_VIDEO_AUDIENCE_OPTIONS: StoryVideoOption[] = [
  { label: '3-5 years', value: 'preschool_3_5' },
  { label: '6-10 years', value: 'kids_6_10' },
  { label: '11-14 years', value: 'tweens_11_14' },
  { label: 'Teens', value: 'teens' },
  { label: 'Family', value: 'family' },
  { label: 'General', value: 'general' },
];

export const STORY_VIDEO_STYLE_OPTIONS: StoryVideoOption[] = [
  { label: 'Cartoon', value: 'cartoon' },
  { label: 'Cinematic', value: 'cinematic' },
  { label: 'Anime', value: 'anime' },
  { label: '3D Animation', value: '3d_animation' },
  { label: 'Realistic', value: 'realistic' },
  { label: 'Comic Book', value: 'comic_book' },
  { label: 'Watercolor', value: 'watercolor' },
  { label: 'Kids Storybook', value: 'kids_storybook' },
];

export const STORY_VIDEO_DURATION_OPTIONS: StoryVideoOption[] = [
  { label: '30 seconds', value: '30' },
  { label: '45 seconds', value: '45' },
  { label: '60 seconds', value: '60' },
];

export const STORY_VIDEO_QUALITY_OPTIONS: StoryVideoOption[] = [
  { label: 'Fast - 1-2 min', value: 'fast' },
  { label: 'Balanced - 2-4 min', value: 'balanced' },
  { label: 'High Quality - 4-8 min', value: 'high_quality' },
];

const audienceValues = new Set(STORY_VIDEO_AUDIENCE_OPTIONS.map((option) => option.value));
const styleValues = new Set(STORY_VIDEO_STYLE_OPTIONS.map((option) => option.value));
const durationValues = new Set(STORY_VIDEO_DURATION_OPTIONS.map((option) => option.value));
const qualityValues = new Set(STORY_VIDEO_QUALITY_OPTIONS.map((option) => option.value));

export type StoryVideoApiPayload = {
  title: string;
  story_text: string;
  animation_style: string;
  age_group: string;
  voice_preset: string;
  quality_mode: string;
  duration_seconds: number;
};

export type FieldErrors = Record<string, string>;

export class ContractValidationError extends Error {
  fields: FieldErrors;

  constructor(fields: FieldErrors) {
    super('Please fix the highlighted fields.');
    this.name = 'ContractValidationError';
    this.fields = fields;
  }
}

const storyVideoFormSchema = z.object({
  title: z.string().trim().min(3, 'Title must be at least 3 characters.').max(100, 'Title must be under 100 characters.'),
  prompt: z
    .string()
    .trim()
    .min(50, 'Prompt must be at least 50 characters for Story Video generation.')
    .max(10000, 'Prompt must be under 10,000 characters.'),
  audience: z.string().refine((value) => audienceValues.has(value), 'Choose a supported audience category.'),
  style: z.string().refine((value) => styleValues.has(value), 'Choose a supported style preset.'),
  duration: z.string().refine((value) => durationValues.has(value), 'Choose 30, 45, or 60 seconds.'),
  quality_mode: z.string().default('balanced').refine((value) => qualityValues.has(value), 'Choose Fast, Balanced, or High Quality.'),
});

export function fieldErrorsFromZod(error: z.ZodError): FieldErrors {
  return error.issues.reduce<FieldErrors>((fields, issue) => {
    const key = String(issue.path[0] || 'form');
    fields[key] = issue.message;
    return fields;
  }, {});
}

export function normalizeStoryVideoPayload(form: ToolSubmitPayload): StoryVideoApiPayload {
  const parsed = storyVideoFormSchema.safeParse(form);
  if (!parsed.success) {
    throw new ContractValidationError(fieldErrorsFromZod(parsed.error));
  }

  const data = parsed.data;
  const durationSeconds = Number(data.duration);
  const fields: FieldErrors = {};

  if (!Number.isFinite(durationSeconds) || durationSeconds < 15 || durationSeconds > 180) {
    fields.duration = 'Choose 30, 45, or 60 seconds.';
  }
  if (Object.keys(fields).length) {
    throw new ContractValidationError(fields);
  }

  return {
    title: data.title.trim(),
    story_text: data.prompt.trim(),
    animation_style: data.style,
    age_group: data.audience,
    voice_preset: 'narrator_warm',
    quality_mode: data.quality_mode,
    duration_seconds: durationSeconds,
  };
}
