import { Play } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Toggle } from '@/components/ui/toggle';
import type { ScheduleTask } from '@/lib/api';

interface SyncSectionProps {
  scheduleTask: ScheduleTask | null;
  onToggle: (enabled: boolean) => void;
  onFullSync: () => void;
  douyinReady: boolean;
}

export function SyncSection({ scheduleTask, onToggle, onFullSync, douyinReady }: SyncSectionProps) {
  return (
    <div className="w-full">
      <div className="rounded-[var(--radius-card)] border border-border/60 bg-card p-5 apple-shadow-md">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium text-foreground">定时同步</div>
            <div className="mt-1 text-xs text-muted-foreground">每天 02:00 自动同步全部创作者</div>
          </div>
          <Toggle checked={scheduleTask?.enabled || false} onChange={onToggle} />
        </div>
        <Button
          variant="primary"
          onClick={onFullSync}
          disabled={!douyinReady}
          className="w-full mt-4"
        >
          <Play className="size-4 mr-2" />
          立即同步所有创作者
        </Button>
        {!douyinReady && (
          <div className="rounded-[var(--radius-card)] border border-warning/20 bg-warning/10 px-3 py-2 text-xs leading-6 text-warning mt-3">
            先添加抖音账号 Cookie 再执行同步。
          </div>
        )}
      </div>
    </div>
  );
}
