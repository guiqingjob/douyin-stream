import { useEffect, useMemo, useState } from 'react';
import { Loader2 } from 'lucide-react';

import { getFailureSummary, type FailureSummary } from '@/lib/api';
import { cn } from '@/lib/utils';

const WINDOW_OPTIONS = [3, 7, 14, 30] as const;

const ERROR_TYPE_LABELS: Record<string, string> = {
  quota: '额度不足',
  network: '网络异常',
  timeout: '请求超时',
  auth: '鉴权失败',
  file: '文件错误',
  validation: '参数错误',
  unknown: '未知错误',
};

const STAGE_LABELS: Record<string, string> = {
  uploading: '上传中',
  uploaded: '上传完成',
  transcribing: '转写中',
  exporting: '导出中',
  downloading: '下载结果',
  saved: '落盘',
  failed: '失败',
  unknown: '未知阶段',
};

function formatRelativeTime(iso: string | null) {
  if (!iso) return '—';
  const t = new Date(iso).getTime();
  if (!Number.isFinite(t)) return '—';
  const diff = Date.now() - t;
  const minute = 60_000;
  const hour = 60 * minute;
  const day = 24 * hour;
  if (diff < minute) return '刚刚';
  if (diff < hour) return `${Math.floor(diff / minute)} 分钟前`;
  if (diff < day) return `${Math.floor(diff / hour)} 小时前`;
  return `${Math.floor(diff / day)} 天前`;
}

export function FailureSummarySection() {
  const [days, setDays] = useState<number>(7);
  const [data, setData] = useState<FailureSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getFailureSummary(days)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch(() => {
        // interceptor toasts; 这里失败时仅清空表格
        if (!cancelled) setData(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [days]);

  const buckets = useMemo(() => data?.buckets ?? [], [data]);
  const total = data?.total_failed ?? 0;

  return (
    <section className="rounded-lg border bg-card p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">最近转写失败原因 Top</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">
            数据源 transcribe_runs 表，按 (error_type, error_stage) 分桶统计。
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          {WINDOW_OPTIONS.map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={cn(
                'rounded px-2 py-1 transition-colors',
                days === d
                  ? 'bg-primary text-primary-foreground'
                  : 'border border-border bg-background text-muted-foreground hover:bg-secondary/50',
              )}
            >
              {d} 天
            </button>
          ))}
        </div>
      </div>

      <div className="mt-3 text-xs text-muted-foreground">
        {loading ? (
          <span className="flex items-center gap-1.5">
            <Loader2 className="size-3 animate-spin" /> 加载中…
          </span>
        ) : (
          <span>
            最近 {data?.window_days ?? days} 天共 <span className="font-semibold text-foreground">{total}</span> 次失败
          </span>
        )}
      </div>

      {buckets.length === 0 && !loading ? (
        <div className="mt-3 rounded-md border border-dashed border-border/60 px-3 py-6 text-center text-xs text-muted-foreground">
          ✓ 这段时间没有转写失败记录
        </div>
      ) : (
        <div className="mt-3 overflow-hidden rounded-md border border-border/60">
          <table className="w-full text-xs">
            <thead className="bg-muted/50 text-muted-foreground">
              <tr>
                <th className="px-3 py-2 text-left font-medium">错误类型</th>
                <th className="px-3 py-2 text-left font-medium">阶段</th>
                <th className="px-3 py-2 text-right font-medium">次数</th>
                <th className="px-3 py-2 text-left font-medium">最近一次</th>
                <th className="px-3 py-2 text-left font-medium">样本错误</th>
              </tr>
            </thead>
            <tbody>
              {buckets.map((b, i) => (
                <tr key={`${b.error_type}-${b.error_stage}-${i}`} className="border-t border-border/40">
                  <td className="px-3 py-2 font-medium text-foreground">
                    {ERROR_TYPE_LABELS[b.error_type] ?? b.error_type}
                  </td>
                  <td className="px-3 py-2 text-muted-foreground">
                    {STAGE_LABELS[b.error_stage] ?? b.error_stage}
                  </td>
                  <td className="px-3 py-2 text-right font-mono">{b.count}</td>
                  <td className="px-3 py-2 text-muted-foreground">{formatRelativeTime(b.last_seen)}</td>
                  <td className="px-3 py-2 text-muted-foreground/80 truncate max-w-[280px]" title={b.sample_error}>
                    {b.sample_error || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
