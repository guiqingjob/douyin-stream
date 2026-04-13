"""
账号与认证页面
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import streamlit as st

from media_tools.douyin.core.config_mgr import ConfigManager
from media_tools.douyin.utils.auth_parser import AuthParser
from media_tools.logger import get_logger
from media_tools.transcribe.auth_state import has_qwen_auth_state, save_qwen_cookie_string
from media_tools.transcribe.quota import get_quota_snapshot
from media_tools.web.components.ui_patterns import (
    render_cta_section,
    render_empty_state,
    render_page_header,
    render_summary_metrics,
)
from media_tools.web.constants import QWEN_AUTH_PATH
from media_tools.web.services.status import get_system_status
from media_tools.web.utils import get_page_path

logger = get_logger("web")

ACCOUNTS_CONFIG_PATH = Path("config/transcribe/accounts.json")


def _check_douyin_status() -> bool:
    return ConfigManager().has_cookie()


def _check_qwen_status() -> bool:
    return has_qwen_auth_state(QWEN_AUTH_PATH)


def _get_qwen_quota() -> dict | None:
    if not _check_qwen_status():
        return None
    try:
        async def _fetch():
            return await get_quota_snapshot(auth_state_path=str(QWEN_AUTH_PATH))

        snapshot = asyncio.run(_fetch())
        return {
            "used_upload": getattr(snapshot, "used_upload", 0),
            "total_upload": getattr(snapshot, "total_upload", 0),
            "remaining_upload": getattr(snapshot, "remaining_upload", 0),
        }
    except Exception:
        logger.exception("获取配额异常")
        return None


def _load_account_pool() -> list[dict]:
    if not ACCOUNTS_CONFIG_PATH.exists():
        return []
    try:
        with open(ACCOUNTS_CONFIG_PATH, encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except Exception:
        logger.exception("读取账号池失败")
        return []


def _mask_cookie(value: str | None) -> str:
    if not value:
        return "-"
    cleaned = value.strip()
    if len(cleaned) <= 24:
        return cleaned
    return f"{cleaned[:12]}...{cleaned[-8:]}"


def _render_auth_summary() -> dict:
    status = get_system_status()
    accounts = _load_account_pool()
    render_summary_metrics(
        [
            {"label": "下载认证", "value": "已就绪" if status["cookie_ok"] else "待配置"},
            {"label": "转写认证", "value": "已就绪" if status["qwen_ok"] else "待配置"},
            {"label": "账号池数量", "value": len(accounts) or 1},
            {"label": "当前阶段", "value": status["workflow_stage"]},
        ]
    )
    return status


def _render_douyin_auth() -> None:
    is_ok = _check_douyin_status()
    cfg = ConfigManager()
    current_cookie = cfg.get_cookie() or ""

    with st.container(border=True):
        st.subheader("① 下载认证（Douyin）")
        st.caption("下载链路依赖抖音 Cookie。这里只处理下载认证，不混入转写账号信息。")

        render_summary_metrics(
            [
                {"label": "状态", "value": "已就绪" if is_ok else "未认证"},
                {"label": "认证方式", "value": "Cookie"},
            ]
        )

        st.caption("存储位置：`config/config.yaml`")
        if is_ok:
            st.code(_mask_cookie(current_cookie), language="text")

        with st.expander("更新抖音 Cookie", expanded=not is_ok):
            st.markdown(
                """
1. 登录抖音网页版
2. 打开开发者工具 -> Network
3. 复制任意请求里的 `Cookie` 请求头
4. 粘贴到下方保存
"""
            )
            douyin_cookie = st.text_area(
                "抖音 Cookie",
                placeholder="sessionid=...; ttwid=...",
                key="douyin_cookie_input",
                label_visibility="collapsed",
            )
            if st.button("保存并验证抖音认证", type="primary", use_container_width=True):
                if not douyin_cookie:
                    st.warning("请输入抖音 Cookie")
                else:
                    _save_douyin_cookie(douyin_cookie)


def _render_qwen_auth() -> None:
    is_ok = _check_qwen_status()
    quota = _get_qwen_quota() if is_ok else None

    with st.container(border=True):
        st.subheader("② 转写认证（Qwen）")
        st.caption("转写链路依赖主账号 Playwright State。这里只回答“能不能转写、额度够不够”。")

        summary_items = [
            {"label": "状态", "value": "已就绪" if is_ok else "未认证"},
            {"label": "认证方式", "value": "Playwright State"},
        ]
        if quota:
            summary_items.extend(
                [
                    {"label": "剩余额度", "value": quota["remaining_upload"]},
                    {"label": "已用额度", "value": quota["used_upload"]},
                    {"label": "总额度", "value": quota["total_upload"]},
                ]
            )
        render_summary_metrics(summary_items)

        st.caption(f"主认证文件：`.auth/{QWEN_AUTH_PATH.name}`")
        st.caption("当前展示的是 upload 配额视图；如后续底层字段变化，页面文案应保持中性，不再假定单位为分钟。")
        if quota is None and is_ok:
            st.info("当前已检测到认证文件，但无法读取配额。常见原因是 Cookie 过期或状态文件失效。")

        with st.expander("更新主账号认证", expanded=not is_ok):
            st.markdown(
                """
1. 登录通义千问
2. 打开开发者工具 -> Network
3. 复制任意请求里的 `Cookie` 请求头
4. 粘贴到下方保存
"""
            )
            qwen_cookie = st.text_area(
                "Qwen Cookie",
                placeholder="tongyi_sso_ticket=...; login_aliyunid_ticket=...",
                key="qwen_cookie_input",
                label_visibility="collapsed",
            )
            if st.button("保存并验证 Qwen 认证", type="primary", use_container_width=True):
                if not qwen_cookie:
                    st.warning("请输入 Qwen Cookie")
                else:
                    _save_qwen_cookie(qwen_cookie)


def _render_account_pool() -> None:
    accounts = _load_account_pool()

    with st.container(border=True):
        st.subheader("③ 转写账号池")
        st.caption("账号池是转写的备用执行资源，不应该和主认证编辑混在一起。")

        if not accounts:
            render_empty_state("当前未检测到账号池配置。", "默认仍可使用主账号运行转写任务。", icon="🪪")
            return

        render_summary_metrics(
            [
                {"label": "账号池数量", "value": len(accounts)},
                {"label": "主状态文件", "value": accounts[0].get("storageStatePath", "-")},
            ]
        )

        table_rows = []
        for account in accounts:
            table_rows.append(
                {
                    "账号 ID": account.get("id", "-"),
                    "显示名称": account.get("label", "-"),
                    "状态文件": account.get("storageStatePath", "-"),
                }
            )
        st.dataframe(table_rows, use_container_width=True, hide_index=True)
        st.caption("如需新增或切换账号池，请编辑 `config/transcribe/accounts.json`。")


def _save_douyin_cookie(raw_cookie: str) -> None:
    parser = AuthParser()
    success, message, _ = parser.validate_data(raw_cookie, "cookie", "douyin")
    if not success:
        st.error(f"Cookie 解析失败: {message}")
        return

    try:
        cfg = ConfigManager()
        cfg.set("cookie", raw_cookie.strip())
        cfg.save()
        st.success("✅ 抖音认证已保存！")
        st.rerun()
    except Exception as exc:
        st.error(f"保存失败: {exc}")


def _save_qwen_cookie(raw_cookie: str) -> None:
    try:
        state = save_qwen_cookie_string(raw_cookie, QWEN_AUTH_PATH)
    except ValueError as exc:
        st.error(f"Cookie 解析失败: {exc}")
        return
    except Exception as exc:
        st.error(f"保存失败: {exc}")
        return

    st.success(f"✅ Qwen 认证已保存！共写入 {len(state.get('cookies', []))} 个核心 Cookie")
    st.rerun()


render_page_header("🔑 账号与认证", "先确认下载认证和转写认证是否就绪，再看配额与账号池。")
status = _render_auth_summary()

col1, col2 = st.columns([1, 1], gap="large")
with col1:
    _render_douyin_auth()
with col2:
    _render_qwen_auth()

st.divider()
_render_account_pool()

if (not status["cookie_ok"] or not status["qwen_ok"]) and render_cta_section(
    "认证未完成？",
    "完成认证后，首页会自动把你引导到下一步最合适的工作流页面。",
    "🏠 回到工作台",
    "back_home_from_accounts",
):
    st.switch_page(get_page_path("home.py"))
