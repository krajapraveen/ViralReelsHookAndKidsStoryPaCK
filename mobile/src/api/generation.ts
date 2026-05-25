import { api, withJobId } from './client';
import type { GenerationJob, ToolKey } from '@/types/api';
import { findTool } from '@/constants/features';

export type ToolSubmitPayload = {
  title?: string;
  prompt?: string;
  audience?: string;
  style?: string;
  duration?: string;
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

    const response = await api.post<GenerationJob>(tool.api.create, {
      ...payload,
      mobile_client: true,
      source: 'visionary-suite-mobile',
    });

    return response.data;
  },
  async getToolJob(toolKey: ToolKey, jobId: string) {
    const tool = findTool(toolKey);
    if (!tool?.api.status) {
      throw new Error('This tool does not expose a documented job status endpoint yet.');
    }
    const response = await api.get<GenerationJob>(withJobId(tool.api.status, jobId));
    return response.data;
  },
  async listToolItems(toolKey: ToolKey) {
    const tool = findTool(toolKey);
    if (!tool?.api.list) return [];
    const response = await api.get<GenerationJob[] | { items?: GenerationJob[]; jobs?: GenerationJob[]; data?: GenerationJob[] }>(
      tool.api.list,
    );
    const body = response.data;
    if (Array.isArray(body)) return body;
    return body.items || body.jobs || body.data || [];
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
