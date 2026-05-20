import { Loader2, Plus, Zap, Trash2 } from 'lucide-react';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import { runScheduleNow } from '@/lib/api';
import type { ScheduleTask } from '@/types';

interface ScheduleSettingsProps {
  schedules: ScheduleTask[];
  isLoadingSchedules: boolean;
  newCronExpr: string;
  setNewCronExpr: (v: string) => void;
  isAddingSchedule: boolean;
  onAddSchedule: () => void;
  onToggleSchedule: (taskId: string, enabled: boolean) => void;
  onDeleteSchedule: (taskId: string) => void;
}

export function ScheduleSettings({
  schedules,
  isLoadingSchedules,
  newCronExpr,
  setNewCronExpr,
  isAddingSchedule,
  onAddSchedule,
  onToggleSchedule,
  onDeleteSchedule,
}: ScheduleSettingsProps) {
  return (
    <div className="pt-3 space-y-3">
      <div className="flex gap-2">
        <input
          type="text"
          placeholder="Cron 表达式，如 0 2 * * *"
          value={newCronExpr}
          onChange={(e) => setNewCronExpr(e.target.value)}
          className="flex-1 bg-sunken rounded-lg px-3 py-2 text-sm text-fg-primary outline-none border border-transparent focus:border-accent-dim transition-colors"
        />
        <button
          onClick={onAddSchedule}
          disabled={!newCronExpr.trim() || isAddingSchedule}
          className="px-4 py-2 bg-accent text-white rounded-lg text-sm font-medium hover:brightness-110 transition-all active:scale-[0.96] disabled:opacity-50"
        >
          {isAddingSchedule ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
        </button>
      </div>
      <div className="text-xs text-fg-muted">
        每天凌晨 2 点: 0 2 * * * · 每 6 小时: 0 */6 * * *
      </div>

      <div className="space-y-2">
        {isLoadingSchedules ? (
          <div className="flex items-center gap-2 py-2 text-sm text-fg-muted">
            <Loader2 className="w-4 h-4 animate-spin" /> 加载中...
          </div>
        ) : schedules.length === 0 ? (
          <div className="text-sm text-fg-muted py-2">还没有定时任务</div>
        ) : (
          schedules.map((task) => (
            <div key={task.task_id} className="flex items-center justify-between py-2 px-3 bg-sunken rounded-lg">
              <div className="min-w-0">
                <div className="text-sm font-medium font-mono text-fg-primary">{task.cron_expr}</div>
                <div className="text-xs text-fg-muted mt-0.5">
                  {task.enabled ? '已启用' : '已禁用'} · {task.task_type === 'scan_all_following' ? '同步关注' : task.task_type}
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => runScheduleNow(task.task_id).then(() => toast.success('已触发立即执行')).catch(() => toast.error('执行失败'))}
                  className="p-1.5 rounded-lg hover:bg-accent/10 text-fg-muted hover:text-accent transition-colors"
                  title="立即执行"
                >
                  <Zap className="w-3.5 h-3.5" />
                </button>
                <Switch
                  checked={task.enabled}
                  onCheckedChange={(v) => onToggleSchedule(task.task_id, v)}
                />
                <button
                  onClick={() => onDeleteSchedule(task.task_id)}
                  className="p-1.5 rounded-lg hover:bg-err/10 text-fg-muted hover:text-err transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
