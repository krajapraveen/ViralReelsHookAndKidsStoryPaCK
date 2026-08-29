import { api, withJobId } from './client';
import type { GenerationJob, ToolKey } from '@/types/api';
import { findTool } from '@/constants/features';
import { normalizeStoryVideoPayload } from '@/contracts/storyVideo';

export type ToolSubmitPayload = {
  title?: string;
  prompt?: string;
  audience?: string;
  style?: string;
  duration?: string;
  quality_mode?: string;
  brand?: string;
  characters?: string;
};

const terminalStatuses = new Set(['COMPLETED', 'FAILED', 'CANCELLED', 'complete', 'failed', 'cancelled']);

export const generationApi = {
  async submitTool(toolKey: ToolKey, payload: ToolSubmitPayload) {
    const tool = findTool(toolKey);
    if (!tool?.api.create) {
      throw new Error('No existing API endpoint is documented for this mobile flow yet.');
    }

    const requestPayload =
      toolKey === 'story-video'
        ? normalizeStoryVideoPayload(payload)
        : {
            ...payload,
            mobile_client: true,
            source: 'visionary-suite-mobile',
          };

    console.info('[mobile.generate.request]', {
      tool: toolKey,
      endpoint: tool.api.create,
      payload: requestPayload,
    });

    const response = await api.post<GenerationJob>(tool.api.create, requestPayload);

    console.info('[mobile.generate.response]', {
      tool: toolKey,
      endpoint: tool.api.create,
      status: response.status,
      job_id: response.data?.job_id || response.data?.id || response.data?._id,
    });

    return response.data;
  },
  async getToolJob(toolKey: ToolKey, jobId: string): Promise<GenerationJob> {
    const tool = findTool(toolKey);
    if (!tool?.api.status) {
      throw new Error('This tool does not expose a documented job status endpoint yet.');
    }
    const response = await api.get<GenerationJob | { success?: boolean; job?: GenerationJob }>(withJobId(tool.api.status, jobId));
    const body = response.data;
    return ('job' in body && body.job ? body.job : body) as GenerationJob;
  },
  async listToolItems(toolKey: ToolKey, filters: { q?: string; audience?: string; style?: string } = {}) {
    const tool = findTool(toolKey);
    if (!tool?.api.list) return [];
    const response = await api.get<GenerationJob[] | { items?: GenerationJob[]; jobs?: GenerationJob[]; data?: GenerationJob[] }>(
      tool.api.list,
    );
    const body = response.data;
    const items = Array.isArray(body) ? body : body.items || body.jobs || body.data || [];
    const tokens = [
      filters.q,
      filters.audience,
      filters.style,
    ]
      .filter(Boolean)
      .flatMap((value) => String(value).toLowerCase().split(/[^a-z0-9_]+/))
      .filter((token) => token.length >= 3);
    if (!tokens.length) return items;
    return items.filter((item) => {
      const haystack = [
        item.title,
        item.prompt,
        item.type,
        item.status,
        item.state,
        item.result ? JSON.stringify(item.result) : '',
      ].join(' ').toLowerCase();
      return tokens.some((token) => haystack.includes(token));
    });
  },
  async listLibrary() {
    const response = await api.get<{ jobs?: GenerationJob[]; items?: GenerationJob[]; data?: GenerationJob[] } | GenerationJob[]>(
      '/api/story-engine/user-jobs',
    );
    const body = response.data;
    if (Array.isArray(body)) return body;
    return body.jobs || body.items || body.data || [];
  },
  async createShareLink(jobId: string) {
    const response = await api.post<{ share_url?: string; url?: string; shareId?: string }>(
      `/api/story-engine/share-link/${encodeURIComponent(jobId)}`,
    );
    return response.data;
  },
  isTerminal(status?: string) {
    return Boolean(status && terminalStatuses.has(status));
  },
};
