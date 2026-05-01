import type { StateCreator } from 'zustand';
import type { Task } from '@/lib/api';
import { getTaskHistory } from '@/lib/api';
import type { StoreState } from '../useStore';

const MAX_TASKS = 200;

export interface TaskSlice {
  activeTaskId: string | null;
  setActiveTaskId: (id: string | null) => void;
  tasks: Task[];
  setTasks: (tasks: Task[]) => void;
  updateTask: (taskUpdate: Partial<Task> & { task_id: string }) => void;
  fetchInitialTasks: () => Promise<void>;
  lastCompletedTaskTime: number;
  lastCompletedTaskType: string | null;
}

export const createTaskSlice: StateCreator<StoreState, [], [], TaskSlice> = (set, get) => ({
  activeTaskId: null,
  setActiveTaskId: (id) => set({ activeTaskId: id }),
  tasks: [],
  lastCompletedTaskTime: 0,
  lastCompletedTaskType: null,
  setTasks: (tasks) => set({ tasks }),

  updateTask: (taskUpdate) => {
    set((state) => {
      let isCompleted = false;
      let completedType: string | null = null;
      const existingTaskIndex = state.tasks.findIndex((t) => t.task_id === taskUpdate.task_id);
      let updatedTasks = [...state.tasks];

      if (existingTaskIndex >= 0) {
        const oldStatus = updatedTasks[existingTaskIndex].status;
        // 过滤掉 undefined 值，防止覆盖已有数据
        const filteredUpdate = Object.fromEntries(
          Object.entries(taskUpdate).filter(([, v]) => v !== undefined),
        );
        updatedTasks[existingTaskIndex] = { ...updatedTasks[existingTaskIndex], ...filteredUpdate };
        if (oldStatus !== 'COMPLETED' && taskUpdate.status === 'COMPLETED') {
          isCompleted = true;
          completedType = updatedTasks[existingTaskIndex].task_type || null;
        }
      } else {
        const msg = (taskUpdate as { msg?: unknown }).msg;
        const newTask = {
          task_id: taskUpdate.task_id,
          task_type: taskUpdate.task_type || 'pipeline',
          status: taskUpdate.status || 'RUNNING',
          progress: taskUpdate.progress || 0,
          payload: taskUpdate.payload || JSON.stringify({ msg: typeof msg === 'string' ? msg : '' }),
          error_msg: taskUpdate.error_msg,
        } as Task;
        updatedTasks = [newTask, ...state.tasks];
        if (newTask.status === 'COMPLETED') {
          isCompleted = true;
          completedType = newTask.task_type;
        }
      }

      const creatorRelatedTypes = [
        'pipeline',
        'download',
        'batch_pipeline',
        'creator_sync_incremental',
        'creator_sync_full',
        'full_sync_incremental',
        'full_sync_full',
      ];
      const shouldResetCreators = isCompleted && completedType ? creatorRelatedTypes.includes(completedType) : false;

      // 超出上限时淘汰已完成/失败/取消的旧任务
      if (updatedTasks.length > MAX_TASKS) {
        const terminal = updatedTasks.filter((t) => ['COMPLETED', 'FAILED', 'CANCELLED'].includes(t.status));
        const active = updatedTasks.filter((t) => !['COMPLETED', 'FAILED', 'CANCELLED'].includes(t.status));
        const toEvict = Math.max(0, updatedTasks.length - MAX_TASKS);
        if (toEvict > 0 && terminal.length > 0) {
          terminal.sort((a, b) => (b.update_time || '').localeCompare(a.update_time || ''));
          updatedTasks = [...active, ...terminal.slice(0, terminal.length - toEvict)];
        }
      }

      return {
        tasks: updatedTasks,
        ...(isCompleted
          ? {
              lastCompletedTaskTime: Date.now(),
              lastCompletedTaskType: completedType,
              ...(shouldResetCreators ? { creatorsLoadedAt: 0, assetsLoadedAt: 0 } : { assetsLoadedAt: 0 }),
            }
          : {}),
      };
    });
  },

  fetchInitialTasks: async () => {
    try {
      const history = await getTaskHistory();
      set((state) => {
        const historyMap = new Map(history.map((t) => [t.task_id, t]));
        // 保留 store 中 WS 已有但 REST 未返回的任务（正在运行中尚未持久化）
        const wsOnlyTasks = state.tasks.filter((t) => !historyMap.has(t.task_id));
        // REST 返回的任务：优先用 WS 的实时进度
        const merged = history.map((t) => {
          const wsTask = state.tasks.find((s) => s.task_id === t.task_id);
          if (wsTask && wsTask.update_time && t.update_time) {
            return new Date(wsTask.update_time) > new Date(t.update_time) ? wsTask : t;
          }
          return wsTask && wsTask.progress > t.progress ? wsTask : t;
        });
        return { tasks: [...merged, ...wsOnlyTasks] };
      });
    } catch (error) {
      console.error('Failed to fetch initial task history', error);
    }
    // get() referenced via merging closure if needed downstream
    void get;
  },
});
