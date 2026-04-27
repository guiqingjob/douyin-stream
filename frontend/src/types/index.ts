export interface Creator {
  uid: string;
  nickname: string;
  sec_user_id: string;
  platform?: 'douyin' | 'bilibili' | 'local' | string;
  sync_status: string;
  avatar?: string;
  bio?: string;
  homepage_url?: string;
  last_fetch_time?: string | null;
  asset_count?: number;
  downloaded_videos_count?: number;
  transcript_completed_count?: number;
  transcript_pending_count?: number;
  unread_completed_count?: number;
}

export interface Asset {
  asset_id: string;
  creator_uid: string;
  title: string;
  video_status: string;
  transcript_status: string;
  transcript_path: string;
  transcript_preview?: string;
  folder_path?: string;
  is_read?: boolean;
  is_starred?: boolean;
  create_time?: string;
  update_time?: string;
}

export interface Task {
  task_id: string;
  task_type: string;
  status: string;
  progress: number;
  payload: string;
  error_msg?: string;
  update_time?: string;
}

export interface ScheduleTask {
  task_id: string;
  task_type: string;
  cron_expr: string;
  enabled: boolean;
  update_time: string;
}

export interface ScannedFile {
  path: string;
  name: string;
  size_mb: number;
}

export interface DouyinVideoMeta {
  aweme_id: string;
  desc: string;
  create_time: number;
  video_url: string;
  cover_url: string;
}

export interface DouyinCreatorMeta {
  uid: string;
  nickname: string;
  avatar: string;
}

export interface DouyinMetadataResponse {
  creator: DouyinCreatorMeta;
  videos: DouyinVideoMeta[];
}

export interface QwenStatusAccount {
  accountId: string;
  accountLabel?: string;
  remaining_hours: number;
  status: string;
}

export interface QwenStatusResponse {
  status: string;
  accounts: QwenStatusAccount[];
  message?: string;
}

export type QwenAccountValidationStatus = 'ok' | 'network_error' | 'auth_invalid';

export interface QwenAccountValidationResult {
  ok?: boolean;
  status?: QwenAccountValidationStatus;
  error_type?: string;
  message?: string;
  remaining_hours?: number;
}

export interface AddQwenAccountResponse {
  status: string;
  account_id?: string;
  validation?: QwenAccountValidationResult | QwenAccountValidationStatus;
  message?: string;
}
