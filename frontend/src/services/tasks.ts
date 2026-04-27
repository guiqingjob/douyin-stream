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

export const rerunTask = async (taskId: string, signal?: AbortSignal): Promise<{ task_id: string; status: string; message: string }> => {
  const response = await apiClient.post(`/tasks/${taskId}/rerun`, null, { signal });
  return response.data;
};

export const setAutoRetry = async (taskId: string, enabled: boolean = true, signal?: AbortSignal): Promise<{ status: string; message: string }> => {
  const response = await apiClient.post(`/tasks/${taskId}/auto-retry?enabled=${enabled}`, null, { signal });
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
