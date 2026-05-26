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

const audienceAliases: Record<string, string> = {
  toddler: 'toddler',
  '2-4': 'toddler',
  'kids 2-4': 'toddler',
  'kids_2_4': 'toddler',
  '5-8': 'kids_5_8',
  '6-10': 'kids_5_8',
  'kids 5-8': 'kids_5_8',
  'kids_5_8': 'kids_5_8',
  '9-12': 'kids_9_12',
  'kids 9-12': 'kids_9_12',
  'kids_9_12': 'kids_9_12',
  teen: 'teen',
  teens: 'teen',
  '13+': 'teen',
  all: 'all_ages',
  'all ages': 'all_ages',
  all_ages: 'all_ages',
};

const styleAliases: Record<string, string> = {
  cartoon: 'cartoon_2d',
  '2d cartoon': 'cartoon_2d',
  cartoon_2d: 'cartoon_2d',
  anime: 'anime_style',
  anime_style: 'anime_style',
  '3d': '3d_pixar',
  '3d animation': '3d_pixar',
  pixar: '3d_pixar',
  '3d_pixar': '3d_pixar',
  watercolor: 'watercolor',
  comic: 'comic_book',
  'comic book': 'comic_book',
  comic_book: 'comic_book',
  claymation: 'claymation',
};

const durationToQuality = (durationSeconds: number) => {
  if (durationSeconds <= 30) return 'fast';
  if (durationSeconds <= 60) return 'balanced';
  return 'high_quality';
};

const normalizeToken = (value?: string) =>
  String(value || '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, ' ');

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
  audience: z.string().trim().min(1, 'Choose an audience category.'),
  style: z.string().trim().min(1, 'Choose a style preset.'),
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
  const audience = audienceAliases[normalizeToken(data.audience)];
  const style = styleAliases[normalizeToken(data.style)];
  const durationMatch = data.duration.match(/\d+/);
  const durationSeconds = durationMatch ? Number(durationMatch[0]) : Number.NaN;
  const fields: FieldErrors = {};

  if (!audience) {
    fields.audience = 'Unsupported audience. Use: 2-4, 5-8, 9-12, 13+, or all ages.';
  }
  if (!style) {
    fields.style = 'Unsupported style. Use: Cartoon, Anime, 3D Animation, Watercolor, Comic Book, or Claymation.';
  }
  if (!Number.isFinite(durationSeconds) || durationSeconds < 15 || durationSeconds > 180) {
    fields.duration = 'Duration must be a number of seconds between 15 and 180.';
  }
  if (Object.keys(fields).length) {
    throw new ContractValidationError(fields);
  }

  return {
    title: data.title.trim(),
    story_text: data.prompt.trim(),
    animation_style: style,
    age_group: audience,
    voice_preset: 'narrator_warm',
    quality_mode: durationToQuality(durationSeconds),
  };
}
