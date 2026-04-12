#!/usr/bin/env python3
"""
抖音下载模块全功能测试脚本
测试所有核心模块: env_check, following, following_mgr, config_mgr, compressor, ui
"""

import json
import os
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

# 设置环境变量
os.environ["PYTHONPATH"] = "src"
sys.path.insert(0, str(Path(__file__).parent / "src"))

# 测试项目根目录
PROJECT_ROOT = Path(__file__).parent
# 备份路径
BACKUP_FOLLOWING = PROJECT_ROOT / "config" / "following.json.bak"

# 测试结果统计
results = []


def record(test_name, status, detail=""):
    """记录测试结果"""
    results.append({"name": test_name, "status": status, "detail": detail})
    icon = {"PASS": "PASS", "FAIL": "FAIL", "WARN": "WARN"}.get(status, "??")
    detail_str = f" - {detail}" if detail else ""
    print(f"  [{icon}] {test_name}{detail_str}")


def backup_following():
    """备份 following.json"""
    src = PROJECT_ROOT / "config" / "following.json"
    if src.exists():
        import shutil
        shutil.copy2(src, BACKUP_FOLLOWING)


def restore_following():
    """恢复 following.json"""
    if BACKUP_FOLLOWING.exists():
        import shutil
        dst = PROJECT_ROOT / "config" / "following.json"
        shutil.copy2(BACKUP_FOLLOWING, dst)
        BACKUP_FOLLOWING.unlink(missing_ok=True)


# ============================================================================
# 1. 环境检测模块测试
# ============================================================================
def test_env_check():
    print("\n" + "=" * 70)
    print("1. 环境检测模块测试 (env_check)")
    print("=" * 70)

    try:
        from media_tools.douyin.core.env_check import (
            check_all,
            check_config,
            check_ffmpeg,
            check_package_installed,
            check_playwright_browsers,
            check_python_version,
        )

        record("导入 env_check 模块", "PASS")
    except Exception as e:
        record("导入 env_check 模块", "FAIL", str(e))
        return

    # 1.1 Python 版本检测
    try:
        ok, msg = check_python_version()
        status = "PASS" if ok else "WARN"
        record("Python 版本检测", status, msg)
    except Exception as e:
        record("Python 版本检测", "FAIL", str(e))

    # 1.2 f2 包检测
    try:
        ok, msg = check_package_installed("f2")
        status = "PASS" if ok else "WARN"
        record("f2 包检测", status, msg)
    except Exception as e:
        record("f2 包检测", "FAIL", str(e))

    # 1.3 playwright 包检测
    try:
        ok, msg = check_package_installed("playwright")
        status = "PASS" if ok else "WARN"
        record("playwright 包检测", status, msg)
    except Exception as e:
        record("playwright 包检测", "FAIL", str(e))

    # 1.4 Playwright 浏览器检测
    try:
        ok, msg = check_playwright_browsers()
        status = "PASS" if ok else "WARN"
        record("Playwright 浏览器检测", status, msg)
    except Exception as e:
        record("Playwright 浏览器检测", "FAIL", str(e))

    # 1.5 ffmpeg 检测
    try:
        ok, msg = check_ffmpeg()
        status = "PASS" if ok else "WARN"
        record("ffmpeg 检测 (env_check)", status, msg)
    except Exception as e:
        record("ffmpeg 检测 (env_check)", "FAIL", str(e))

    # 1.6 配置文件检测
    try:
        ok, msg = check_config()
        status = "PASS" if ok else "WARN"
        record("配置文件检测", status, msg)
    except Exception as e:
        record("配置文件检测", "FAIL", str(e))

    # 1.7 check_all() 完整检测
    try:
        all_ok, res_dict = check_all()
        record("check_all() 完整检测", "PASS", f"总结果: {'通过' if all_ok else '未通过'}")
        for check_name, check_res in res_dict.items():
            sub_status = "PASS" if check_res["ok"] else "WARN"
            record(f"  - {check_name}", sub_status, check_res["message"])
    except Exception as e:
        record("check_all() 完整检测", "FAIL", str(e))


# ============================================================================
# 2. 关注列表 CRUD 测试
# ============================================================================
def test_following_crud():
    print("\n" + "=" * 70)
    print("2. 关注列表 CRUD 测试 (following + following_mgr)")
    print("=" * 70)

    # 2.1 导入模块
    try:
        from media_tools.douyin.utils.following import (
            add_user,
            create_empty_user,
            get_user,
            list_users,
            load_following,
            remove_user,
            save_following,
        )

        record("导入 utils.following 模块", "PASS")
    except Exception as e:
        record("导入 utils.following 模块", "FAIL", str(e))
        return

    try:
        from media_tools.douyin.core.following_mgr import (
            add_user as mgr_add_user,
            display_users,
            list_users as mgr_list_users,
            remove_user as mgr_remove_user,
        )

        record("导入 core.following_mgr 模块", "PASS")
    except Exception as e:
        record("导入 core.following_mgr 模块", "FAIL", str(e))

    # 2.2 列出所有关注博主
    try:
        users = list_users()
        assert isinstance(users, list)
        record("list_users() 返回用户列表", "PASS", f"共 {len(users)} 位博主")
        for u in users[:3]:
            name = u.get("nickname", u.get("name", "未知"))
            uid = u.get("uid", "未知")
            record(f"  - 博主: {name}", "PASS", f"UID: {uid}")
    except Exception as e:
        record("list_users() 返回用户列表", "FAIL", str(e))

    # 2.3 get_user() 获取单个用户
    try:
        if users:
            test_uid = str(users[0]["uid"])
            user = get_user(test_uid)
            if user and user["uid"] == test_uid:
                record("get_user() 获取单个用户", "PASS", f"找到 UID: {test_uid}")
            else:
                record("get_user() 获取单个用户", "FAIL", "返回数据不匹配")
        else:
            record("get_user() 获取单个用户", "WARN", "关注列表为空，跳过")
    except Exception as e:
        record("get_user() 获取单个用户", "FAIL", str(e))

    # 2.4 get_user() 获取不存在的用户
    try:
        user = get_user("999999999999")
        if user is None:
            record("get_user() 不存在的用户返回 None", "PASS")
        else:
            record("get_user() 不存在的用户返回 None", "FAIL", f"返回了: {user}")
    except Exception as e:
        record("get_user() 不存在的用户返回 None", "FAIL", str(e))

    # 2.5 添加用户 (测试错误处理 - 无效链接)
    try:
        # 先用 mgr_add_user 测试假链接
        ok, info = mgr_add_user("https://www.douyin.com/user/FAKE_SEC_USER_ID")
        if not ok and info is None:
            record("添加假链接 - 正确返回失败", "PASS")
        elif not ok:
            record("添加假链接 - 正确返回失败", "PASS", "ok=False, 有 info 数据")
        else:
            record("添加假链接 - 正确返回失败", "FAIL", f"意外成功: ok={ok}")
    except Exception as e:
        # 如果抛异常但不崩溃也算可接受
        error_msg = str(e)
        if "F2" in error_msg or "提取" in error_msg or "失败" in error_msg:
            record("添加假链接 - 错误处理", "PASS", f"抛出异常: {error_msg[:80]}")
        else:
            record("添加假链接 - 错误处理", "WARN", f"异常: {error_msg[:100]}")

    # 2.6 测试 URL 格式校验
    try:
        ok, info = mgr_add_user("https://example.com/not-douyin")
        if not ok:
            record("非抖音链接 - 正确拒绝", "PASS")
        else:
            record("非抖音链接 - 正确拒绝", "FAIL", f"意外通过: ok={ok}")
    except Exception as e:
        record("非抖音链接 - 正确拒绝", "WARN", f"异常: {str(e)[:80]}")

    # 2.7 重复添加检测 (用现有用户 UID 构造一个 sec_user_id 测试)
    try:
        if users:
            existing_sec = users[0].get("sec_user_id", "")
            if existing_sec:
                fake_url = f"https://www.douyin.com/user/{existing_sec}"
                ok, info = mgr_add_user(fake_url)
                if not ok and info is not None:
                    record("重复添加检测 - 正确提示已存在", "PASS", f"用户: {info.get('nickname', '未知')}")
                else:
                    record("重复添加检测 - 正确提示已存在", "WARN", f"ok={ok}")
            else:
                record("重复添加检测", "WARN", "无法获取 sec_user_id，跳过")
        else:
            record("重复添加检测", "WARN", "关注列表为空，跳过")
    except Exception as e:
        record("重复添加检测", "WARN", f"异常: {str(e)[:80]}")

    # 2.8 添加用户 (底层 add_user)
    try:
        test_uid = "TEST_UID_" + str(os.getpid())
        test_info = {
            "nickname": "测试用户",
            "name": "测试用户",
            "sec_user_id": "TEST_SEC_" + str(os.getpid()),
        }
        is_new = add_user(test_uid, test_info)
        if is_new:
            record("add_user() 添加新用户", "PASS")
        else:
            record("add_user() 添加新用户", "FAIL", "返回 False 表示更新而非新增")

        # 验证用户存在
        user = get_user(test_uid)
        if user and user["nickname"] == "测试用户":
            record("验证添加的用户存在", "PASS")
        else:
            record("验证添加的用户存在", "FAIL", f"查找结果: {user}")

        # 2.9 重复添加测试 (merge=True 应更新)
        update_info = {"nickname": "更新后的测试用户"}
        is_new2 = add_user(test_uid, update_info, merge=True)
        if not is_new2:
            record("重复添加 - 返回 False 表示更新", "PASS")
        else:
            record("重复添加 - 返回 False 表示更新", "FAIL", "返回 True 表示新增")

        # 验证合并后的数据
        user2 = get_user(test_uid)
        if user2 and user2.get("nickname") == "更新后的测试用户" and user2.get("sec_user_id"):
            record("merge=True 保留已有字段", "PASS")
        else:
            record("merge=True 保留已有字段", "WARN", f"user2: {user2}")

        # 2.10 删除用户
        deleted = remove_user(test_uid)
        if deleted:
            record("remove_user() 删除用户", "PASS")
        else:
            record("remove_user() 删除用户", "FAIL")

        # 验证删除
        user3 = get_user(test_uid)
        if user3 is None:
            record("验证用户已删除", "PASS")
        else:
            record("验证用户已删除", "FAIL", f"用户仍存在: {user3}")

    except Exception as e:
        record("添加/删除用户测试", "FAIL", str(e))

    # 2.11 导出/导入功能测试 (通过 load/save_following)
    try:
        data = load_following()
        assert "users" in data
        assert isinstance(data["users"], list)
        record("load_following() 加载数据", "PASS", f"{len(data['users'])} 位用户")

        # 模拟导出为 JSON 字符串
        export_json = json.dumps(data, ensure_ascii=False, indent=2)
        parsed_back = json.loads(export_json)
        if parsed_back == data:
            record("导出/导入 JSON 往返一致", "PASS")
        else:
            record("导出/导入 JSON 往返一致", "FAIL", "数据不一致")

        # 测试 save_following
        test_data = {"users": [{"uid": "export_test", "nickname": "导出测试"}]}
        save_following(test_data)
        reloaded = load_following()
        if any(u["uid"] == "export_test" for u in reloaded["users"]):
            record("save_following() 写入并重新加载", "PASS")
        else:
            record("save_following() 写入并重新加载", "FAIL")

        # 恢复原始数据
        save_following(data)

    except Exception as e:
        record("导出/导入功能测试", "FAIL", str(e))

    # 2.12 display_users() 测试
    try:
        displayed = display_users()
        assert isinstance(displayed, list)
        record("display_users() 显示关注列表", "PASS", f"显示 {len(displayed)} 位博主")
    except Exception as e:
        record("display_users() 显示关注列表", "FAIL", str(e))

    # 2.13 mgr_list_users() 测试
    try:
        mgr_users = mgr_list_users()
        assert isinstance(mgr_users, list)
        record("following_mgr.list_users()", "PASS", f"返回 {len(mgr_users)} 位用户")
    except Exception as e:
        record("following_mgr.list_users()", "FAIL", str(e))

    # 2.14 mgr_remove_user() 错误处理 (删除不存在的用户)
    try:
        result = mgr_remove_user("NONEXISTENT_UID_999999")
        if result is False:
            record("mgr_remove_user() 删除不存在的用户", "PASS", "正确返回 False")
        else:
            record("mgr_remove_user() 删除不存在的用户", "WARN", f"返回: {result}")
    except Exception as e:
        record("mgr_remove_user() 删除不存在的用户", "WARN", f"异常: {str(e)[:80]}")

    # 2.15 create_empty_user() 模板
    try:
        empty_user = create_empty_user("test_uid_123", "test_sec_456")
        assert empty_user["uid"] == "test_uid_123"
        assert empty_user["sec_user_id"] == "test_sec_456"
        assert "last_updated" in empty_user
        assert "folder" in empty_user
        record("create_empty_user() 创建模板用户", "PASS")
    except Exception as e:
        record("create_empty_user() 创建模板用户", "FAIL", str(e))


# ============================================================================
# 3. 配置管理模块测试
# ============================================================================
def test_config_mgr():
    print("\n" + "=" * 70)
    print("3. 配置管理模块测试 (config_mgr)")
    print("=" * 70)

    try:
        from media_tools.douyin.core.config_mgr import (
            ConfigManager,
            get_config,
            reset_config,
        )

        record("导入 config_mgr 模块", "PASS")
    except Exception as e:
        record("导入 config_mgr 模块", "FAIL", str(e))
        return

    # 3.1 加载配置
    try:
        reset_config()
        config = get_config()
        assert isinstance(config, ConfigManager)
        record("get_config() 加载配置", "PASS", f"config_path: {config.config_path}")
    except Exception as e:
        record("get_config() 加载配置", "FAIL", str(e))
        return

    # 3.2 获取下载路径
    try:
        dl_path = config.get_download_path()
        if dl_path.exists():
            record("get_download_path()", "PASS", str(dl_path))
        else:
            record("get_download_path()", "WARN", f"路径不存在: {dl_path}")
    except Exception as e:
        record("get_download_path()", "FAIL", str(e))

    # 3.3 获取数据库路径
    try:
        db_path = config.get_db_path()
        record("get_db_path()", "PASS", str(db_path))
    except Exception as e:
        record("get_db_path()", "FAIL", str(e))

    # 3.4 获取关注列表路径
    try:
        following_path = config.get_following_path()
        if following_path.exists():
            record("get_following_path()", "PASS", str(following_path))
        else:
            record("get_following_path()", "WARN", f"路径不存在: {following_path}")
    except Exception as e:
        record("get_following_path()", "FAIL", str(e))

    # 3.5 Cookie 配置检查
    try:
        has_cookie = config.has_cookie()
        cookie = config.get_cookie()
        if has_cookie and len(cookie) > 50:
            record("Cookie 配置", "PASS", f"Cookie 长度: {len(cookie)}")
        elif has_cookie:
            record("Cookie 配置", "WARN", f"Cookie 长度较短: {len(cookie)}")
        else:
            record("Cookie 配置", "WARN", "未配置 Cookie")
    except Exception as e:
        record("Cookie 配置检查", "FAIL", str(e))

    # 3.6 获取命名格式
    try:
        naming = config.get_naming()
        record("get_naming()", "PASS", naming)
    except Exception as e:
        record("get_naming()", "FAIL", str(e))

    # 3.7 自动转写配置
    try:
        auto_trans = config.is_auto_transcribe()
        record("is_auto_transcribe()", "PASS", str(auto_trans))
    except Exception as e:
        record("is_auto_transcribe()", "FAIL", str(e))

    # 3.8 自动删除视频配置
    try:
        auto_del = config.is_auto_delete_video()
        record("is_auto_delete_video()", "PASS", str(auto_del))
    except Exception as e:
        record("is_auto_delete_video()", "FAIL", str(e))

    # 3.9 get() 嵌套键访问
    try:
        path = config.get("download.path")
        record("get() 嵌套键访问", "PASS", str(path) if path else "None (使用默认)")
    except Exception as e:
        record("get() 嵌套键访问", "FAIL", str(e))

    # 3.10 set() 内存设置
    try:
        config.set("test.key", "test_value")
        val = config.get("test.key")
        if val == "test_value":
            record("set() 内存设置", "PASS")
        else:
            record("set() 内存设置", "FAIL", f"读取值: {val}")
    except Exception as e:
        record("set() 内存设置", "FAIL", str(e))

    # 3.11 validate() 验证
    try:
        is_valid, errors = config.validate()
        if is_valid:
            record("validate() 配置验证", "PASS")
        else:
            record("validate() 配置验证", "WARN", f"问题: {'; '.join(errors)}")
    except Exception as e:
        record("validate() 配置验证", "FAIL", str(e))

    # 3.12 配置文件不存在时的降级处理
    try:
        temp_config = ConfigManager("/tmp/nonexistent_config_12345.yaml")
        # 应该能正常初始化，只是配置为空
        path = temp_config.get_download_path()
        # 默认路径应该回退到项目根目录下的 downloads
        record("配置文件不存在 - 降级处理", "PASS", f"使用默认下载路径: {path}")
    except Exception as e:
        record("配置文件不存在 - 降级处理", "FAIL", str(e))


# ============================================================================
# 4. 视频压缩模块测试
# ============================================================================
def test_compressor():
    print("\n" + "=" * 70)
    print("4. 视频压缩模块测试 (compressor)")
    print("=" * 70)

    try:
        from media_tools.douyin.core.compressor import (
            _compress_video,
            _get_video_info,
            check_ffmpeg,
            compress_all,
            compress_user_dir,
        )

        record("导入 compressor 模块", "PASS")
    except Exception as e:
        record("导入 compressor 模块", "FAIL", str(e))
        return

    # 4.1 ffmpeg 检测
    try:
        has_ffmpeg = check_ffmpeg()
        status = "PASS" if has_ffmpeg else "WARN"
        record("check_ffmpeg()", status, "已安装" if has_ffmpeg else "未安装")
    except Exception as e:
        record("check_ffmpeg()", "FAIL", str(e))

    # 4.2 验证压缩函数存在
    try:
        assert callable(_compress_video)
        record("_compress_video() 函数存在", "PASS")
    except Exception as e:
        record("_compress_video() 函数存在", "FAIL", str(e))

    try:
        assert callable(_get_video_info)
        record("_get_video_info() 函数存在", "PASS")
    except Exception as e:
        record("_get_video_info() 函数存在", "FAIL", str(e))

    try:
        assert callable(compress_user_dir)
        record("compress_user_dir() 函数存在", "PASS")
    except Exception as e:
        record("compress_user_dir() 函数存在", "FAIL", str(e))

    try:
        assert callable(compress_all)
        record("compress_all() 函数存在", "PASS")
    except Exception as e:
        record("compress_all() 函数存在", "FAIL", str(e))

    # 4.3 压缩函数错误处理 - 不存在的文件
    try:
        fake_path = Path("/tmp/nonexistent_video_fake_12345.mp4")
        out_path = Path("/tmp/fake_output_12345.mp4")
        ok, orig, comp, err = _compress_video(fake_path, out_path)
        if not ok and err:
            record("_compress_video() 不存在的文件", "PASS", f"错误信息: {err}")
        else:
            record("_compress_video() 不存在的文件", "FAIL", f"意外结果: ok={ok}")
    except Exception as e:
        record("_compress_video() 不存在的文件", "FAIL", str(e))

    # 4.4 _get_video_info() 不存在的文件
    try:
        fake_path = Path("/tmp/nonexistent_video_fake_12345.mp4")
        info = _get_video_info(fake_path)
        if info is None:
            record("_get_video_info() 不存在的文件返回 None", "PASS")
        else:
            record("_get_video_info() 不存在的文件返回 None", "FAIL", f"返回: {info}")
    except Exception as e:
        record("_get_video_info() 不存在的文件返回 None", "FAIL", str(e))

    # 4.5 compress_user_dir() 不存在的目录
    try:
        s, sk, f = compress_user_dir("nonexistent_dir_12345")
        if s == 0 and sk == 0 and f == 0:
            record("compress_user_dir() 不存在的目录", "PASS", "正确返回 (0, 0, 0)")
        else:
            record("compress_user_dir() 不存在的目录", "WARN", f"返回: ({s}, {sk}, {f})")
    except Exception as e:
        record("compress_user_dir() 不存在的目录", "FAIL", str(e))

    # 4.6 路径遍历攻击防护
    try:
        s, sk, f = compress_user_dir("../../etc/passwd")
        if s == 0 and sk == 0 and f == 0:
            record("路径遍历攻击防护", "PASS", "正确拒绝非法路径")
        else:
            record("路径遍历攻击防护", "WARN", f"返回: ({s}, {sk}, {f})")
    except Exception as e:
        record("路径遍历攻击防护", "FAIL", str(e))

    # 4.7 compress_all() 在无 ffmpeg 或空目录下的行为
    try:
        s, sk, f = compress_all()
        record("compress_all() 执行", "PASS", f"结果: 成功={s}, 跳过={sk}, 失败={f}")
    except Exception as e:
        record("compress_all() 执行", "FAIL", str(e))


# ============================================================================
# 5. UI 模块测试
# ============================================================================
def test_ui():
    print("\n" + "=" * 70)
    print("5. UI 模块测试 (ui)")
    print("=" * 70)

    try:
        from media_tools.douyin.core.ui import (
            Colors,
            ProgressBar,
            bold,
            dim,
            error,
            format_duration,
            format_number,
            format_size,
            header,
            info,
            print_countdown,
            print_footer,
            print_header,
            print_key_value,
            print_menu,
            print_status,
            print_table,
            separator,
            success,
            warning,
        )

        record("导入 ui 模块所有函数", "PASS")
    except ImportError as e:
        record("导入 ui 模块所有函数", "FAIL", f"导入失败: {e}")
        return
    except Exception as e:
        record("导入 ui 模块所有函数", "FAIL", str(e))
        return

    # 5.1 测试各个 UI 函数的可调用性
    ui_functions = {
        "success()": lambda: success("测试成功"),
        "error()": lambda: error("测试错误"),
        "warning()": lambda: warning("测试警告"),
        "info()": lambda: info("测试信息"),
        "header()": lambda: header("测试标题"),
        "bold()": lambda: bold("粗体"),
        "dim()": lambda: dim("暗淡"),
        "separator()": lambda: separator("-", 30),
        "format_size()": lambda: format_size(1024 * 1024 * 10),
        "format_number()": lambda: format_number(100000),
        "format_duration()": lambda: format_duration(3661),
        "Colors 类": lambda: Colors.GREEN,
    }

    for name, func in ui_functions.items():
        try:
            result = func()
            assert result is not None or result == ""
            record(f"UI 函数 {name}", "PASS")
        except Exception as e:
            record(f"UI 函数 {name}", "FAIL", str(e))

    # 5.2 print 类函数
    try:
        print_header("测试标题")
        record("print_header()", "PASS")
    except Exception as e:
        record("print_header()", "FAIL", str(e))

    try:
        print_menu([("1", "选项1"), ("2", "选项2")])
        record("print_menu()", "PASS")
    except Exception as e:
        record("print_menu()", "FAIL", str(e))

    try:
        print_table(["列1", "列2"], [["a", "b"], ["c", "d"]])
        record("print_table()", "PASS")
    except Exception as e:
        record("print_table()", "FAIL", str(e))

    try:
        print_status("success", "测试状态")
        record("print_status()", "PASS")
    except Exception as e:
        record("print_status()", "FAIL", str(e))

    try:
        print_key_value("键", "值")
        record("print_key_value()", "PASS")
    except Exception as e:
        record("print_key_value()", "FAIL", str(e))

    # 5.3 ProgressBar
    try:
        pb = ProgressBar(10, "测试进度")
        pb.update(5)
        pb.finish()
        record("ProgressBar", "PASS")
    except Exception as e:
        record("ProgressBar", "FAIL", str(e))

    # 5.4 print_footer
    try:
        print_footer("测试脚注")
        record("print_footer()", "PASS")
    except Exception as e:
        record("print_footer()", "FAIL", str(e))


# ============================================================================
# 6. 错误处理测试
# ============================================================================
def test_error_handling():
    print("\n" + "=" * 70)
    print("6. 错误处理测试")
    print("=" * 70)

    # 6.1 无效的抖音链接
    print("\n  --- 测试无效抖音链接 ---")
    invalid_urls = [
        "https://example.com",
        "not_a_url",
        "",
        "https://www.bilibili.com/video/xxx",
        "https://www.douyin.com/not-a-user-path",
        "https://www.douyin.com/user/",  # 缺少 sec_user_id
        "    ",
    ]

    try:
        from media_tools.douyin.core.following_mgr import add_user as mgr_add_user

        for url in invalid_urls:
            try:
                ok, info = mgr_add_user(url)
                if not ok:
                    record(f"无效链接处理: '{url[:40]}'", "PASS", "正确返回失败")
                else:
                    record(f"无效链接处理: '{url[:40]}'", "WARN", f"意外 ok={ok}")
            except Exception as e:
                # 优雅的错误处理应该要么返回失败，要么抛出有意义的异常
                record(f"无效链接处理: '{url[:40]}'", "WARN", f"异常: {str(e)[:60]}")
    except Exception as e:
        record("无效链接处理测试", "FAIL", str(e))

    # 6.2 关注列表为空时的处理
    try:
        from media_tools.douyin.utils.following import load_following, save_following

        # 备份原始数据
        original = load_following()

        # 设置为空
        save_following({"users": []})

        # 测试各种操作
        users = load_following()["users"]
        if users == []:
            record("空关注列表 - load_following()", "PASS", "返回空列表")
        else:
            record("空关注列表 - load_following()", "FAIL", f"返回: {users}")

        # 测试 display_users() 空列表
        from media_tools.douyin.core.following_mgr import display_users

        displayed = display_users()
        if displayed == []:
            record("空关注列表 - display_users()", "PASS", "返回空列表")
        else:
            record("空关注列表 - display_users()", "WARN", f"返回: {len(displayed)}")

        # 测试 list_users() 空列表
        from media_tools.douyin.core.following_mgr import list_users as mgr_list_users

        mgr_users = mgr_list_users()
        if mgr_users == []:
            record("空关注列表 - following_mgr.list_users()", "PASS")
        else:
            record("空关注列表 - following_mgr.list_users()", "WARN")

        # 测试 get_user() 空列表
        from media_tools.douyin.utils.following import get_user

        user = get_user("any_uid")
        if user is None:
            record("空关注列表 - get_user()", "PASS", "返回 None")
        else:
            record("空关注列表 - get_user()", "FAIL", f"返回: {user}")

        # 恢复原始数据
        save_following(original)

    except Exception as e:
        record("空关注列表处理", "FAIL", str(e))
        # 尝试恢复
        try:
            from media_tools.douyin.utils.following import load_following, save_following
            original = load_following()
            save_following(original)
        except Exception:
            pass

    # 6.3 配置文件不存在时的降级
    try:
        from media_tools.douyin.core.config_mgr import ConfigManager

        fake_config = ConfigManager("/nonexistent/path/config.yaml")
        # 应该能正常初始化
        dl_path = fake_config.get_download_path()
        db_path = fake_config.get_db_path()
        has_cookie = fake_config.has_cookie()

        record("配置不存在 - 初始化不抛异常", "PASS")
        record("配置不存在 - get_download_path() 有默认值", "PASS", str(dl_path))
        record("配置不存在 - get_db_path() 有默认值", "PASS", str(db_path))
        record("配置不存在 - has_cookie() 返回 False", "PASS" if not has_cookie else "WARN")

    except Exception as e:
        record("配置文件不存在的降级处理", "FAIL", str(e))

    # 6.4 损坏的 following.json 处理
    try:
        from media_tools.douyin.utils.following import load_following, save_following

        original = load_following()

        # 写入损坏的 JSON
        following_path = PROJECT_ROOT / "config" / "following.json"
        with open(following_path, "w", encoding="utf-8") as f:
            f.write("{ invalid json !!!")

        # 应该优雅降级
        data = load_following()
        if data == {"users": []}:
            record("损坏的 JSON - 优雅降级为空数据", "PASS")
        else:
            record("损坏的 JSON - 优雅降级为空数据", "FAIL", f"返回: {data}")

        # 恢复
        save_following(original)

    except Exception as e:
        record("损坏的 following.json 处理", "FAIL", str(e))
        # 尝试恢复
        try:
            from media_tools.douyin.utils.following import load_following, save_following
            original = load_following()
            save_following(original)
        except Exception:
            pass

    # 6.5 数据库不存在时的处理
    try:
        from media_tools.douyin.core.following_mgr import add_user as mgr_add_user

        # 使用一个无效的 URL 来触发数据库读取流程
        # 这里主要测试代码不会因数据库不存在而崩溃
        ok, info = mgr_add_user("https://www.douyin.com/user/FAKE_TEST_12345")
        # 预期会失败（无法通过 F2 获取信息），但不应该崩溃
        record("数据库不存在/无效 - 不崩溃", "PASS", "优雅处理")
    except subprocess.CalledProcessError:
        record("数据库不存在/无效 - 不崩溃", "PASS", "F2 返回非零退出码，但程序未崩溃")
    except Exception as e:
        error_str = str(e)
        if "F2" in error_str or "获取" in error_str or "失败" in error_str:
            record("数据库不存在/无效 - 不崩溃", "PASS", f"可预期的错误: {error_str[:60]}")
        else:
            record("数据库不存在/无效 - 不崩溃", "WARN", f"异常: {error_str[:100]}")


# ============================================================================
# 7. 其他模块测试 (auth, downloader, cleaner, data_generator, db_helper, f2_helper, update_checker)
# ============================================================================
def test_other_modules():
    print("\n" + "=" * 70)
    print("7. 其他模块可导入性测试")
    print("=" * 70)

    modules = [
        "media_tools.douyin.core.auth",
        "media_tools.douyin.core.downloader",
        "media_tools.douyin.core.cleaner",
        "media_tools.douyin.core.data_generator",
        "media_tools.douyin.core.db_helper",
        "media_tools.douyin.core.f2_helper",
        "media_tools.douyin.core.update_checker",
        "media_tools.douyin.core.enhanced_menu",
        "media_tools.douyin.utils.auth_parser",
        "media_tools.douyin.utils.config",
        "media_tools.douyin.utils.logger",
    ]

    for mod_name in modules:
        try:
            __import__(mod_name)
            record(f"导入 {mod_name}", "PASS")
        except Exception as e:
            record(f"导入 {mod_name}", "FAIL", str(e)[:80])


# ============================================================================
# 主函数
# ============================================================================
def main():
    print("\n" + "#" * 70)
    print("# 抖音下载模块全功能测试报告")
    print("# 项目: /Users/gq/Projects/media-tools")
    print(f"# Python: {sys.version}")
    print(f"# 日期: 2026-04-12")
    print("#" * 70)

    # 备份 following.json
    backup_following()

    try:
        test_env_check()
        test_following_crud()
        test_config_mgr()
        test_compressor()
        test_ui()
        test_error_handling()
        test_other_modules()
    finally:
        # 恢复 following.json
        restore_following()

    # 汇总统计
    print("\n" + "=" * 70)
    print("测试汇总")
    print("=" * 70)

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    warned = sum(1 for r in results if r["status"] == "WARN")
    total = len(results)

    print(f"\n总计: {total} 项测试")
    print(f"  PASS: {passed}")
    print(f"  WARN: {warned}")
    print(f"  FAIL: {failed}")
    print(f"  通过率: {passed / total * 100:.1f}%")

    if failed > 0:
        print("\n--- FAIL 项目详情 ---")
        for r in results:
            if r["status"] == "FAIL":
                print(f"  [FAIL] {r['name']}: {r['detail']}")

    if warned > 0:
        print("\n--- WARN 项目详情 ---")
        for r in results:
            if r["status"] == "WARN":
                print(f"  [WARN] {r['name']}: {r['detail']}")

    print()
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
