from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PageSpec:
    filename: str
    title: str
    icon: str
    group: str
    summary: str
    default: bool = False


WEB_DIR = Path(__file__).resolve().parent

PAGE_SPECS: tuple[PageSpec, ...] = (
    PageSpec("home.py", "工作台", "🏠", "总览", "查看系统状态与下一步建议", default=True),
    PageSpec("download_center.py", "下载中心", "📥", "内容生产", "获取抖音素材到本地素材库"),
    PageSpec("transcribe_center.py", "转写中心", "🎙️", "内容生产", "把素材批量转成文稿"),
    PageSpec("asset_library.py", "资产大盘", "📂", "内容生产", "集中查看视频与文稿资产"),
    PageSpec("following_mgmt.py", "关注管理", "👥", "来源与认证", "维护来源列表，服务批量拉取"),
    PageSpec("accounts.py", "账号与认证", "🔑", "来源与认证", "管理下载与转写所需认证"),
    PageSpec("cleanup.py", "清理与备份", "🧹", "维护", "清理本地空间并备份关键数据"),
    PageSpec("settings.py", "系统配置", "⚙️", "维护", "环境检测、预设与常见修复"),
)


def build_navigation(st):
    grouped_pages: dict[str, list] = {}
    for spec in PAGE_SPECS:
        grouped_pages.setdefault(spec.group, []).append(
            st.Page(
                str(WEB_DIR / "pages" / spec.filename),
                title=spec.title,
                icon=spec.icon,
                default=spec.default,
            )
        )
    return st.navigation(grouped_pages)


def get_navigation_summary() -> list[tuple[str, str]]:
    return [(spec.title, spec.summary) for spec in PAGE_SPECS]
