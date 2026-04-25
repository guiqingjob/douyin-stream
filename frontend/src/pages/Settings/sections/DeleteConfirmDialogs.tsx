import { ConfirmDialog } from '@/components/ui/confirm-dialog';

interface DeleteConfirmDialogsProps {
  deletingDouyinId: string | null;
  setDeletingDouyinId: (v: string | null) => void;
  onDeleteDouyin: (id: string) => void;
  deletingQwenId: string | null;
  setDeletingQwenId: (v: string | null) => void;
  onDeleteQwen: (id: string) => void;
  deletingBilibiliId: string | null;
  setDeletingBilibiliId: (v: string | null) => void;
  onDeleteBilibili: (id: string) => void;
}

export function DeleteConfirmDialogs({
  deletingDouyinId,
  setDeletingDouyinId,
  onDeleteDouyin,
  deletingQwenId,
  setDeletingQwenId,
  onDeleteQwen,
  deletingBilibiliId,
  setDeletingBilibiliId,
  onDeleteBilibili,
}: DeleteConfirmDialogsProps) {
  return (
    <>
      <ConfirmDialog
        open={!!deletingDouyinId}
        onOpenChange={(open) => { if (!open) setDeletingDouyinId(null); }}
        title="移除抖音账号"
        description="确定要从账号池中移除这个抖音账号吗？移除后需要重新添加 Cookie。"
        confirmLabel="移除"
        destructive
        onConfirm={() => {
          if (deletingDouyinId) void onDeleteDouyin(deletingDouyinId);
        }}
      />
      <ConfirmDialog
        open={!!deletingQwenId}
        onOpenChange={(open) => { if (!open) setDeletingQwenId(null); }}
        title="移除 Qwen 账号"
        description="确定要从账号池中移除这个 Qwen 账号吗？移除后需要重新添加 Cookie。"
        confirmLabel="移除"
        destructive
        onConfirm={() => {
          if (deletingQwenId) void onDeleteQwen(deletingQwenId);
        }}
      />
      <ConfirmDialog
        open={!!deletingBilibiliId}
        onOpenChange={(open) => { if (!open) setDeletingBilibiliId(null); }}
        title="移除B站账号"
        description="确定要从账号池中移除这个B站账号吗？移除后需要重新添加 Cookie。"
        confirmLabel="移除"
        destructive
        onConfirm={() => {
          if (deletingBilibiliId) void onDeleteBilibili(deletingBilibiliId);
        }}
      />
    </>
  );
}
