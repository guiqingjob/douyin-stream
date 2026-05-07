import type { TaskStage } from '@/types';

export interface StageInfo {
  label: string;
  icon: string;
  color: 'primary' | 'success' | 'destructive' | 'muted';
  description: string;
}

const STAGE_CONFIG: Record<TaskStage, StageInfo> = {
  created: {
    label: '等待中',
    icon: '⏳',
    color: 'muted',
    description: '任务已创建，等待后台处理'
  },
  fetching: {
    label: '获取列表',
    icon: '📋',
    color: 'primary',
    description: '正在从服务器获取视频列表'
  },
  auditing: {
    label: '对账中',
    icon: '✔️',
    color: 'primary',
    description: '比对本地已有文件，确定待下载内容'
  },
  downloading: {
    label: '下载中',
    icon: '⬇️',
    color: 'primary',
    description: '正在下载视频文件'
  },
  transcribing: {
    label: '转写中',
    icon: '✍️',
    color: 'primary',
    description: '正在将语音转为文字'
  },
  exporting: {
    label: '导出中',
    icon: '📤',
    color: 'primary',
    description: '正在导出字幕文件'
  },
  completed: {
    label: '已完成',
    icon: '✅',
    color: 'success',
    description: '任务全部完成'
  },
  failed: {
    label: '失败',
    icon: '❌',
    color: 'destructive',
    description: '任务执行失败'
  },
  cancelled: {
    label: '已取消',
    icon: '🚫',
    color: 'muted',
    description: '任务已被取消'
  },
};

export const STAGE_ORDER: TaskStage[] = [
  'created',
  'fetching',
  'auditing',
  'downloading',
  'transcribing',
  'exporting',
  'completed',
];

export function getStageInfo(stage: TaskStage): StageInfo {
  return STAGE_CONFIG[stage] || {
    label: stage,
    icon: '❓',
    color: 'muted',
    description: ''
  };
}

export function getStageProgress(currentStage: TaskStage): { current: number; total: number } {
  const index = STAGE_ORDER.indexOf(currentStage);
  return {
    current: index >= 0 ? index + 1 : STAGE_ORDER.length,
    total: STAGE_ORDER.length,
  };
}
