import { Loader2, Pencil, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';

interface Account {
  id: string;
  status: string;
  last_used: string | null;
  remark: string;
  create_time: string | null;
}

interface AccountPoolSectionProps {
  title: string;
  icon: React.ReactNode;
  description: string;
  placeholder: string;
  accounts: Account[];
  cookie: string;
  setCookie: (v: string) => void;
  remark: string;
  setRemark: (v: string) => void;
  isAdding: boolean;
  cookieError: string;
  setCookieError: (v: string) => void;
  onAdd: () => void;
  onDelete: (id: string) => void;
  editingRemarkId: string | null;
  setEditingRemarkId: (v: string | null) => void;
  editingRemarkValue: string;
  setEditingRemarkValue: (v: string) => void;
  onSaveRemark: (id: string, value: string) => void;
  extraFooter?: React.ReactNode;
  extraInfo?: React.ReactNode;
}

const STATUS_LABELS: Record<string, string> = {
  active: '可用',
  inactive: '停用',
  expired: '过期',
  error: '异常',
};

export function AccountPoolSection({
  title,
  icon,
  description,
  placeholder,
  accounts,
  cookie,
  setCookie,
  remark,
  setRemark,
  isAdding,
  cookieError,
  setCookieError,
  onAdd,
  onDelete,
  editingRemarkId,
  setEditingRemarkId,
  editingRemarkValue,
  setEditingRemarkValue,
  onSaveRemark,
  extraFooter,
  extraInfo,
}: AccountPoolSectionProps) {
  return (
    <div className="rounded-[var(--radius-card)] border border-border/60 bg-card p-1">
      <div className="h-12 px-4 flex items-center gap-3 border-b border-border/60">
        <div className="size-5 rounded-sm bg-foreground flex items-center justify-center">
          {icon}
        </div>
        <h3 className="text-[17px] font-semibold text-foreground">{title}</h3>
      </div>
      <div className="px-4 py-3 space-y-3">
        <div className="text-[13px] text-muted-foreground">{description}</div>
        <div className="flex gap-2">
          <Input
            placeholder={placeholder}
            value={cookie}
            onChange={(e) => { setCookie(e.target.value); setCookieError(''); }}
            className={cookieError ? 'border-destructive' : ''}
          />
          <Input
            placeholder="备注"
            value={remark}
            onChange={(e) => setRemark(e.target.value)}
            className="w-24"
          />
          <Button
            variant="primary"
            size="sm"
            onClick={onAdd}
            disabled={!cookie.trim() || isAdding}
          >
            {isAdding ? <Loader2 className="size-4 animate-spin" /> : '添加'}
          </Button>
        </div>
        <div className="space-y-1">
          {accounts.length === 0 ? (
            <div className="text-sm text-muted-foreground py-2">
              {extraInfo ?? '还没有账号。'}
            </div>
          ) : (
            accounts.map((account, index) => (
              <div key={account.id} className="h-[52px] px-3 flex items-center justify-between rounded-[var(--radius-card)] hover:bg-muted/40 transition-colors duration-150">
                <div className="min-w-0 flex-1">
                  {editingRemarkId === account.id ? (
                    <Input
                      className="h-7 px-2 py-0 text-[13px]"
                      value={editingRemarkValue}
                      onChange={(e) => setEditingRemarkValue(e.target.value)}
                      onBlur={() => onSaveRemark(account.id, editingRemarkValue)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') onSaveRemark(account.id, editingRemarkValue);
                        if (e.key === 'Escape') setEditingRemarkId(null);
                      }}
                    />
                  ) : (
                    <div className="flex items-center gap-1.5">
                      <span className="text-[13px] font-medium text-foreground">
                        {account.remark || `账号 ${index + 1}`}
                      </span>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => {
                          setEditingRemarkId(account.id);
                          setEditingRemarkValue(account.remark || '');
                        }}
                        className="size-6 text-muted-foreground hover:bg-muted hover:text-foreground"
                      >
                        <Pencil className="size-3" />
                      </Button>
                    </div>
                  )}
                  <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                    <span className="font-mono">{account.id.slice(0, 8)}</span>
                    {account.last_used ? (
                      <span>· {new Date(account.last_used).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}</span>
                    ) : account.create_time ? (
                      <span>· {new Date(account.create_time).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}</span>
                    ) : null}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={cn('text-[11px] font-medium', account.status === 'active' ? 'text-success' : 'text-warning')}>
                    {STATUS_LABELS[account.status] ?? account.status}
                  </span>
                  <Button
                    variant="destructive"
                    size="icon-sm"
                    onClick={() => onDelete(account.id)}
                    className="size-8"
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </div>
              </div>
            ))
          )}
        </div>
        {extraFooter}
      </div>
    </div>
  );
}
