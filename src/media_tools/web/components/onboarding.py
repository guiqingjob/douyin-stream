"""
新手引导组件

首次访问时显示分步引导流程
"""

import streamlit as st

from media_tools.web.constants import PROJECT_ROOT

from media_tools.logger import get_logger
logger = get_logger('web')


# 标记文件路径
_FIRST_VISIT_FILE = PROJECT_ROOT / ".first_visit_done"


def _is_first_visit() -> bool:
    """检查是否首次访问"""
    return not _FIRST_VISIT_FILE.exists()


def _mark_first_visit_done():
    """标记首次访问已完成"""
    _FIRST_VISIT_FILE.touch()
    st.session_state.onboarding_step = None


def render_onboarding() -> None:
    """渲染新手引导流程"""
    if not _is_first_visit():
        return
    
    st.divider()
    st.info("👋 欢迎使用 Media Tools！检测到您是首次使用，请跟随引导完成初始配置。")
    
    # 使用 session_state 管理引导步骤
    if "onboarding_step" not in st.session_state:
        st.session_state.onboarding_step = 1
    
    step = st.session_state.onboarding_step
    
    # 步骤指示器
    steps = ["环境检测", "配置 Cookie", "添加关注", "开始使用"]
    cols = st.columns(len(steps))
    for i, (col, name) in enumerate(zip(cols, steps)):
        if i + 1 < step:
            col.success(f"✅ {name}")
        elif i + 1 == step:
            col.info(f"👉 {name}")
        else:
            col.caption(f"⏳ {name}")
    
    st.divider()
    
    # 步骤 1: 环境检测
    if step == 1:
        st.subheader("🔍 步骤 1: 环境检测")
        st.markdown("首先需要检测您的环境是否配置完整，包括 Python 版本、依赖包、浏览器等。")
        
        if st.button("开始检测", type="primary"):
            with st.spinner("正在检测..."):
                try:
                    from media_tools.douyin.core.env_check import check_all
                    passed, details = check_all()
                    
                    if passed:
                        st.success("✅ 环境检测通过！")
                        st.session_state.onboarding_step = 2
                        st.rerun()
                    else:
                        st.warning("⚠️ 部分检测项未通过，请查看下方详情并修复后重试。")
                        if details:
                            for name, info in details.items():
                                if info.get("ok"):
                                    st.success(f"✅ {name}: {info.get('message', '')}")
                                else:
                                    st.error(f"❌ {name}: {info.get('message', '')}")
                except Exception as e:
                    logger.exception('发生异常')
                    st.error(f"环境检测失败: {e}")
    
    # 步骤 2: 配置 Cookie
    elif step == 2:
        st.subheader("🍪 步骤 2: 配置抖音 Cookie")
        st.markdown("""
        **Cookie 用于访问抖音 API，必须配置后才能使用下载功能。**
        
        **配置步骤：**
        1. 打开浏览器访问 https://www.douyin.com 并登录
        2. 按 F12 打开开发者工具，切换到 Network 标签
        3. 刷新页面，找到任意请求
        4. 在 Request Headers 中找到 `Cookie` 字段，复制整行内容
        5. 粘贴到下方输入框中
        """)
        
        cookie = st.text_area(
            "抖音 Cookie",
            placeholder="name=value; name2=value2; ...",
            height=100,
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("跳过（稍后配置）"):
                st.session_state.onboarding_step = 3
                st.rerun()
        with col2:
            if st.button("保存 Cookie", type="primary"):
                if not cookie:
                    st.warning("请输入 Cookie 内容")
                else:
                    try:
                        from media_tools.douyin.core.config_mgr import ConfigManager

                        cfg = ConfigManager()
                        cfg.set("cookie", cookie.strip())
                        cfg.save()
                        st.success("✅ Cookie 已保存！")
                        st.session_state.onboarding_step = 3
                        st.rerun()
                    except Exception as e:
                        logger.exception('发生异常')
                        st.error(f"保存失败: {e}")
    
    # 步骤 3: 添加关注
    elif step == 3:
        st.subheader("👤 步骤 3: 添加关注的博主")
        st.markdown("""
        **您可以添加关注的抖音博主，之后可以批量下载他们的视频。**
        
        **如何获取博主主页链接：**
        1. 打开抖音 APP 或网页版
        2. 进入您想关注的博主主页
        3. 复制浏览器地址栏的链接
        4. 粘贴到下方输入框中
        """)
        
        url = st.text_input(
            "博主主页链接",
            placeholder="https://www.douyin.com/user/MS4wLjABAAAA...",
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("跳过（稍后添加）"):
                st.session_state.onboarding_step = 4
                st.rerun()
        with col2:
            if st.button("添加关注", type="primary"):
                if not url:
                    st.warning("请输入链接")
                else:
                    with st.spinner("正在获取用户信息..."):
                        try:
                            from media_tools.douyin.core.following_mgr import add_user
                            ok, user = add_user(url)
                            if ok and user:
                                st.success(f"✅ 已添加: {user.get('nickname', '未知')}")
                                # 继续停留在步骤 3，可以添加更多关注
                            else:
                                st.error("添加失败，请检查链接是否正确")
                        except Exception as e:
                            logger.exception('发生异常')
                            st.error(f"添加失败: {e}")
    
    # 步骤 4: 完成
    elif step == 4:
        st.subheader("🎉 恭喜！配置完成")
        st.success("您已完成初始配置，现在可以开始使用 Media Tools 的所有功能了！")
        
        st.markdown("""
        **快速开始：**
        - 🏠 **工作台**: 先看当前状态，再决定下一步
        - 📥 **下载中心**: 下载博主视频或批量拉取素材
        - 🎙️ **转写中心**: 将视频/音频转为文字
        - 👥 **关注管理**: 管理关注的博主列表
        - 🔑 **账号与配额**: 管理转写认证和配额
        - 🗑️ **清理与备份**: 清理过期数据并备份关键内容
        - ⚙️ **系统配置**: 环境检测和配置管理
        """)
        
        if st.button("开始使用", type="primary"):
            _mark_first_visit_done()
            st.rerun()
    
    # 导航按钮
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if step > 1 and st.button("← 上一步", key="onboarding_prev"):
            st.session_state.onboarding_step = step - 1
            st.rerun()
    with col2:
        if step < 4 and st.button("下一步 →", key="onboarding_next"):
            st.session_state.onboarding_step = step + 1
            st.rerun()
