import { apiClient } from '@/lib/api';
import type { Task } from '@/types';

export const getTaskHistory = async (signal?: AbortSignal): Promise<Task[]> => {
  const response = await apiClient.get('/tasks/history', { signal });
  return response.data;
};

export const getTaskStatus = async (taskId: string, signal?: AbortSignal): Promise<Task> => {
  const response = await apiClient.get(`/tasks/${taskId}`, { signal });
  return response.data;
};

export const pauseTask = async (taskId: string, signal?: AbortSignal): Promise<{ status: string; message: string }> => {
  const response = await apiClient.post(`/tasks/${taskId}/pause`, null, { signal });
  return response.data;
};

export const resumeTask = async (taskId: string, signal?: AbortSignal): Promise<{ status: string; message: string }> => {
  const response = await apiClient.post(`/tasks/${taskId}/resume`, null, { signal });
  return response.data;
};

export const cancelTask = async (taskId: string, signal?: AbortSignal): Promise<{ status: string; message: string }> => {
  const response = await apiClient.post(`/tasks/${taskId}/cancel`, null, { signal });
  return response.data;
};

export const rerunTask = async (taskId: string, signal?: AbortSignal): Promise<{ task_id: string; status: string; message: string }> => {
  const response = await apiClient.post(`/tasks/${taskId}/rerun`, null, { signal });
  return response.data;
};

export const retryFailedSubtasks = async (
  taskId: string,
  signal?: AbortSignal,
): Promise<{ task_id: string; status: string; file_count: number }> => {
  const response = await apiClient.post(`/tasks/${taskId}/retry-failed`, null, { signal });
  return response.data;
};

export type RetryFailedAssetsRequest = {
  creator_uid?: string;
  platform?: string;
  error_types?: string[];
  limit?: number;
  delete_after?: boolean;
};

export type RetryFailedAssetsResponse = {
  task_id: string;
  status: string;
  file_count: number;
  missing_file_assets: string[];
};

export const retryFailedAssets = async (
  body: RetryFailedAssetsRequest = {},
  signal?: AbortSignal,
): Promise<RetryFailedAssetsResponse> => {
  const response = await apiClient.post('/tasks/transcribe/retry-failed-assets', body, { signal });
  return response.data;
};

export const setAutoRetry = async (taskId: string, enabled: boolean = true, signal?: AbortSignal): Promise<{ status: string; message: string }> => {
  const response = await apiClient.post(`/tasks/${taskId}/auto-retry?enabled=${enabled}`, null, { signal });
  return response.data;
};

export interface FailureBucket {
  error_type: string;
  error_stage: string;
  count: number;
  last_seen: string | null;
  sample_error: string;
}

export interface FailureSummary {
  window_days: number;
  total_failed: number;
  buckets: FailureBucket[];
}

export const getFailureSummary = async (days: number = 7, signal?: AbortSignal): Promise<FailureSummary> => {
  const response = await apiClient.get(`/metrics/failure-summary?days=${days}`, { signal });
  return response.data;
};

export const clearTaskHistory = async (signal?: AbortSignal): Promise<{ status: string; message: string }> => {
  const response = await apiClient.delete('/tasks/history', { signal });
  return response.data;
};

export const deleteTask = async (taskId: string, signal?: AbortSignal): Promise<{ status: string; message: string }> => {
  const response = await apiClient.delete(`/tasks/${taskId}`, { signal });
  return response.data;
};

export const triggerPipeline = async (url: string, maxCounts: number = 5, autoDelete: boolean = true, signal?: AbortSignal): Promise<{task_id: string}> => {
  const response = await apiClient.post('/tasks/pipeline', { url, max_counts: maxCounts, auto_delete: autoDelete }, { signal });
  return response.data;
};

export const triggerBatchPipeline = async (videoUrls: string[], maxCounts?: number, signal?: AbortSignal): Promise<{task_id: string}> => {
  if (videoUrls.length === 1) {
    return triggerPipeline(videoUrls[0], maxCounts, undefined, signal);
  }
  const response = await apiClient.post('/tasks/pipeline/batch', { video_urls: videoUrls }, { signal });
  return response.data;
};

export const triggerDownloadBatch = async (videoUrls: string[], signal?: AbortSignal): Promise<{task_id: string}> => {
  const response = await apiClient.post('/tasks/download/batch', { video_urls: videoUrls }, { signal });
  return response.data;
};

export const triggerCreatorDownload = async (uid: string, mode: 'incremental' | 'full' = 'incremental', signal?: AbortSignal): Promise<{task_id: string}> => {
  const response = await apiClient.post('/tasks/download/creator', { uid, mode }, { signal });
  return response.data;
};

export const triggerFullSyncFollowing = async (mode: 'incremental' | 'full' = 'incremental', signal?: AbortSignal): Promise<{task_id: string}> => {
  const response = await apiClient.post('/tasks/download/full-sync', { mode }, { signal });
  return response.data;
};

export const recoverAwemeAndTranscribe = async (
  creatorUid: string,
  awemeId: string,
  title: string = '',
  signal?: AbortSignal
): Promise<{ task_id: string; status: string }> => {
  const response = await apiClient.post(
    '/tasks/recover/aweme',
    { creator_uid: creatorUid, aweme_id: awemeId, title },
    { signal }
  );
  return response.data;
};

export type CreatorTranscribeCleanupRetryResponse = {
  task_id: string;
  deleted_count: number;
  failed_count: number;
  failed_paths: Array<{ path: string; reason: string }>;
  total_deleted_count: number;
};

export const retryCreatorTranscribeCleanup = async (
  taskId: string,
  signal?: AbortSignal,
): Promise<CreatorTranscribeCleanupRetryResponse> => {
  const response = await apiClient.post(
    '/tasks/transcribe/creator/cleanup-retry',
    { task_id: taskId },
    { signal },
  );
  return response.data;
};
