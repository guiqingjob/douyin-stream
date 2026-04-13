"""
工作台状态卡片组件
"""

from media_tools.web.components.ui_patterns import render_summary_metrics
from media_tools.web.services.status import get_system_status

from media_tools.logger import get_logger
logger = get_logger('web')


def render_home_status_cards() -> dict:
    """渲染工作台状态卡片，并返回统一系统状态。"""
    status = get_system_status()

    render_summary_metrics(
        [
            {
                "label": "下载认证",
                "value": "已就绪" if status["cookie_ok"] else "待配置",
                "delta": "Cookie 可用" if status["cookie_ok"] else "缺少抖音 Cookie",
            },
            {
                "label": "转写认证",
                "value": "已就绪" if status["qwen_ok"] else "待配置",
                "delta": "Qwen 可用" if status["qwen_ok"] else "缺少 Qwen 认证",
            },
            {
                "label": "来源数量",
                "value": status["source_count"],
                "delta": f"素材 {status['downloads_count']} 条",
            },
            {
                "label": "待转写",
                "value": status["pending_transcripts"],
                "delta": f"已完成 {status['transcripts_count']} 篇",
            },
        ]
    )

    render_summary_metrics(
        [
            {
                "label": "本地占用",
                "value": status["storage_usage"],
                "delta": "环境通过" if status["env_ok"] else "请先完成环境检测",
            },
            {
                "label": "当前阶段",
                "value": status["workflow_stage"],
                "delta": "按建议路径逐步推进",
            },
        ]
    )

    return status
