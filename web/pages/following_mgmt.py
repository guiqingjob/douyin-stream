"""
关注管理页面
"""

import json

import streamlit as st

from web.components.ui_patterns import render_empty_state, render_highlight_card, render_summary_metrics, render_table_section
from web.constants import PAGE_DOWNLOAD

from media_tools.logger import get_logger
logger = get_logger('web')



# render_following_mgmt
"""渲染关注管理页面"""
def _render_following_list() -> None:
    """渲染来源列表"""
    st.subheader("📋 来源列表")
    st.caption("这里展示所有可用于批量拉取素材的来源。")

    try:
        from media_tools.douyin.utils.following import list_users

        users = list_users()
        if not users:
            render_empty_state("来源列表为空。", "先添加一个博主主页链接，后续才能按来源批量拉取素材。")
            return

        total_users = len(users)
        nicknames = [u.get("nickname", u.get("name", "")).strip() for u in users]
        named_users = sum(1 for name in nicknames if name)
        render_summary_metrics(
            [
                {"label": "来源数量", "value": total_users},
                {"label": "可批量拉取", "value": total_users},
                {"label": "已命名来源", "value": named_users},
                {"label": "待补全昵称", "value": total_users - named_users},
            ]
        )

        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            sort_by = st.selectbox("排序方式", ["默认", "UID", "昵称"])
        with filter_col2:
            search = st.text_input("搜索来源", placeholder="输入昵称或 UID")

        if sort_by == "UID":
            users = sorted(users, key=lambda u: u.get("uid", ""))
        elif sort_by == "昵称":
            users = sorted(users, key=lambda u: u.get("nickname", u.get("name", "")))

        if search:
            users = [
                u
                for u in users
                if search.lower() in u.get("nickname", u.get("name", "")).lower() or search in u.get("uid", "")
            ]

        if not users:
            render_empty_state("没有符合搜索条件的来源。", "可以清空搜索条件，或换一种排序方式重新查看。")
            return

        latest_user = users[0]
        render_highlight_card(
            "来源列表概览",
            latest_user.get("nickname", latest_user.get("name", latest_user.get("uid", "未知来源"))),
            [
                f"UID: {latest_user.get('uid', '-')}",
                f"视频数: {latest_user.get('aweme_count', '-')}",
            ],
        )

        table_data = []
        for user in users:
            table_data.append(
                {
                    "UID": user.get("uid", ""),
                    "昵称": user.get("nickname", user.get("name", "未知")),
                    "粉丝数": user.get("follower_count", user.get("mplatform_followers_count", "-")),
                    "视频数": user.get("aweme_count", "-"),
                }
            )

        render_table_section(
            table_data,
            empty_message="当前没有可展示的来源数据。",
            hint="如果来源已经整理好，下一步通常是去下载中心执行批量拉取。",
        )
        if st.button("📥 去下载中心批量拉取", key="go_download_from_following"):
            st.switch_page("web/pages/download_center.py")
    except Exception as e:
        logger.exception('发生异常')
        st.error(f"加载来源列表失败: {e}")


def _render_add_following() -> None:
    """渲染添加来源"""
    st.subheader("➕ 添加来源")
    st.caption("新增一个博主主页链接，后续就可以从这个来源批量拉取素材。")

    url = st.text_input(
        "抖音主页链接",
        placeholder="https://www.douyin.com/user/MS4wLjABAAAA...",
    )

    if st.button("➕ 添加来源", type="primary"):
        if not url:
            st.warning("请输入链接")
            return

        with st.spinner("正在获取用户信息..."):
            ok, user = _add_user(url)
            if ok and user:
                st.success(f"✅ 添加成功: {user.get('nickname', user.get('uid', '未知'))}")
                st.info("现在可以前往下载中心，从关注列表批量拉取这个来源的素材。")
                st.rerun()
            else:
                st.error("添加失败，请检查链接是否正确或 Cookie 是否有效")


def _render_import_export() -> None:
    """渲染导入导出"""
    st.subheader("📤 导入 / 导出来源列表")
    st.caption("适合做来源备份、迁移到其他环境，或一次性导入一批来源。")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**导出来源**")
        st.caption("导出当前来源列表，用于备份或迁移。")
        data = _export_users()
        if data:
            st.download_button(
                label="📥 下载 JSON",
                data=data,
                file_name="following.json",
                mime="application/json",
                use_container_width=True,
            )
        else:
            render_empty_state("暂无可导出的来源数据。")

    with col2:
        st.markdown("**导入来源**")
        st.caption("导入 JSON 文件，将来源列表恢复到当前环境。")
        uploaded = st.file_uploader("上传 JSON 文件", type=["json"])
        if uploaded and st.button("📤 开始导入", use_container_width=True):
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
        logger.exception('发生异常')
        return False, str(e)


def _export_users() -> str:
    """导出用户"""
    try:
        from media_tools.douyin.utils.following import load_following

        data = load_following()
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception:
        logger.exception('发生异常')
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
                logger.exception('发生异常')
                continue

        return True, f"成功导入 {count} 个来源"
    except Exception as e:
        logger.exception('发生异常')
        return False, f"导入失败: {e}"
st.title("👥 关注管理")
st.caption("把你持续观察的博主整理成来源列表，供后续批量拉取素材使用。")

tab1, tab2, tab3 = st.tabs(["📋 来源列表", "➕ 添加来源", "📤 导入 / 导出"])

with tab1:
    _render_following_list()
with tab2:
    _render_add_following()
with tab3:
    _render_import_export()


