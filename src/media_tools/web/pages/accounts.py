"""
账号与配额页面
"""

from pathlib import Path
import json
import sqlite3
import asyncio
import datetime

import streamlit as st

from media_tools.web.constants import QWEN_AUTH_PATH
from media_tools.web.components.ui_patterns import render_page_header
from media_tools.web.utils import format_size, safe_json_display
from media_tools.logger import get_logger
from media_tools.douyin.core.config_mgr import ConfigManager, get_config
from media_tools.douyin.utils.auth_parser import AuthParser
from media_tools.transcribe.quota import get_quota_snapshot

logger = get_logger('web')

# ---- 状态检查函数 ----

def _check_douyin_status() -> bool:
    """检查抖音是否已配置有效 Cookie"""
    cfg = ConfigManager()
    return cfg.has_cookie()

def _check_qwen_status() -> bool:
    """检查 Qwen 是否已配置且有效"""
    if not QWEN_AUTH_PATH.exists():
        return False
    try:
        with open(QWEN_AUTH_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return bool(data.get('cookies'))
    except:
        return False

def _get_qwen_quota() -> dict | None:
    """获取 Qwen 配额"""
    if not _check_qwen_status():
        return None
    try:
        async def _fetch():
            return await get_quota_snapshot(auth_state_path=str(QWEN_AUTH_PATH))
        
        snapshot = asyncio.run(_fetch())
        return {
            "used_minutes": getattr(snapshot, "used_minutes", 0),
            "total_minutes": getattr(snapshot, "total_minutes", 0),
            "remaining_minutes": getattr(snapshot, "remaining_minutes", 0),
        }
    except Exception as e:
        logger.exception('获取配额异常')
        return None

# ---- 卡片渲染函数 ----

def _render_douyin_card() -> None:
    is_ok = _check_douyin_status()
    status_icon = "✅ 正常" if is_ok else "❌ 未认证"
    status_color = "var(--mt-ok)" if is_ok else "var(--mt-danger)"
    
    with st.container(border=True):
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown(f"### 🎵 抖音 (Douyin)")
        with col2:
            st.markdown(f"<div style='text-align: right; color: {status_color}; font-weight: 600; margin-top: 8px;'>状态：{status_icon}</div>", unsafe_allow_html=True)
            
        st.divider()
        
        info_col, _ = st.columns([1, 1])
        with info_col:
            st.caption("认证方式：Cookie")
            st.caption("存储位置：ConfigManager (config/config.yaml)")
            if is_ok:
                cfg = ConfigManager()
                c = cfg.get_cookie() or ""
                st.caption(f"当前 Cookie: `{c[:30]}...`")
                
        with st.expander("更新抖音认证", expanded=not is_ok):
            st.markdown("1. 登录 [抖音网页版](https://www.douyin.com)\n2. 打开开发者工具 (F12) -> Network\n3. 找到任意请求，复制 `Cookie` 请求头\n4. 粘贴到下方：")
            douyin_cookie = st.text_area("抖音 Cookie", placeholder="sessionid=...; ttwid=...", key="douyin_cookie_input", label_visibility="collapsed")
            if st.button("保存并验证抖音认证", type="primary", use_container_width=True):
                if not douyin_cookie:
                    st.warning("请输入抖音 Cookie")
                else:
                    _save_douyin_cookie(douyin_cookie)

def _render_qwen_card() -> None:
    is_ok = _check_qwen_status()
    status_icon = "✅ 正常" if is_ok else "❌ 未认证"
    status_color = "var(--mt-ok)" if is_ok else "var(--mt-danger)"
    
    with st.container(border=True):
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown(f"### 🤖 通义千问 (Qwen)")
        with col2:
            st.markdown(f"<div style='text-align: right; color: {status_color}; font-weight: 600; margin-top: 8px;'>状态：{status_icon}</div>", unsafe_allow_html=True)
            
        st.divider()
        
        # 配额展示区
        if is_ok:
            with st.spinner("获取配额中..."):
                quota = _get_qwen_quota()
            if quota:
                q1, q2, q3 = st.columns(3)
                q1.metric("剩余额度 (分钟)", f"{quota['remaining_minutes']:.1f}")
                q2.metric("已用额度 (分钟)", f"{quota['used_minutes']:.1f}")
                q3.metric("总额度 (分钟)", f"{quota['total_minutes']:.1f}")
            else:
                st.caption("⚠️ 无法获取当前配额，可能 Cookie 已过期。")
            st.divider()
            
        info_col, account_col = st.columns([1, 1])
        with info_col:
            st.caption("认证方式：Playwright State")
            st.caption(f"存储位置：SQLite & `.auth/{QWEN_AUTH_PATH.name}`")
            
        with account_col:
            # 检查多账号池
            accounts_config = Path("config/transcribe/accounts.json")
            if accounts_config.exists():
                try:
                    with open(accounts_config, encoding="utf-8") as f:
                        accs = json.load(f)
                    if isinstance(accs, list) and len(accs) > 0:
                        st.caption(f"**多账号池**：检测到 {len(accs)} 个备用账号。")
                        with st.popover("查看备用账号"):
                            for i, acc in enumerate(accs):
                                acc_id = acc.get('id', f'账号_{i+1}')
                                st.markdown(f"- `{acc_id}`")
                except:
                    pass
            else:
                st.caption("**多账号池**：当前为单账号模式。")

        with st.expander("更新主账号认证", expanded=not is_ok):
            st.markdown("1. 登录 [通义千问](https://www.qianwen.com)\n2. 打开开发者工具 (F12) -> Network\n3. 找到任意请求，复制 `Cookie` 请求头\n4. 粘贴到下方：")
            qwen_cookie = st.text_area("Qwen Cookie", placeholder="tongyi_sso_ticket=...; login_aliyunid_ticket=...", key="qwen_cookie_input", label_visibility="collapsed")
            if st.button("保存并验证 Qwen 认证", type="primary", use_container_width=True):
                if not qwen_cookie:
                    st.warning("请输入 Qwen Cookie")
                else:
                    _save_qwen_cookie(qwen_cookie)

# ---- 保存逻辑 ----

def _save_douyin_cookie(raw_cookie: str) -> None:
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
    parser = AuthParser()
    success, msg, cookies_dict = parser.validate_data(raw_cookie, "cookie", "qwen")
    
    if not success:
        st.error(f"Cookie 解析失败: {msg}")
        return

    playwright_cookies = []
    core_keys = {"tongyi_sso_ticket", "tongyi_sso_ticket_hash", "login_aliyunid_ticket", "cookie2", "XSRF-TOKEN", "atpsida", "cna"}
    
    for k, v in cookies_dict.items():
        if k in core_keys or "tongyi" in k.lower():
            playwright_cookies.append({
                "name": k, "value": v, "domain": ".qianwen.com", "path": "/",
                "expires": -1, "httpOnly": False, "secure": False, "sameSite": "Lax"
            })

    state = {"cookies": playwright_cookies, "origins": []}

    try:
        db_path = get_config().get_db_path()
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO auth_credentials (platform, auth_data, is_valid, last_check_time) VALUES (?, ?, ?, ?)",
                ("qwen", json.dumps(state), True, datetime.datetime.now())
            )
            conn.commit()
            
        QWEN_AUTH_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(QWEN_AUTH_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
            
        st.success("✅ Qwen 认证已保存！")
        st.rerun()
    except Exception as e:
        st.error(f"保存失败: {e}")

# ---- 主渲染逻辑 ----

render_page_header("🔑 账号与认证", "管理系统依赖的所有平台账号与 Cookie 授权。")

_render_douyin_card()
st.write("") # 增加间距
_render_qwen_card()
