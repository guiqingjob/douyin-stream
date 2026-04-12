"""
账号管理页面
"""

import streamlit as st
from pathlib import Path


def render_accounts() -> None:
    """渲染账号管理页面"""
    st.title("🔑 账号管理")

    tab1, tab2 = st.tabs(["📋 账号列表", "📊 配额查询"])

    with tab1:
        _render_account_list()
    with tab2:
        _render_quota_query()


def _render_account_list() -> None:
    """渲染账号列表"""
    st.subheader("已配置的转写账号")

    accounts_config = Path("config/transcribe/accounts.json")
    if accounts_config.exists():
        import json

        with open(accounts_config, encoding="utf-8") as f:
            accounts = json.load(f)

        if isinstance(accounts, list) and accounts:
            for i, acc in enumerate(accounts):
                with st.expander(f"账号 {i+1}: {acc.get('id', 'unknown')}"):
                    st.json(acc)
        else:
            st.info("未配置多账号")
    else:
        st.info("使用默认单账号模式")
        auth_path = Path(".auth/qwen-storage-state.json")
        if auth_path.exists():
            st.success(f"✅ 认证文件存在: {auth_path}")
            st.caption(f"文件大小: {auth_path.stat().st_size / 1024:.2f} KB")
        else:
            st.error("❌ 认证文件不存在")


def _render_quota_query() -> None:
    """渲染配额查询"""
    st.subheader("配额查询")

    if st.button("查询当前配额", type="primary"):
        with st.spinner("正在查询..."):
            quota = _get_quota()
            if quota:
                st.json(quota)
            else:
                st.warning("无法获取配额，请确认已认证")


def _get_quota() -> dict | None:
    """获取配额信息"""
    try:
        import asyncio
        from media_tools.transcribe.quota import get_quota_snapshot

        auth_path = Path(".auth/qwen-storage-state.json")
        if not auth_path.exists():
            return None

        async def _fetch():
            return await get_quota_snapshot(auth_state_path=str(auth_path))

        snapshot = asyncio.run(_fetch())
        return {
            "used_minutes": snapshot.used_minutes if hasattr(snapshot, "used_minutes") else 0,
            "total_minutes": snapshot.total_minutes if hasattr(snapshot, "total_minutes") else 0,
            "remaining_minutes": snapshot.remaining_minutes if hasattr(snapshot, "remaining_minutes") else 0,
        }
    except Exception as e:
        st.error(f"配额查询失败: {e}")
        return None
