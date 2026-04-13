"""
关注管理页面
"""

import streamlit as st
import json
from pathlib import Path


def render_following() -> None:
    """渲染关注管理页面"""
    st.title("👤 关注列表管理")

    tab1, tab2, tab3 = st.tabs(["📋 查看列表", "➕ 添加关注", "📤 导入/导出"])

    with tab1:
        _render_user_list()
    with tab2:
        _render_add_user()
    with tab3:
        _render_import_export()


def _render_user_list() -> None:
    """渲染用户列表"""
    try:
        from media_tools.douyin.utils.following import list_users

        users = list_users()

        if not users:
            st.info("关注列表为空，请添加博主")
            return

        st.success(f"共关注 {len(users)} 位博主")

        # 表格展示
        data = []
        for user in users:
            data.append(
                {
                    "UID": user.get("uid", ""),
                    "昵称": user.get("nickname", user.get("name", "未知")),
                    "粉丝数": user.get("follower_count", 0),
                    "视频数": user.get("video_count", user.get("aweme_count", 0)),
                    "关注时间": user.get("last_updated", "")[:10],
                }
            )

        st.dataframe(data, use_container_width=True, hide_index=True)

        # 删除操作
        st.divider()
        st.subheader("➖ 删除关注")
        user_options = {
            f"{u.get('nickname', u.get('name', u.get('uid', '未知')))} ({u.get('uid', '')})": u.get(
                "uid", ""
            )
            for u in users
        }

        selected = st.selectbox("选择要删除的博主", list(user_options.keys()))

        # 使用两步骤确认：先点击删除按钮，再弹窗确认
        if "confirm_delete_uid" not in st.session_state:
            st.session_state.confirm_delete_uid = None
        
        if st.button("🗑️ 删除选中", type="primary"):
            st.session_state.confirm_delete_uid = selected
        
        # 显示确认步骤
        if st.session_state.confirm_delete_uid == selected:
            st.warning(f"⚠️ 确认删除 **{selected}**？此操作不可恢复！")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ 确认删除", type="primary"):
                    uid = user_options[selected]
                    ok = _remove_user(uid)
                    if ok:
                        st.success(f"已删除: {selected}")
                        st.session_state.confirm_delete_uid = None
                        st.rerun()
                    else:
                        st.error("删除失败")
            with col2:
                if st.button("❌ 取消"):
                    st.session_state.confirm_delete_uid = None
                    st.rerun()

    except Exception as e:
        st.error(f"加载关注列表失败: {e}")


def _render_add_user() -> None:
    """渲染添加用户"""
    st.subheader("➕ 添加关注博主")

    url = st.text_input(
        "抖音主页链接",
        placeholder="https://www.douyin.com/user/MS4wLjABAAAA...",
    )

    if st.button("添加", type="primary"):
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
        if st.button("导出为 JSON"):
            data = _export_users()
            if data:
                st.download_button(
                    label="下载 JSON",
                    data=data,
                    file_name="following.json",
                    mime="application/json",
                )

    with col2:
        st.markdown("**导入**")
        uploaded = st.file_uploader("上传 JSON 文件", type=["json"])
        if uploaded and st.button("导入"):
            content = uploaded.read().decode("utf-8")
            ok, msg = _import_users(content)
            if ok:
                st.success(msg)
            else:
                st.error(msg)


def _add_user(url: str) -> tuple[bool, dict | None]:
    """添加用户"""
    try:
        from media_tools.douyin.core.following_mgr import add_user

        return add_user(url)
    except Exception as e:
        st.error(f"添加失败: {e}")
        return False, None


def _remove_user(uid: str) -> bool:
    """删除用户"""
    try:
        from media_tools.douyin.core.following_mgr import remove_user

        return remove_user(uid)
    except Exception as e:
        st.error(f"删除失败: {e}")
        return False


def _export_users() -> str | None:
    """导出用户列表为 JSON"""
    try:
        from media_tools.douyin.utils.following import list_users

        users = list_users()
        return json.dumps({"users": users}, ensure_ascii=False, indent=2)
    except Exception:
        return None


def _import_users(content: str) -> tuple[bool, str]:
    """导入用户列表"""
    try:
        data = json.loads(content)
        users = data.get("users", [])
        if not isinstance(users, list):
            return False, "JSON 格式错误: 应包含 'users' 数组"

        from media_tools.douyin.core.following_mgr import add_user

        imported = 0
        skipped = 0
        for user in users:
            if isinstance(user, dict) and user.get("uid"):
                ok, _ = add_user(user["uid"], user, merge=True)
                if ok:
                    imported += 1
                else:
                    skipped += 1

        return True, f"导入完成: 新增 {imported} 位, 跳过 {skipped} 位"
    except json.JSONDecodeError as e:
        return False, f"JSON 格式错误: {e}"
    except Exception as e:
        return False, f"导入失败: {e}"
