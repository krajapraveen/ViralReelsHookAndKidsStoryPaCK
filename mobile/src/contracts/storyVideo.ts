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

const audienceValues = new Set(STORY_VIDEO_AUDIENCE_OPTIONS.map((option) => option.value));
const styleValues = new Set(STORY_VIDEO_STYLE_OPTIONS.map((option) => option.value));

const durationToQuality = (durationSeconds: number) => {
  if (durationSeconds <= 30) return 'fast';
  if (durationSeconds <= 60) return 'balanced';
  return 'high_quality';
};

export type StoryVideoApiPayload = {
  title: string;
  story_text: string;
  animation_style: string;
  age_group: string;
  voice_preset: string;
  quality_mode: string;
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
  duration: z.string().trim().min(1, 'Choose a duration.'),
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
  const durationMatch = data.duration.match(/\d+/);
  const durationSeconds = durationMatch ? Number(durationMatch[0]) : Number.NaN;
  const fields: FieldErrors = {};

  if (!Number.isFinite(durationSeconds) || durationSeconds < 15 || durationSeconds > 180) {
    fields.duration = 'Duration must be a number of seconds between 15 and 180.';
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
    quality_mode: durationToQuality(durationSeconds),
  };
}
