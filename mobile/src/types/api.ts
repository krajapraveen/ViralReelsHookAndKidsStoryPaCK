export type ApiEnvelope<T> = {
  data?: T;
  detail?: string | ApiErrorDetail;
  request_id?: string;
};

export type ApiErrorDetail = {
  code?: string;
  message?: string;
  request_id?: string;
  retryable?: boolean;
  http_status?: number;
};

export type User = {
  id?: string;
  _id?: string;
  email: string;
  name?: string;
  full_name?: string;
  username?: string;
  plan?: string;
  role?: string;
  credits?: number;
  email_verified?: boolean;
};

export type AuthResponse = {
  access_token?: string;
  token?: string;
  user?: User;
};

export type CreditBalance = {
  balance?: number;
  credits?: number;
  available?: number;
  plan?: string;
};

export type JobStatus = 'PENDING' | 'QUEUED' | 'RUNNING' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | 'CANCELLED' | string;

export type GenerationJob = {
  id?: string;
  _id?: string;
  job_id?: string;
  status?: JobStatus;
  state?: string;
  progress?: number;
  progress_percent?: number;
  current_stage?: string;
  current_step?: string;
  queue_position?: number;
  quality_mode?: string;
  series_id?: string;
  episode_number?: number;
  challenge_id?: string;
  parent_job_id?: string;
  requested_duration_seconds?: number;
  actual_duration_seconds?: number;
  actual_audio_duration_seconds?: number;
  duration_seconds?: number;
  duration_validation?: {
    ok?: boolean;
    requested_duration_seconds?: number;
    actual_duration_seconds?: number;
    actual_audio_duration_seconds?: number;
    repaired?: boolean;
    error?: string;
  };
  title?: string;
  prompt?: string;
  type?: string;
  created_at?: string;
  updated_at?: string;
  video_url?: string;
  playback_url?: string;
  asset_ready?: boolean;
  asset_validation?: {
    ready?: boolean;
    reason?: string;
    http_status?: number;
    size_bytes?: number;
    content_type?: string;
    detail?: string;
  };
  output_url?: string;
  download_url?: string;
  share_url?: string;
  thumbnail_url?: string;
  preview_url?: string;
  result?: Record<string, unknown>;
  error?: string;
  error_message?: string;
  error_code?: string;
  detail?: string;
  render_queue?: {
    name?: string;
    position?: number | null;
    workers?: number;
    concurrency?: number;
    timeout_seconds?: number;
    max_retries?: number;
    dedicated?: boolean;
  };
};

export type PricingProduct = {
  id?: string;
  productId?: string;
  name?: string;
  price?: number;
  currency?: string;
  credits?: number;
  description?: string;
  interval?: string;
};

export type ToolKey =
  | 'story-video'
  | 'story-series'
  | 'photo-trailer'
  | 'character-memory'
  | 'reel-generator'
  | 'photo-to-comic'
  | 'comic-storybook'
  | 'bedtime-stories'
  | 'reaction-gif'
  | 'brand-story'
  | 'daily-viral-ideas';
