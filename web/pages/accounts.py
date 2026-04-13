"""
账号与配额页面
"""

from pathlib import Path

import streamlit as st

from web.constants import QWEN_AUTH_PATH
from web.components.ui_patterns import render_page_header
from web.utils import format_size, safe_json_display

from media_tools.logger import get_logger
logger = get_logger('web')



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
        logger.exception('发生异常')
        st.error(f"配额查询失败: {e}")
        return None


def _render_auth_config() -> None:
    """渲染手动认证配置"""
    st.subheader("手动认证配置")
    st.caption("您可以直接从浏览器复制 Cookie 并粘贴到此处。所有认证信息将统一存储在 `.auth/` 目录下。")

    st.markdown("#### 抖音 Cookie")
    st.markdown("1. 登录 [抖音网页版](https://www.douyin.com)\n2. 打开开发者工具 (F12) -> Network\n3. 找到任意请求，复制 `Cookie` 请求头\n4. 粘贴到下方：")
    
    douyin_cookie = st.text_area("抖音 Cookie", placeholder="sessionid=...; ttwid=...", key="douyin_cookie_input")
    if st.button("保存抖音认证", type="primary"):
        if not douyin_cookie:
            st.warning("请输入抖音 Cookie")
        else:
            _save_douyin_cookie(douyin_cookie)
            
    st.divider()

    st.markdown("#### Qwen (通义千问) Cookie")
    st.markdown("1. 登录 [通义千问](https://www.qianwen.com)\n2. 打开开发者工具 (F12) -> Network\n3. 找到任意请求，复制 `Cookie` 请求头\n4. 粘贴到下方：")

    qwen_cookie = st.text_area("Qwen Cookie", placeholder="tongyi_sso_ticket=...; login_aliyunid_ticket=...", key="qwen_cookie_input")
    if st.button("保存 Qwen 认证", type="primary"):
        if not qwen_cookie:
            st.warning("请输入 Qwen Cookie")
        else:
            _save_qwen_cookie(qwen_cookie)


def _save_douyin_cookie(raw_cookie: str) -> None:
    from media_tools.douyin.utils.auth_parser import AuthParser
    from media_tools.douyin.core.config_mgr import ConfigManager
    
    parser = AuthParser()
    success, msg, cookies_dict = parser.validate_data(raw_cookie, "cookie", "douyin")
    
    if not success:
        st.error(f"Cookie 解析失败: {msg}")
        return
        
    try:
        cfg = ConfigManager()
        cfg.set("cookie", raw_cookie.strip())
        cfg.save()
        st.success("✅ 抖音认证已保存！")
        st.rerun()
    except Exception as e:
        st.error(f"保存失败: {e}")


def _save_qwen_cookie(raw_cookie: str) -> None:
    from media_tools.douyin.utils.auth_parser import AuthParser
    import json
    from web.constants import QWEN_AUTH_PATH

    parser = AuthParser()
    success, msg, cookies_dict = parser.validate_data(raw_cookie, "cookie", "qwen")
    
    if not success:
        st.error(f"Cookie 解析失败: {msg}")
        return

    playwright_cookies = []
    
    core_keys = {
        "tongyi_sso_ticket", 
        "tongyi_sso_ticket_hash", 
        "login_aliyunid_ticket", 
        "cookie2", 
        "XSRF-TOKEN", 
        "atpsida",
        "cna"
    }
    
    for k, v in cookies_dict.items():
        if k in core_keys or "tongyi" in k.lower():
            playwright_cookies.append({
                "name": k,
                "value": v,
                "domain": ".qianwen.com",
                "path": "/",
                "expires": -1,
                "httpOnly": False,
                "secure": False,
                "sameSite": "Lax"
            })

    state = {
        "cookies": playwright_cookies,
        "origins": []
    }

    try:
        import sqlite3
        import datetime
        from media_tools.douyin.core.config_mgr import get_config
        db_path = get_config().get_db_path()
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO auth_credentials (platform, auth_data, is_valid, last_check_time) VALUES (?, ?, ?, ?)",
                ("qwen", json.dumps(state), True, datetime.datetime.now())
            )
            conn.commit()
            
        # 仍然写入一份兼容性文件，以免旧代码断裂
        QWEN_AUTH_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(QWEN_AUTH_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
            
        st.success("✅ Qwen 认证已保存！(已简化并存入数据库)")
        st.rerun()
    except Exception as e:
        st.error(f"保存失败: {e}")


render_page_header("🔑 账号与配额", "查看转写认证状态、已配置账号以及当前配额。")

tab1, tab2, tab3 = st.tabs(["📋 账号列表", "📊 配额查询", "🔑 认证配置"])

with tab1:
    _render_account_list()
with tab2:
    _render_quota_query()
with tab3:
    _render_auth_config()
