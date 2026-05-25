import type { ToolKey } from '@/types/api';

export type ToolDefinition = {
  key: ToolKey;
  title: string;
  shortTitle: string;
  description: string;
  route: string;
  api: {
    create?: string;
    status?: string;
    list?: string;
    config?: string;
    method?: 'GET' | 'POST';
  };
  fields: Array<'title' | 'prompt' | 'audience' | 'style' | 'duration' | 'brand' | 'characters'>;
  mobileNotes?: string[];
  uploadRequired?: boolean;
};

export const CREATOR_TOOLS: ToolDefinition[] = [
  {
    key: 'story-video',
    title: 'Story Video generation',
    shortTitle: 'Story Video',
    description: 'Turn an idea into a cinematic AI story video.',
    route: '/tools/story-video',
    api: {
      create: '/api/story-engine/create',
      status: '/api/story-engine/status/{jobId}',
      list: '/api/story-engine/user-jobs',
    },
    fields: ['title', 'prompt', 'audience', 'style', 'duration'],
  },
  {
    key: 'story-series',
    title: 'Story Series',
    shortTitle: 'Series',
    description: 'Create multi-episode sagas with persistent world memory.',
    route: '/tools/story-series',
    api: {
      create: '/api/story-series/create',
      list: '/api/story-series/my-series',
    },
    fields: ['title', 'prompt', 'audience', 'characters'],
  },
  {
    key: 'photo-trailer',
    title: 'My Movie Trailer / Photo Trailer',
    shortTitle: 'Trailer',
    description: 'Use photos to generate a personalized trailer.',
    route: '/tools/photo-trailer',
    api: {
      create: '/api/photo-trailer/jobs',
      status: '/api/photo-trailer/jobs/{jobId}',
      list: '/api/photo-trailer/my-trailers',
    },
    fields: ['title', 'prompt', 'style', 'duration'],
    uploadRequired: true,
    mobileNotes: ['Native image picking and upload handoff are marked TODO until multipart contracts are validated.'],
  },
  {
    key: 'character-memory',
    title: 'Character Memory',
    shortTitle: 'Characters',
    description: 'Build reusable characters with memory, portraits, and continuity.',
    route: '/tools/character-memory',
    api: {
      create: '/api/characters/create',
      list: '/api/characters/my-characters',
    },
    fields: ['title', 'prompt', 'style', 'characters'],
  },
  {
    key: 'reel-generator',
    title: 'Reel Generator',
    shortTitle: 'Reels',
    description: 'Generate viral short-form video scripts and reels.',
    route: '/tools/reel-generator',
    api: {
      create: '/api/generate/reel',
      status: '/api/generate/{jobId}',
      list: '/api/generate/',
    },
    fields: ['title', 'prompt', 'audience', 'style', 'duration'],
  },
  {
    key: 'photo-to-comic',
    title: 'Photo to Comic',
    shortTitle: 'Comic',
    description: 'Transform photos into stylized comic panels.',
    route: '/tools/photo-to-comic',
    api: {
      create: '/api/photo-to-comic/generate',
      status: '/api/photo-to-comic/job/{jobId}',
      list: '/api/photo-to-comic/history',
    },
    fields: ['title', 'prompt', 'style'],
    uploadRequired: true,
  },
  {
    key: 'comic-storybook',
    title: 'Comic Storybook',
    shortTitle: 'Storybook',
    description: 'Create illustrated storybooks panel by panel.',
    route: '/tools/comic-storybook',
    api: {
      create: '/api/comic-storybook-v2/generate',
      status: '/api/comic-storybook-v2/job/{jobId}',
      list: '/api/comic-storybook-v2/history',
      config: '/api/comic-storybook-v2/genres',
    },
    fields: ['title', 'prompt', 'audience', 'style', 'characters'],
  },
  {
    key: 'bedtime-stories',
    title: 'Bedtime Stories',
    shortTitle: 'Bedtime',
    description: 'Generate narrated bedtime stories with safe themes.',
    route: '/tools/bedtime-stories',
    api: {
      create: '/api/bedtime-story-builder/generate',
      config: '/api/bedtime-story-builder/config',
    },
    fields: ['title', 'prompt', 'audience', 'style'],
  },
  {
    key: 'reaction-gif',
    title: 'Reaction GIF',
    shortTitle: 'GIF',
    description: 'Create expressive reaction GIFs from photos.',
    route: '/tools/reaction-gif',
    api: {
      create: '/api/reaction-gif/generate',
      status: '/api/reaction-gif/job/{jobId}',
      list: '/api/reaction-gif/history',
      config: '/api/reaction-gif/reactions',
    },
    fields: ['title', 'prompt', 'style'],
    uploadRequired: true,
  },
  {
    key: 'brand-story',
    title: 'Brand Story',
    shortTitle: 'Brand',
    description: 'Turn positioning into a cinematic brand narrative.',
    route: '/tools/brand-story',
    api: {
      create: '/api/brand-story-builder/generate',
      status: '/api/brand-story-builder/job/{jobId}',
      config: '/api/brand-story-builder/config',
    },
    fields: ['title', 'prompt', 'audience', 'brand', 'style'],
  },
  {
    key: 'daily-viral-ideas',
    title: 'Daily Viral Ideas',
    shortTitle: 'Ideas',
    description: 'Get trend-aware prompts and content angles.',
    route: '/tools/daily-viral-ideas',
    api: {
      create: '/api/viral-ideas/generate-bundle',
      status: '/api/viral-ideas/jobs/{jobId}',
      list: '/api/viral-ideas/daily-feed',
    },
    fields: ['prompt', 'audience', 'style'],
  },
];

export const findTool = (key?: string) => CREATOR_TOOLS.find((tool) => tool.key === key);
