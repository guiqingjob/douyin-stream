## 1. 架构设计
- **前端单文件架构 (Single File HTML)**：采用原生的 HTML5 + CSS3 + Vanilla JS，零构建工具（无 Node.js、Webpack、Vite）。
- **静态数据源注入 (Static Data Injection)**：通过在 HTML 中以 `<script src="data.js"></script>` 引入 Python 脚本生成的静态 JSON 数据文件。
- **无服务器依赖 (Serverless)**：直接在本地文件系统（`file://` 协议）双击即可运行，规避了跨域 (CORS) 与部署成本。

## 2. 技术选型
- **语言**：HTML5, CSS3, ES6+ JavaScript
- **数据格式**：挂载在 `window.APP_DATA` 的对象
- **样式**：原生 CSS Variables (`:root`) 实现主题配置，Flexbox + CSS Grid 布局。
- **媒体展示**：原生 `<video>` 标签，支持 `controls`、`preload="none"` 和 `poster` 属性。

## 3. 核心功能实现逻辑

### 3.1 渲染引擎 (Render Engine)
1. **`render()`**：
   - 检查 `window.APP_DATA` 是否存在。如果不存在，注入空状态 DOM (`<div class="empty-state">...</div>`)。
   - 遍历 `APP_DATA.videos`，使用 `reduce` 统计全局数据（如 `totalDiggs` 和 `totalSize`）。
   - 将统计结果挂载到 `#globalStats`。
   - 调用 `renderAuthors()` 更新博主和视频列表。

### 3.2 排序算法 (Sort Algorithm)
1. **`sortVideos(videos, sortType)`**：
   - 接收视频数组和排序策略字符串。
   - 使用 JS `Array.prototype.sort()`，支持：
     - `digg_desc`: 点赞数倒序（默认）
     - `time_desc`: 发布时间倒序（最新）
     - `time_asc`: 发布时间正序（最早）
     - `comment_desc`: 评论数倒序
     - `size_desc`: 视频体积倒序

### 3.3 搜索与过滤 (Search & Filter)
1. **`handleSearch(event)`**：
   - 绑定到搜索框的 `onkeyup` 事件。
   - 实时提取 `e.target.value.toLowerCase()`。
   - 用户敲击回车或输入时，触发 `renderAuthors()`。
2. **`renderAuthors()` 过滤逻辑**：
   - 遍历每个博主的视频数组，利用 `String.prototype.includes()` 进行全文匹配（匹配字段包括 `v.stats?.desc` 和 `v.name`）。
   - 若某博主匹配到的视频数为 0，且当前处于搜索状态，则直接跳过该博主卡片的渲染，保证视图整洁。

### 3.4 交互优化 (UX Enhancement)
1. **Accordion 折叠面板**：
   - 使用 CSS 选择器 `.author-card.active .video-grid` 控制显示与隐藏 (`display: grid; animation: fadeIn 0.4s ease-out;`)。
   - 在 JS 中动态追加 `active` 类名。当用户输入搜索词时，命中的博主卡片会自动添加 `active` 类展开内容。
2. **数字格式化工具**：
   - `formatNumber(num)`：将大数字转换为带“万”或“亿”的易读格式。
   - `formatSize(bytes)`：将字节级数字转换为 `KB`, `MB`, `GB` 格式。

## 4. 数据模型 (Data Structure)

挂载在 `data.js` 中的 `window.APP_DATA` 结构：
```javascript
{
  "generated_at": "2024-05-18T12:00:00.000Z",
  "users": [
    {
      "uid": "1234567890",
      "sec_user_id": "MS4wLjABAAAA...",
      "name": "博主昵称",
      "folder": "博主昵称",
      "video_count": 10,
      "stats": {
        "total_diggs": 5000000
      }
    }
  ],
  "videos": [
    {
      "aweme_id": "71234567890",
      "name": "2024-05-18_视频标题",
      "folder": "博主昵称",
      "size": 10485760, // 字节
      "stats": {
        "digg_count": 10000,
        "comment_count": 500,
        "create_time": 1716000000,
        "desc": "视频完整文案描述 #标签"
      }
    }
  ]
}
```