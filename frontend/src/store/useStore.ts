import { create } from 'zustand';
import { API_WS_URL, Task, Creator, Asset, getTaskHistory, getSettings, getCreators, getAssets } from '@/lib/api';

type SettingsPayload = Awaited<ReturnType<typeof getSettings>>;

const CREATORS_CACHE_TTL = 30_000; // 30 seconds
const ASSETS_CACHE_TTL = 30_000; // 30 seconds

interface StoreState {
  activeTaskId: string | null;
  setActiveTaskId: (id: string | null) => void;
  tasks: Task[];
  setTasks: (tasks: Task[]) => void;
  updateTask: (taskUpdate: Partial<Task> & { task_id: string }) => void;
  fetchInitialTasks: () => Promise<void>;
  connectWebSocket: () => void;
  disconnectWebSocket: () => void;
  wsConnected: boolean;
  lastCompletedTaskTime: number;
  lastCompletedTaskType: string | null;
  _wsRetryCount: number;
  _wsInstance: WebSocket | null;
  _wsRetryTimer: ReturnType<typeof setTimeout> | null;
  _wsClosing: boolean;
  settings: SettingsPayload | null;
  fetchSettings: () => Promise<SettingsPayload | undefined>;
  creators: Creator[];
  creatorsLoadedAt: number;
  fetchCreators: (force?: boolean) => Promise<Creator[]>;
  _fetchingCreators: Promise<Creator[]> | null;
  assets: Asset[];
  assetsLoadedAt: number;
  fetchAssets: (force?: boolean) => Promise<Asset[]>;
  _fetchingAssets: Promise<Asset[]> | null;
}

const WS_BASE_DELAY = 1000;
const WS_MAX_DELAY = 30000;
const WS_MAX_RETRIES = 20;

export const useStore = create<StoreState>((set, get) => ({
  activeTaskId: null,
  setActiveTaskId: (id) => set({ activeTaskId: id }),
  tasks: [],
  lastCompletedTaskTime: 0,
  lastCompletedTaskType: null,
  _wsClosing: false,
  setTasks: (tasks) => set({ tasks }),
  updateTask: (taskUpdate) => {
    set((state) => {
      let isCompleted = false;
      let completedType: string | null = null;
      const existingTaskIndex = state.tasks.findIndex(t => t.task_id === taskUpdate.task_id);
      let updatedTasks = [...state.tasks];

      if (existingTaskIndex >= 0) {
        const oldStatus = updatedTasks[existingTaskIndex].status;
        // 过滤掉 undefined 值，防止覆盖已有数据
        const filteredUpdate = Object.fromEntries(
          Object.entries(taskUpdate).filter(([, v]) => v !== undefined)
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

      const creatorRelatedTypes = ['pipeline', 'download', 'batch_pipeline', 'creator_sync_incremental', 'creator_sync_full', 'full_sync_incremental', 'full_sync_full'];
      const shouldResetCreators = isCompleted && completedType ? creatorRelatedTypes.includes(completedType) : false;

      return {
        tasks: updatedTasks,
        ...(isCompleted ? { lastCompletedTaskTime: Date.now(), lastCompletedTaskType: completedType, ...(shouldResetCreators ? { creatorsLoadedAt: 0, assetsLoadedAt: 0 } : { assetsLoadedAt: 0 }) } : {})
      };
    });
  },
  fetchInitialTasks: async () => {
    try {
      const history = await getTaskHistory();
      // merge 而非 replace：保留 WS 已推送的更新（WS 更新可能比 REST 更新）
      set((state) => {
        const wsUpdated = new Map(state.tasks.map(t => [t.task_id, t]));
        for (const t of history) {
          if (!wsUpdated.has(t.task_id)) {
            wsUpdated.set(t.task_id, t);
          }
        }
        return { tasks: Array.from(wsUpdated.values()) };
      });
    } catch (error) {
      console.error("Failed to fetch initial task history", error);
    }
  },
  creators: [],
  creatorsLoadedAt: 0,
  _fetchingCreators: null,
  fetchCreators: async (force = false) => {
    const { creatorsLoadedAt, creators, _fetchingCreators } = get();
    if (!force && creatorsLoadedAt > 0 && Date.now() - creatorsLoadedAt < CREATORS_CACHE_TTL) {
      return creators;
    }
    if (_fetchingCreators) return _fetchingCreators;
    const promise = (async () => {
      try {
        const data = await getCreators();
        set({ creators: data, creatorsLoadedAt: Date.now(), _fetchingCreators: null });
        return data;
      } catch (error) {
        console.error("Failed to fetch creators", error);
        set({ _fetchingCreators: null });
        return get().creators;
      }
    })();
    set({ _fetchingCreators: promise });
    return promise;
  },
  assets: [],
  assetsLoadedAt: 0,
  _fetchingAssets: null,
  fetchAssets: async (force = false) => {
    const { assetsLoadedAt, assets, _fetchingAssets } = get();
    if (!force && assetsLoadedAt > 0 && Date.now() - assetsLoadedAt < ASSETS_CACHE_TTL) {
      return assets;
    }
    if (_fetchingAssets) return _fetchingAssets;
    const promise = (async () => {
      try {
        const data = await getAssets();
        set({ assets: data, assetsLoadedAt: Date.now(), _fetchingAssets: null });
        return data;
      } catch (error) {
        console.error("Failed to fetch assets", error);
        set({ _fetchingAssets: null });
        return get().assets;
      }
    })();
    set({ _fetchingAssets: promise });
    return promise;
  },
  settings: null,
  fetchSettings: async () => {
    try {
      const data = await getSettings();
      set({ settings: data });
      return data;
    } catch (error) {
      console.error("Failed to fetch settings", error);
    }
  },
  wsConnected: false,
  _wsRetryCount: 0,
  _wsInstance: null,
  _wsRetryTimer: null,
  connectWebSocket: () => {
    // 如果已有有效连接或正在连接，直接返回
    const { _wsInstance, wsConnected } = get();
    if (wsConnected || (_wsInstance && (_wsInstance.readyState === WebSocket.OPEN || _wsInstance.readyState === WebSocket.CONNECTING))) return;

    const ws = new WebSocket(API_WS_URL);
    set({ _wsInstance: ws });

    ws.onopen = () => {
      console.log('Task WebSocket connected');
      set({ wsConnected: true, _wsRetryCount: 0 });
      get().fetchInitialTasks();
      get().fetchSettings();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // 忽略 ping 消息
        if (data.type === 'ping') return;
        if (!data.task_id) return;
        const update: Partial<Task> & { task_id: string } = {
          task_id: data.task_id,
          progress: data.progress,
          status: data.status,
          task_type: data.task_type,
          update_time: new Date().toISOString(),
        };
        const msg = typeof data.msg === 'string' ? data.msg : '';
        if ('msg' in data || data.subtasks || data.result_summary || data.stage) {
          const existing = get().tasks.find((t) => t.task_id === data.task_id);
          let payload: Record<string, unknown> = {};
          if (existing?.payload) {
            try {
              const parsed = JSON.parse(existing.payload);
              if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
                payload = parsed as Record<string, unknown>;
              }
            } catch {
              payload = {};
            }
          }
          if (msg) payload.msg = msg;
          if (data.subtasks) payload.subtasks = data.subtasks;
          if (data.result_summary) payload.result_summary = data.result_summary;
          if (data.stage) payload.stage = data.stage;
          update.payload = JSON.stringify(payload);
        }
        if (data.status === 'FAILED' && msg) {
          update.error_msg = msg;
        }
        get().updateTask(update);
      } catch (e) {
        console.error("Failed to parse task WS message", e);
      }
    };

    ws.onclose = () => {
      set({ wsConnected: false, _wsInstance: null });
      // 如果是主动断开，不重连
      if (get()._wsClosing) {
        set({ _wsClosing: false });
        return;
      }
      const retryCount = get()._wsRetryCount;
      if (retryCount >= WS_MAX_RETRIES) {
        console.warn('Task WebSocket max retries reached, giving up');
        return;
      }
      // 清理已有的重连 timer，避免多个 timer 累积
      const existingTimer = get()._wsRetryTimer;
      if (existingTimer) {
        clearTimeout(existingTimer);
      }
      const delay = Math.min(WS_BASE_DELAY * Math.pow(2, retryCount), WS_MAX_DELAY);
      console.log(`Task WebSocket disconnected, reconnecting in ${delay}ms (attempt ${retryCount + 1})`);
      set({ _wsRetryCount: retryCount + 1 });
      const timer = setTimeout(() => {
        get().connectWebSocket();
      }, delay);
      set({ _wsRetryTimer: timer });
    };

    ws.onerror = (err) => {
      console.error('Task WebSocket error', err);
      ws.close();
    };
  },
  disconnectWebSocket: () => {
    const { _wsInstance, _wsRetryTimer } = get();
    if (_wsRetryTimer) {
      clearTimeout(_wsRetryTimer);
    }
    if (_wsInstance) {
      set({ _wsClosing: true });
      _wsInstance.close();
    }
    set({ _wsInstance: null, wsConnected: false, _wsRetryTimer: null, _wsRetryCount: 0 });
  }
}));
