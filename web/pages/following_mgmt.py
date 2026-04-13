"""
关注管理页面 - 重构版
"""

import streamlit as st
import json
from pathlib import Path


def render_following_mgmt() -> None:
    """渲染关注管理页面"""
    st.title("👥 关注管理")
    
    tab1, tab2, tab3 = st.tabs(["📋 关注列表", "➕ 添加关注", "📤 导入/导出"])
    
    with tab1:
        _render_following_list()
    with tab2:
        _render_add_following()
    with tab3:
        _render_import_export()


def _render_following_list() -> None:
    """渲染关注列表"""
    st.subheader("📋 关注列表")
    
    try:
        from media_tools.douyin.utils.following import list_users
        
        users = list_users()
        
        if not users:
            st.info("关注列表为空，请先添加关注的博主。")
            return
        
        st.success(f"共 **{len(users)}** 个关注的博主")
        
        # 显示选项
        col1, col2 = st.columns(2)
        with col1:
            sort_by = st.selectbox("排序方式", ["默认", "UID", "昵称"])
        with col2:
            search = st.text_input("搜索", placeholder="输入昵称或 UID")
        
        # 排序
        if sort_by == "UID":
            users = sorted(users, key=lambda u: u.get("uid", ""))
        elif sort_by == "昵称":
            users = sorted(users, key=lambda u: u.get("nickname", u.get("name", "")))
        
        # 搜索过滤
        if search:
            users = [
                u for u in users
                if search.lower() in u.get("nickname", u.get("name", "")).lower()
                or search in u.get("uid", "")
            ]
        
        # 显示表格
        if users:
            table_data = []
            for u in users:
                table_data.append({
                    "UID": u.get("uid", ""),
                    "昵称": u.get("nickname", u.get("name", "未知")),
                    "粉丝数": u.get("follower_count", u.get("mplatform_followers_count", "-")),
                    "视频数": u.get("aweme_count", "-"),
                })
            
            st.dataframe(table_data, use_container_width=True, hide_index=True)
            
            # 批量操作
            st.divider()
            st.subheader("批量操作")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📥 下载选中", use_container_width=True):
                    st.info("下载功能开发中...")
            with col2:
                if st.button("🗑️ 删除选中", use_container_width=True):
                    st.info("删除功能开发中...")
        
    except Exception as e:
        st.error(f"加载关注列表失败: {e}")


def _render_add_following() -> None:
    """渲染添加关注"""
    st.subheader("➕ 添加关注博主")
    
    url = st.text_input(
        "抖音主页链接",
        placeholder="https://www.douyin.com/user/MS4wLjABAAAA...",
    )
    
    if st.button("➕ 添加", type="primary"):
        if not url:
            st.warning("请输入链接")
            return
        
        with st.spinner("正在获取用户信息..."):
            ok, user = _add_user(url)
            if ok and user:
                st.success(f"✅ 添加成功: {user.get('nickname', user.get('uid', '未知'))}")
                st.rerun()
            else:
                st.error("添加失败，请检查链接是否正确或 Cookie 是否有效")


def _render_import_export() -> None:
    """渲染导入导出"""
    st.subheader("📤 导入/导出关注列表")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**导出**")
        if st.button("📥 导出为 JSON", use_container_width=True):
            data = _export_users()
            if data:
                st.download_button(
                    label="⬇️ 下载 JSON",
                    data=data,
                    file_name="following.json",
                    mime="application/json",
                    use_container_width=True,
                )
    
    with col2:
        st.markdown("**导入**")
        uploaded = st.file_uploader("上传 JSON 文件", type=["json"])
        if uploaded and st.button("📤 导入", use_container_width=True):
            content = uploaded.read().decode("utf-8")
            ok, msg = _import_users(content)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)


def _add_user(url: str) -> tuple:
    """添加用户"""
    try:
        from media_tools.douyin.core.following_mgr import add_user
        return add_user(url)
    except Exception as e:
        return False, str(e)


def _remove_user(uid: str) -> bool:
    """删除用户"""
    try:
        from media_tools.douyin.core.following_mgr import remove_user
        return remove_user(uid)
    except Exception:
        return False


def _export_users() -> str:
    """导出用户"""
    try:
        from media_tools.douyin.utils.following import load_following
        data = load_following()
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception:
        return ""


def _import_users(content: str) -> tuple:
    """导入用户"""
    try:
        data = json.loads(content)
        users = data.get("users", data if isinstance(data, list) else [])
        
        count = 0
        for user in users:
            try:
                from media_tools.douyin.core.following_mgr import add_user
                uid = user.get("uid")
                if uid:
                    add_user(uid, user, merge=True)
                    count += 1
            except Exception:
                continue
        
        return True, f"成功导入 {count} 个用户"
    except Exception as e:
        return False, f"导入失败: {e}"
