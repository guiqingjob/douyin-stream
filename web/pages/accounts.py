"""
账号与配额页面
"""

from pathlib import Path

import streamlit as st

from web.constants import QWEN_AUTH_PATH
from web.utils import format_size, safe_json_display


# render_accounts
"""渲染账号与配额页面"""
def _render_account_list() -> None:
    """渲染账号列表"""
    st.subheader("已配置的转写账号")

    accounts_config = Path("config/transcribe/accounts.json")
    if accounts_config.exists():
        import json

        with open(accounts_config, encoding="utf-8") as f:
            accounts = json.load(f)

        if isinstance(accounts, list) and accounts:
            st.success(f"已检测到 {len(accounts)} 个转写账号配置")
            for i, acc in enumerate(accounts):
                with st.expander(f"账号 {i + 1}: {acc.get('id', 'unknown')}"):
                    st.json(acc)
        else:
            st.info("账号文件存在，但未发现可用的多账号配置。")
    else:
        st.info("当前使用默认单账号模式。")
        if QWEN_AUTH_PATH.exists():
            st.success(f"✅ 已检测到认证文件：{QWEN_AUTH_PATH.name}")
            st.caption(f"文件大小：{format_size(QWEN_AUTH_PATH.stat().st_size)}")
        else:
            st.error("❌ 未检测到转写认证文件，请先完成认证。")


def _render_quota_query() -> None:
    """渲染配额查询"""
    st.subheader("转写配额")
    st.caption("如果查询失败，优先检查认证状态是否有效。")

    if st.button("查询当前配额", type="primary"):
        with st.spinner("正在查询..."):
            quota = _get_quota()
            if quota:
                safe_json_display(quota)
            else:
                st.warning("无法获取配额，请确认已完成认证且认证仍有效。")


def _get_quota() -> dict | None:
    """获取配额信息"""
    try:
        import asyncio

        from media_tools.transcribe.quota import get_quota_snapshot

        if not QWEN_AUTH_PATH.exists():
            return None

        async def _fetch():
            return await get_quota_snapshot(auth_state_path=str(QWEN_AUTH_PATH))

        snapshot = asyncio.run(_fetch())
        return {
            "used_minutes": snapshot.used_minutes if hasattr(snapshot, "used_minutes") else 0,
            "total_minutes": snapshot.total_minutes if hasattr(snapshot, "total_minutes") else 0,
            "remaining_minutes": snapshot.remaining_minutes if hasattr(snapshot, "remaining_minutes") else 0,
        }
    except Exception as e:
        st.error(f"配额查询失败: {e}")
        return None
st.title("🔑 账号与配额")
st.caption("查看转写认证状态、已配置账号以及当前配额。")

tab1, tab2 = st.tabs(["📋 账号列表", "📊 配额查询"])

with tab1:
    _render_account_list()
with tab2:
    _render_quota_query()


