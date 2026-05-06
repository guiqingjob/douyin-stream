# 重构策略与技术方案

## 版本历史

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| v1.0 | 2026-05-06 | 架构团队 | 初始版本 |

---

## 3. 重构策略与技术方案

### 3.1 下载器模块重构

**当前状态**: `douyin/core/downloader.py` 1207行，包含下载、解析、存储等多重职责

**重构策略**: 职责分离 + 策略模式

**重构后结构**:
```
douyin/core/
├── fetcher.py        # 网络请求抽象
│   └── interface: VideoFetcher
├── parser.py         # 响应解析
│   └── interface: ResponseParser
├── storage.py        # 文件存储
│   └── interface: VideoStorage
├── validator.py      # 数据校验
│   └── interface: DataValidator
└── downloader.py     # 协调者 (Facade)
    └── class: VideoDownloader
```

**设计原则**:
- ✅ 单一职责：每个模块只负责一个功能
- ✅ 依赖倒置：依赖接口而非具体实现
- ✅ 策略模式：支持不同平台的下载策略

**实施要点**:
1. 定义抽象接口
2. 逐步迁移代码到新模块
3. 更新所有调用方
4. 添加单元测试

---

### 3.2 管道编排重构

**当前状态**: `pipeline/orchestrator.py` 871行，流程硬编码

**重构策略**: 责任链模式 + 可插拔步骤

**重构后结构**:
```python
class PipelineStep(ABC):
    """管道步骤抽象基类"""
    
    @abstractmethod
    def execute(self, context: PipelineContext) -> PipelineContext:
        """执行步骤，返回更新后的上下文"""
    
    @abstractmethod
    def can_execute(self, context: PipelineContext) -> bool:
        """判断是否可以执行此步骤"""

class Pipeline:
    """管道执行器"""
    
    def __init__(self, steps: List[PipelineStep]):
        self.steps = steps
    
    async def run(self, context: PipelineContext) -> PipelineResult:
        for step in self.steps:
            if step.can_execute(context):
                context = await step.execute(context)
                if context.is_terminal():
                    break
        return PipelineResult.from_context(context)
```

**设计原则**:
- ✅ 开闭原则：对扩展开放，对修改关闭
- ✅ 可插拔：步骤可以自由组合
- ✅ 可测试：每个步骤独立测试

**步骤定义**:
| 步骤 | 类名 | 职责 |
|------|------|------|
| 下载 | DownloadStep | 下载视频文件 |
| 转写 | TranscribeStep | 调用 Qwen 转写 |
| 导出 | ExportStep | 导出为 Markdown |
| 清理 | CleanupStep | 清理临时文件 |

---

### 3.3 配置系统重构

**当前状态**: 配置来源分散（DB、文件、环境变量）

**重构策略**: 单一配置入口 + 类型安全

**重构后结构**:
```python
class AppConfig:
    """统一应用配置接口"""
    
    # Runtime settings (SystemSettings)
    @property
    def concurrency(self) -> int:
        """并发数"""
    
    @property
    def auto_transcribe(self) -> bool:
        """自动转写"""
    
    @property
    def auto_delete(self) -> bool:
        """自动删除源文件"""
    
    # File settings (config.yaml)
    @property
    def download_path(self) -> Path:
        """下载路径"""
    
    @property
    def database_path(self) -> Path:
        """数据库路径"""
    
    # Environment settings
    @property
    def debug_mode(self) -> bool:
        """调试模式"""
```

**设计原则**:
- ✅ 单一来源：所有配置通过统一入口访问
- ✅ 类型安全：属性返回正确的类型
- ✅ 懒加载：按需加载配置

---

### 3.4 API 分层重构

**当前状态**: `api/routers/tasks.py` 640行，路由层包含业务逻辑

**重构策略**: 路由层 + 服务层分离

**重构后结构**:
```
api/
├── routers/
│   └── tasks.py      # 路由层（仅处理HTTP）
└── services/
    └── task_service.py  # 业务逻辑层
```

**路由层职责**:
- HTTP 请求解析
- 参数校验
- 响应格式化
- 异常处理

**服务层职责**:
- 业务逻辑处理
- 数据访问
- 事务管理

**代码示例**:
```python
# 路由层
@router.post("/tasks")
async def create_task(request: TaskCreateRequest) -> TaskResponse:
    task = await task_service.create(request.dict())
    return TaskResponse.from_orm(task)

# 服务层
class TaskService:
    async def create(self, data: dict) -> Task:
        # 业务逻辑
        task = Task(**data)
        await self.repository.save(task)
        return task
```

---

### 3.5 错误处理统一

**当前状态**: 异常处理分散，错误信息不统一

**重构策略**: 统一异常类型 + 错误处理中间件

**统一异常类型**:
| 异常类 | HTTP状态码 | 用途 |
|--------|-----------|------|
| `AppError` | 400 | 应用层错误 |
| `NotFoundError` | 404 | 资源不存在 |
| `ValidationError` | 422 | 参数校验失败 |
| `ConfigurationError` | 500 | 配置错误 |
| `ExternalServiceError` | 503 | 外部服务错误 |

**错误响应格式**:
```json
{
  "code": "TASK_NOT_FOUND",
  "message": "任务不存在",
  "details": {
    "task_id": "task-xxx"
  }
}
```

---

### 3.6 日志系统优化

**当前状态**: 日志格式不一致，缺少上下文

**重构策略**: 结构化日志 + 上下文注入

**日志格式**:
```python
logger.info(
    "任务开始执行",
    extra={
        "task_id": task_id,
        "task_type": task_type,
        "creator_uid": creator_uid
    }
)
```

**日志上下文**:
| 字段 | 说明 | 是否必选 |
|------|------|----------|
| request_id | 请求ID | 是（HTTP请求） |
| task_id | 任务ID | 是（任务相关） |
| creator_uid | 创作者UID | 是（创作者相关） |
| asset_id | 素材ID | 否 |

---

### 3.7 代码规范统一

**当前状态**: 命名风格不一致，缺少类型注解

**重构策略**: 代码规范文档 + 自动化检查

**命名规范**:
| 类型 | 规范 | 示例 |
|------|------|------|
| 类名 | PascalCase | VideoDownloader |
| 函数名 | snake_case | download_video |
| 变量名 | snake_case | max_retries |
| 常量 | UPPER_SNAKE_CASE | MAX_RETRY_COUNT |
| 模块名 | snake_case | video_downloader.py |

**类型注解要求**:
- ✅ 函数参数必须标注类型
- ✅ 返回值必须标注类型
- ✅ 复杂类型使用 TypedDict 或 dataclass
- ✅ 使用 Optional[] 表示可选值

**自动化工具**:
- `mypy`: 类型检查
- `ruff`: 代码规范检查
- `black`: 代码格式化