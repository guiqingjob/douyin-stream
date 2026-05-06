import { Loader2, Pencil, Trash2, User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
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
    <Card size="default">
      <CardContent className="space-y-4">
        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="size-9 rounded-[10px] bg-gradient-to-br from-primary/15 to-primary/5 flex items-center justify-center">
            {icon}
          </div>
          <div>
            <h3 className="text-title-3 font-semibold text-foreground">{title}</h3>
            <p className="text-caption text-muted-foreground">{description}</p>
          </div>
        </div>

        {/* Input Area */}
        <div className="flex gap-2">
          <Input
            placeholder={placeholder}
            value={cookie}
            onChange={(e) => { setCookie(e.target.value); setCookieError(''); }}
            className={cn(cookieError && 'border-destructive')}
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

        {/* Cookie Error */}
        {cookieError && (
          <div className="text-caption text-destructive">{cookieError}</div>
        )}

        {/* Account List */}
        <div className="space-y-1">
          {accounts.length === 0 ? (
            <div className="text-caption text-muted-foreground py-2">
              {extraInfo ?? '还没有账号。'}
            </div>
          ) : (
            accounts.map((account, index) => (
              <div 
                key={account.id} 
                className="apple-list-item rounded-[10px] px-4 py-3"
              >
                <div className="flex items-center justify-between">
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
                      <div className="flex items-center gap-2">
                        <User className="size-4 text-muted-foreground" />
                        <span className="text-body font-medium text-foreground">
                          {account.remark || `账号 ${index + 1}`}
                        </span>
                        <Button
                          variant="ghost"
                          size="iconSm"
                          onClick={() => {
                            setEditingRemarkId(account.id);
                            setEditingRemarkValue(account.remark || '');
                          }}
                          className="text-muted-foreground hover:text-foreground"
                        >
                          <Pencil className="size-3" />
                        </Button>
                      </div>
                    )}
                    <div className="mt-1 flex items-center gap-2 text-caption text-muted-foreground">
                      <span className="font-mono">{account.id.slice(0, 8)}</span>
                      {account.last_used ? (
                        <span>· 上次使用: {new Date(account.last_used).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}</span>
                      ) : account.create_time ? (
                        <span>· 创建于: {new Date(account.create_time).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}</span>
                      ) : null}
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={cn(
                      "text-small font-semibold px-2 py-1 rounded-[6px]",
                      account.status === 'active' 
                        ? 'bg-success/12 text-success' 
                        : 'bg-warning/14 text-warning'
                    )}>
                      {STATUS_LABELS[account.status] ?? account.status}
                    </span>
                    <Button
                      variant="ghostDestructive"
                      size="iconSm"
                      onClick={() => onDelete(account.id)}
                    >
                      <Trash2 className="size-3.5" />
                    </Button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Extra Footer */}
        {extraFooter && (
          <div className="pt-2 border-t border-border/40">
            {extraFooter}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
