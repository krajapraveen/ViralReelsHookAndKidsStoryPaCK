import { z } from 'zod';

import type { SelectOption } from '@/components/SelectField';

export const SERIES_STYLE_OPTIONS: SelectOption[] = [
  { label: '2D Cartoon', value: 'cartoon_2d' },
  { label: 'Anime', value: 'anime' },
  { label: 'Watercolor', value: 'watercolor' },
  { label: 'Cinematic', value: 'cinematic' },
  { label: 'Comic', value: 'comic' },
  { label: 'Cartoon Fun', value: 'cartoon_fun' },
  { label: 'Kids Storybook', value: 'kids_storybook' },
  { label: 'Bold Superhero', value: 'bold_superhero' },
  { label: 'Soft Manga', value: 'soft_manga' },
  { label: 'Cute Chibi', value: 'cute_chibi' },
  { label: 'Retro Action', value: 'retro_action' },
  { label: 'Noir Comic', value: 'noir_comic' },
  { label: 'Sci-Fi Neon', value: 'scifi_neon' },
  { label: 'Cyberpunk Comic', value: 'cyberpunk_comic' },
  { label: 'Magical Fantasy', value: 'magical_fantasy' },
  { label: 'Dreamy Pastel', value: 'dreamy_pastel' },
  { label: 'Black & White Ink', value: 'black_white_ink' },
];

export const SERIES_AUDIENCE_OPTIONS: SelectOption[] = [
  { label: 'Kids 5-8', value: 'kids_5_8' },
  { label: 'Kids 9-12', value: 'kids_9_12' },
  { label: 'Teens', value: 'teen' },
  { label: 'Family', value: 'family' },
  { label: 'General', value: 'general' },
];

export const SERIES_GENRE_OPTIONS: SelectOption[] = [
  { label: 'Adventure', value: 'adventure' },
  { label: 'Fantasy', value: 'fantasy' },
  { label: 'Mystery', value: 'mystery' },
  { label: 'Comedy', value: 'comedy' },
  { label: 'Sci-Fi', value: 'sci_fi' },
  { label: 'Bedtime', value: 'bedtime' },
];

export const SERIES_TOOL_OPTIONS: SelectOption[] = [
  { label: 'Story Video', value: 'story_video' },
  { label: 'Comic', value: 'comic' },
];

export const SERIES_DIRECTION_OPTIONS: SelectOption[] = [
  { label: 'Continue', value: 'continue' },
  { label: 'Twist', value: 'twist' },
  { label: 'Raise Stakes', value: 'stakes' },
  { label: 'Flashback', value: 'flashback' },
  { label: 'Spinoff', value: 'spinoff' },
  { label: 'Custom', value: 'custom' },
];

const values = (options: SelectOption[]) => new Set(options.map((option) => option.value));

export const createSeriesSchema = z.object({
  title: z.string().trim().min(3, 'Series title must be at least 3 characters.').max(100),
  initial_prompt: z.string().trim().min(20, 'Initial prompt must be at least 20 characters.').max(5000),
  genre: z.string().refine((value) => values(SERIES_GENRE_OPTIONS).has(value), 'Choose a supported genre.'),
  audience: z.string().refine((value) => values(SERIES_AUDIENCE_OPTIONS).has(value), 'Choose a supported audience.'),
  style: z.string().refine((value) => values(SERIES_STYLE_OPTIONS).has(value), 'Choose a supported style.'),
  tool: z.string().refine((value) => values(SERIES_TOOL_OPTIONS).has(value), 'Choose Story Video or Comic.'),
});

export const planEpisodeSchema = z.object({
  direction_type: z.string().refine((value) => values(SERIES_DIRECTION_OPTIONS).has(value), 'Choose a supported direction.'),
  custom_prompt: z.string().trim().max(2000).optional(),
});

export const fieldErrorsFromZod = (error: z.ZodError) =>
  error.issues.reduce<Record<string, string>>((fields, issue) => {
    fields[String(issue.path[0] || 'form')] = issue.message;
    return fields;
  }, {});
