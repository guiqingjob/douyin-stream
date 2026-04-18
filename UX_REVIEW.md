# 用户体验审查报告

## 一、问题清单

### 🔴 高优先级 (P0)

| # | 问题 | 位置 | 描述 |
|---|------|------|------|
| 1 | **设置页添加账号后无反馈** | Settings.tsx:120,125,145,151 | 添加/删除账号后只显示 toast，没有刷新账号列表状态 |
| 2 | **创作者下载状态不明确** | Creators.tsx:330-340 | 点击下载后无即时加载状态，用户不知道是否成功触发 |
| 3 | **收件箱批量操作无进度反馈** | Inbox.tsx:376-441 | 批量删除/标记/导出是大数据量操作，无 loading 状态 |
| 4 | **页面切换无过渡动画** | App.tsx:46 | 路由切换是纯内容替换，缺少淡入效果 |

### 🟠 中优先级 (P1)

| # | 问题 | 位置 | 描述 |
|---|------|------|------|
| 5 | **发现页视频列表无骨架屏** | Discovery.tsx:228-320 | 加载中只有 spinner，没有 skeleton 加载态 |
| 6 | **创作者页面无空状态引导** | Creators.tsx:302-310 | 没有创作者时没有引导用户去添加 |
| 7 | **设置页并发数保存无反馈** | Settings.tsx:684 | 保存并发设置后无 toast 确认 |
| 8 | **搜索无防抖处理** | Inbox.tsx:188-210 | 每次输入立即触发搜索，请求过于频繁 |
| 9 | **定时任务开关无状态** | Creators.tsx:190-210 | 定时任务开启/关闭后不刷新状态 |

### 🟡 低优先级 (P2)

| # | 问题 | 位置 | 描述 |
|---|------|------|------|
| 10 | 图标缺少 tooltips | 多个页面 | 一些图标按钮没有 title 属性 |
| 11 | 快捷键无提示覆盖层 | Inbox.tsx | 快捷键 `?` 只在 cheatsheet 显示，页面无持久提示 |
| 12 | 表单验证样式不统一 | Settings.tsx | 输入框验证失败无红色边框提示 |
| 13 | 底部工具栏响应式问题 | Discovery.tsx:430 | 窄屏幕下 fixed 定位可能遮挡内容 |

---

## 二、具体改进建议

### 1. 设置页账号操作后刷新 (P0)

```tsx
// Settings.tsx - handleAddDouyin 后
} catch (err) {
  const msg = err instanceof Error ? err.message : '未知错误';
  toast.error(`添加抖音账号失败: ${msg}`);
} finally {
  setIsAddingDouyin(false);
  fetchSettings(); // ← 新增：刷新设置状态
}

// handleDeleteDouyin 后
} catch (err) {
  ...
} finally {
  fetchSettings(); // ← 新增
}
```

### 2. 创作者下载状态反馈 (P0)

```tsx
// Creators.tsx
const handleDownload = async (uid, mode) => {
  if (downloadingCreators[uid]) return; // 已在下载

  setDownloadingCreators((prev) => ({ ...prev, [uid]: mode }));
  try {
    await triggerCreatorDownload(uid, mode);
    toast.success(`已启动${mode === 'full' ? '全量' : '增量'}同步`);
  } catch (err) {
    const msg = err instanceof Error ? err.message : '未知错误';
    toast.error(`同步失败: ${msg}`);
  } finally {
    setDownloadingCreators((prev) => ({ ...prev, [uid]: null }));
  }
};
```

### 3. 批量操作 Loading 状态 (P0)

```tsx
// Inbox.tsx - handleBulkDelete
const handleBulkDelete = async () => {
  if (selectedIds.size === 0) return;
  // 添加删除中的 loading
  const idsToDelete = Array.from(selectedIds);
  setDeletingAssets(new Set(idsToDelete));
  clearSelection();

  try {
    await bulkDeleteAssets(idsToDelete);
    toast.success(`已删除 ${idsToDelete.length} 条素材`);
    fetchAssetsByCreator(selectedCreatorUid);
  } catch (err) {
    ...
  } finally {
    setDeletingAssets(new Set());
  }
};
```

### 4. 添加骨架屏 (P1)

```tsx
// Discovery.tsx - 在 videoGrid 前添加
{isFetching ? (
  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
    {Array.from({ length: 12 }).map((_, i) => (
      <div key={i} className="rounded-2xl bg-card skeleton-shimmer aspect-[3/4]" />
    ))}
  </div>
) : (
  <Virtuoso ... />
)}
```

### 5. 搜索防抖 (P1)

```tsx
// Inbox.tsx
const [searchDebounce] = useState(() =>
  debounce((q) => {
    if (!q.trim()) {
      setDisplayAssets(assets);
      return;
    }
    setIsSearching(true);
    searchAssets(q).then(...).finally(() => setIsSearching(false));
  }, 300)
);

const handleSearchChange = (e) => {
  const q = e.target.value;
  setSearchQuery(q);
  searchDebounce(q);
};
```

---

## 三、预期效果

| 优化项 | 预期效果 |
|--------|----------|
| 账号操作刷新 | 设置页操作后立即看到最新状态，减少困惑 |
| 下载状态反馈 | 用户明确知道是否成功触发任务 |
| 批量 loading | 大数据量操作时不卡死界面，告知用户进度 |
| 骨架屏 | 加载过程更流畅，减少感知等待时间 |
| 搜索防抖 | 减少无效 API 请求，提升性能 |

---

## 四、已修复的问题 (本次会话)

- ✅ 获取预览前确认放弃已选视频
- ✅ 错误信息显示具体原因
- ✅ 并发数输入验证 1-10
- ✅ 收件箱素材数量显示完整 (limit=500)
- ✅ 待下载/待转写素材重试按钮
- ✅ 账号池按余额权重分配任务
- ✅ Apple 设计系统优化