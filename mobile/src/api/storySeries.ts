import { api } from './client';

export type SeriesTool = 'story_video' | 'comic';
export type SeriesDirection = 'continue' | 'twist' | 'stakes' | 'flashback' | 'spinoff' | 'custom';

export type CreateSeriesPayload = {
  title: string;
  initial_prompt: string;
  genre: string;
  audience: string;
  style: string;
  tool: SeriesTool;
};

export type StorySeriesSummary = {
  series_id: string;
  title: string;
  genre?: string;
  audience?: string;
  audience_type?: string;
  style?: string;
  root_tool?: SeriesTool;
  episode_count?: number;
  branch_count?: number;
  view_count?: number;
  is_public?: boolean;
  status?: 'active' | 'paused' | 'archived' | string;
  cover_url?: string;
  latest_episode?: StoryEpisode;
  ready_count?: number;
  total_episodes?: number;
  next_episode?: StoryEpisode;
  next_hook?: string;
};

export type StoryEpisode = {
  episode_id: string;
  episode_number?: number;
  title?: string;
  summary?: string;
  status?: 'planned' | 'generating' | 'validating' | 'ready' | 'failed' | string;
  output_asset_url?: string;
  thumbnail_url?: string;
  pipeline_job_id?: string;
  current_stage?: string;
  progress?: number;
  error_message?: string;
  cliffhanger?: string;
  is_branch?: boolean;
  branch_type?: string;
  parent_episode_id?: string;
  plan?: {
    scene_breakdown?: Array<Record<string, unknown>>;
    cliffhanger?: Record<string, unknown> | string;
  };
};

export type StorySeriesDetail = {
  series: StorySeriesSummary;
  episodes: StoryEpisode[];
  character_bible?: Record<string, any>;
  world_bible?: Record<string, any>;
  story_memory?: Record<string, any>;
};

const unwrap = <T>(data: any, key: string): T => data?.[key] ?? data;

export const storySeriesApi = {
  async list() {
    const response = await api.get('/api/story-series/my-series');
    return {
      series: (response.data?.series || []) as StorySeriesSummary[],
      total: Number(response.data?.total || 0),
    };
  },
  async create(payload: CreateSeriesPayload) {
    const response = await api.post('/api/story-series/create', payload);
    return response.data as { success?: boolean; series_id?: string; duplicate?: boolean; episode_id?: string };
  },
  async get(seriesId: string): Promise<StorySeriesDetail> {
    const response = await api.get(`/api/story-series/${encodeURIComponent(seriesId)}`);
    return unwrap<StorySeriesDetail>(response.data, 'data');
  },
  async planEpisode(seriesId: string, payload: { direction_type: SeriesDirection; custom_prompt?: string }) {
    const response = await api.post(`/api/story-series/${encodeURIComponent(seriesId)}/plan-episode`, payload);
    return response.data as { success?: boolean; episode_id?: string; episode_number?: number; plan?: Record<string, unknown>; status?: string };
  },
  async generateEpisode(seriesId: string, episodeId: string) {
    const response = await api.post(`/api/story-series/${encodeURIComponent(seriesId)}/generate-episode`, { episode_id: episodeId });
    return response.data as { success?: boolean; episode_id?: string; pipeline_job_id?: string; status?: string; tool?: SeriesTool };
  },
  async episodeStatus(seriesId: string, episodeId: string): Promise<StoryEpisode> {
    const response = await api.get(`/api/story-series/${encodeURIComponent(seriesId)}/episode/${encodeURIComponent(episodeId)}/status`);
    return response.data as StoryEpisode;
  },
  async suggestions(seriesId: string) {
    const response = await api.post(`/api/story-series/${encodeURIComponent(seriesId)}/suggestions`);
    return (response.data?.suggestions || []) as Array<{
      title?: string;
      description?: string;
      direction_type?: SeriesDirection;
      excitement_level?: string;
      emoji?: string;
    }>;
  },
  async updateMemory(seriesId: string, episodeId: string) {
    const response = await api.post(`/api/story-series/${encodeURIComponent(seriesId)}/update-memory`, { episode_id: episodeId });
    return response.data;
  },
  async share(seriesId: string, isPublic: boolean) {
    const response = await api.post(`/api/story-series/${encodeURIComponent(seriesId)}/share`, { is_public: isPublic });
    return response.data as { success?: boolean; share_url?: string; is_public?: boolean };
  },
  async rewards(seriesId: string) {
    const response = await api.get(`/api/story-series/${encodeURIComponent(seriesId)}/rewards`);
    return response.data;
  },
  async claimReward(seriesId: string, milestone: number) {
    const response = await api.post(`/api/story-series/${encodeURIComponent(seriesId)}/claim-reward`, { milestone });
    return response.data;
  },
  async extractedCharacters(seriesId: string) {
    const response = await api.get(`/api/story-series/${encodeURIComponent(seriesId)}/extracted-characters`);
    return response.data;
  },
  async confirmCharacters(seriesId: string, characterIds: string[]) {
    const response = await api.post(`/api/story-series/${encodeURIComponent(seriesId)}/confirm-characters`, {
      confirmed_character_ids: characterIds,
    });
    return response.data;
  },
  async dismissExtraction(seriesId: string) {
    const response = await api.post(`/api/story-series/${encodeURIComponent(seriesId)}/dismiss-extraction`);
    return response.data;
  },
};
