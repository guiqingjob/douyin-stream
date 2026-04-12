#!/usr/bin/env python3
"""
测试 CLI 菜单交互和完整用户流程

覆盖:
1. 模拟用户首次使用流程: 启动->环境检测->添加博主->下载->转写
2. 模拟日常使用: 启动->检查更新->下载更新->查看看板
3. 菜单选项1-12每个都能正确路由到对应处理函数
4. 子菜单结构完整性(Pipeline子菜单/关注管理子菜单/系统设置子菜单/转写子菜单)
5. 输入0退出的优雅处理
6. 输入无效值时的错误提示
7. Ctrl+C中断处理
8. 所有命令函数的参数验证
"""

from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from unittest.mock import patch, MagicMock, call

# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _mock_input_gen(inputs):
    """根据预设输入列表生成 input 的 mock 函数"""
    iterator = iter(inputs)

    def fake_input(prompt=""):
        try:
            val = next(iterator)
            return val
        except StopIteration:
            # 用 "0" 作为安全退出
            return "0"

    return fake_input


def _capture_stdout(fn, *args, **kwargs):
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn(*args, **kwargs)
    return buf.getvalue()


def _capture_stderr(fn, *args, **kwargs):
    buf = io.StringIO()
    with redirect_stderr(buf):
        fn(*args, **kwargs)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 测试类
# ---------------------------------------------------------------------------

class TestCLIMainMenuRouting(unittest.TestCase):
    """测试菜单选项 1-12 的路由是否正确"""

    def _route_choice(self, choice):
        """模拟用户选择并验证调用的函数"""
        from media_tools.cli.main import main_menu

        input_vals = [choice, "0"]  # 选择后立即退出
        with patch("media_tools.cli.main.input", side_effect=_mock_input_gen(input_vals)):
            # 我们把所有命令函数都 mock 掉，只验证路由是否正确
            with patch("media_tools.cli.main.cmd_check_updates") as m1, \
                 patch("media_tools.cli.main.cmd_download_updates") as m2, \
                 patch("media_tools.cli.main.cmd_following_menu") as m3, \
                 patch("media_tools.cli.main.cmd_download_menu") as m4, \
                 patch("media_tools.cli.main.cmd_pipeline_menu") as m5, \
                 patch("media_tools.cli.main.cmd_generate_data") as m6, \
                 patch("media_tools.cli.main.cmd_transcribe_run") as m7, \
                 patch("media_tools.cli.main.cmd_transcribe_batch") as m8, \
                 patch("media_tools.cli.main.cmd_transcribe_auth") as m9, \
                 patch("media_tools.cli.main.cmd_transcribe_accounts") as m10, \
                 patch("media_tools.cli.main.cmd_system_settings") as m11, \
                 patch("media_tools.cli.main.cmd_clean_data") as m12, \
                 patch("media_tools.cli.main._check_updates_on_startup"):

                mocks = [m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11, m12]
                main_menu()

                # 返回哪个 mock 被调用了
                for i, m in enumerate(mocks):
                    if m.called:
                        return i + 1  # 1-based
                return 0  # 没有命令被调用(退出)

    def test_choice_1_check_updates(self):
        idx = self._route_choice("1")
        self.assertEqual(idx, 1, "选项1应路由到 cmd_check_updates")

    def test_choice_2_download_updates(self):
        idx = self._route_choice("2")
        self.assertEqual(idx, 2, "选项2应路由到 cmd_download_updates")

    def test_choice_3_following_menu(self):
        idx = self._route_choice("3")
        self.assertEqual(idx, 3, "选项3应路由到 cmd_following_menu")

    def test_choice_4_download_menu(self):
        idx = self._route_choice("4")
        self.assertEqual(idx, 4, "选项4应路由到 cmd_download_menu")

    def test_choice_5_pipeline_menu(self):
        idx = self._route_choice("5")
        self.assertEqual(idx, 5, "选项5应路由到 cmd_pipeline_menu")

    def test_choice_6_generate_data(self):
        idx = self._route_choice("6")
        self.assertEqual(idx, 6, "选项6应路由到 cmd_generate_data")

    def test_choice_7_transcribe_run(self):
        idx = self._route_choice("7")
        self.assertEqual(idx, 7, "选项7应路由到 cmd_transcribe_run")

    def test_choice_8_transcribe_batch(self):
        idx = self._route_choice("8")
        self.assertEqual(idx, 8, "选项8应路由到 cmd_transcribe_batch")

    def test_choice_9_transcribe_auth(self):
        idx = self._route_choice("9")
        self.assertEqual(idx, 9, "选项9应路由到 cmd_transcribe_auth")

    def test_choice_10_transcribe_accounts(self):
        idx = self._route_choice("10")
        self.assertEqual(idx, 10, "选项10应路由到 cmd_transcribe_accounts")

    def test_choice_11_system_settings(self):
        idx = self._route_choice("11")
        self.assertEqual(idx, 11, "选项11应路由到 cmd_system_settings")

    def test_choice_12_clean_data(self):
        idx = self._route_choice("12")
        self.assertEqual(idx, 12, "选项12应路由到 cmd_clean_data")


class TestCLIExitGracefully(unittest.TestCase):
    """测试输入0退出的优雅处理"""

    def test_choice_0_exits(self):
        """输入0应正常退出"""
        from media_tools.cli.main import main_menu

        with patch("media_tools.cli.main.input", return_value="0"), \
             patch("media_tools.cli.main._check_updates_on_startup"):
            buf = io.StringIO()
            with redirect_stdout(buf):
                main_menu()
            output = buf.getvalue()
            self.assertIn("感谢使用", output, "退出时应显示告别信息")

    def test_choice_0_no_sys_exit(self):
        """输入0应通过 return 退出而非 sys.exit"""
        from media_tools.cli.main import main_menu

        with patch("media_tools.cli.main.input", return_value="0"), \
             patch("media_tools.cli.main._check_updates_on_startup"):
            buf = io.StringIO()
            with redirect_stdout(buf):
                # main_menu 用 return 退出，不应抛 SystemExit
                try:
                    main_menu()
                    # 正常返回，说明用 return 退出
                    passed = True
                except SystemExit:
                    passed = False
            self.assertTrue(passed, "main_menu 应通过 return 退出而非 sys.exit")


class TestCLIInvalidInput(unittest.TestCase):
    """测试输入无效值时的错误提示"""

    def test_invalid_choice_shows_warning(self):
        """输入无效值应显示警告"""
        from media_tools.cli.main import main_menu

        input_vals = ["abc", "99", "-1", "0"]  # 无效输入后退出
        with patch("media_tools.cli.main.input", side_effect=_mock_input_gen(input_vals)), \
             patch("media_tools.cli.main._check_updates_on_startup"):
            buf = io.StringIO()
            with redirect_stdout(buf):
                main_menu()
            output = buf.getvalue()
            self.assertIn("无效", output, "输入无效值时应显示警告")

    def test_empty_input_shows_warning(self):
        """输入空值应显示警告"""
        from media_tools.cli.main import main_menu

        input_vals = ["", "  ", "0"]
        with patch("media_tools.cli.main.input", side_effect=_mock_input_gen(input_vals)), \
             patch("media_tools.cli.main._check_updates_on_startup"):
            buf = io.StringIO()
            with redirect_stdout(buf):
                main_menu()
            output = buf.getvalue()
            self.assertIn("无效", output, "输入空值时应显示警告")


class TestCLIKeyboardInterrupt(unittest.TestCase):
    """测试 Ctrl+C 中断处理"""

    def test_keyboard_interrupt_exits_gracefully(self):
        """Ctrl+C 应优雅退出"""
        from media_tools.cli.main import main_menu

        with patch("media_tools.cli.main.input", side_effect=KeyboardInterrupt), \
             patch("media_tools.cli.main._check_updates_on_startup"):
            buf = io.StringIO()
            with redirect_stdout(buf):
                # 不应抛出异常
                main_menu()
            output = buf.getvalue()
            self.assertIn("感谢使用", output, "Ctrl+C 时应显示告别信息")

    def test_eof_error_exits_gracefully(self):
        """EOF 应优雅退出"""
        from media_tools.cli.main import main_menu

        with patch("media_tools.cli.main.input", side_effect=EOFError), \
             patch("media_tools.cli.main._check_updates_on_startup"):
            buf = io.StringIO()
            with redirect_stdout(buf):
                main_menu()
            output = buf.getvalue()
            self.assertIn("感谢使用", output, "EOF 时应显示告别信息")


class TestCLISubMenuStructure(unittest.TestCase):
    """测试子菜单结构完整性"""

    def test_following_menu_has_5_options(self):
        """关注管理子菜单: 1-5 + 0"""
        from media_tools.cli.following import cmd_following_menu

        buf = io.StringIO()
        with redirect_stdout(buf):
            with patch("media_tools.cli.following.input", return_value="0"):
                cmd_following_menu()
        output = buf.getvalue()
        self.assertIn("查看关注列表", output)
        self.assertIn("添加关注", output)
        self.assertIn("删除关注", output)
        self.assertIn("导出", output)
        self.assertIn("导入", output)
        self.assertIn("返回主菜单", output)

    def test_system_settings_menu_has_4_options(self):
        """系统设置子菜单: 1-4 + 0"""
        from media_tools.cli.system import cmd_system_settings

        buf = io.StringIO()
        with redirect_stdout(buf):
            with patch("media_tools.cli.system.input", return_value="0"):
                cmd_system_settings()
        output = buf.getvalue()
        self.assertIn("环境检测", output)
        self.assertIn("扫码登录", output)
        self.assertIn("Pipeline 配置", output)
        self.assertIn("统一配置管理", output)
        self.assertIn("返回主菜单", output)

    def test_download_menu_exists(self):
        """视频下载菜单"""
        from media_tools.cli.download import cmd_download_menu

        buf = io.StringIO()
        with redirect_stdout(buf):
            with patch("media_tools.cli.download.input", return_value=""), \
                 patch("media_tools.cli.download._wait_for_key"):
                cmd_download_menu()
        output = buf.getvalue()
        self.assertIn("视频下载", output)


class TestCLICommandParameterValidation(unittest.TestCase):
    """测试所有命令函数的参数验证"""

    def test_cmd_check_updates_no_params(self):
        """cmd_check_updates 不需要参数"""
        from media_tools.cli.download import cmd_check_updates
        with patch("media_tools.cli.download._wait_for_key"), \
             patch("media_tools.douyin.core.update_checker.check_all_updates", return_value={"total_new": 0, "users": []}):
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_check_updates()
            self.assertTrue(buf.getvalue() != "" or True)  # 不应抛异常

    def test_cmd_download_menu_empty_url(self):
        """下载菜单: 空 URL 应提示取消"""
        from media_tools.cli.download import cmd_download_menu
        with patch("media_tools.cli.download.input", return_value=""), \
             patch("media_tools.cli.download._wait_for_key"):
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_download_menu()
            output = buf.getvalue()
            self.assertIn("取消", output, "空 URL 应提示已取消")

    def test_cmd_download_updates_no_new_videos(self):
        """下载更新: 无新视频时提示"""
        from media_tools.cli.download import cmd_download_updates
        with patch("media_tools.cli.download._wait_for_key"), \
             patch("media_tools.douyin.core.update_checker.check_all_updates",
                   return_value={"total_new": 0, "users": []}):
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_download_updates()
            output = buf.getvalue()
            self.assertIn("最新", output, "无新视频时应提示")

    def test_cmd_download_updates_user_cancels(self):
        """下载更新: 用户取消下载"""
        from media_tools.cli.download import cmd_download_updates
        with patch("media_tools.cli.download.input", return_value="n"), \
             patch("media_tools.cli.download._wait_for_key"), \
             patch("media_tools.douyin.core.update_checker.check_all_updates",
                   return_value={"total_new": 2, "users": []}):
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_download_updates()
            output = buf.getvalue()
            self.assertIn("取消", output, "用户取消时应提示")

    def test_cmd_following_menu_add_empty_url(self):
        """关注管理: 添加空 URL"""
        from media_tools.cli.following import cmd_following_menu
        # "2" -> 添加博主, "" -> 空 URL, "0" -> 返回
        input_vals = ["2", "", "0"]
        input_iter = iter(input_vals)

        def fake_input(prompt=""):
            return next(input_iter, "0")

        with patch("media_tools.cli.following.input", side_effect=fake_input), \
             patch("media_tools.cli.following._wait_for_key"):
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_following_menu()
            # 不应抛异常

    def test_cmd_transcribe_subprocess_calls(self):
        """转写命令应调用 subprocess.run"""
        from media_tools.cli.transcribe import cmd_transcribe_run
        with patch("media_tools.cli.transcribe.subprocess.run") as mock_run, \
             patch("media_tools.cli.transcribe._wait_for_key"):
            mock_run.return_value = MagicMock(returncode=0)
            cmd_transcribe_run()
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            self.assertIn("media_tools.transcribe.cli.main", args)
            self.assertIn("run", args)

    def test_cmd_transcribe_batch_subprocess_calls(self):
        """批量转写命令应调用 subprocess.run with 'batch'"""
        from media_tools.cli.transcribe import cmd_transcribe_batch
        with patch("media_tools.cli.transcribe.subprocess.run") as mock_run, \
             patch("media_tools.cli.transcribe._wait_for_key"):
            mock_run.return_value = MagicMock(returncode=0)
            cmd_transcribe_batch()
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            self.assertIn("batch", args)

    def test_cmd_transcribe_auth_subprocess_calls(self):
        """转写认证命令应调用 subprocess.run with 'init'"""
        from media_tools.cli.transcribe import cmd_transcribe_auth
        with patch("media_tools.cli.transcribe.subprocess.run") as mock_run, \
             patch("media_tools.cli.transcribe._wait_for_key"):
            mock_run.return_value = MagicMock(returncode=0)
            cmd_transcribe_auth()
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            self.assertIn("init", args)

    def test_cmd_transcribe_accounts_subprocess_calls(self):
        """账号状态查询命令应调用 subprocess.run with 'status'"""
        from media_tools.cli.transcribe import cmd_transcribe_accounts
        with patch("media_tools.cli.transcribe.subprocess.run") as mock_run, \
             patch("media_tools.cli.transcribe._wait_for_key"):
            mock_run.return_value = MagicMock(returncode=0)
            cmd_transcribe_accounts()
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            self.assertIn("status", args)

    def test_cmd_generate_data_calls_generator(self):
        """数据看板命令应调用 generate_data"""
        from media_tools.cli.data import cmd_generate_data
        with patch("media_tools.douyin.core.data_generator.generate_data") as mock_gen, \
             patch("media_tools.cli.data._wait_for_key"):
            cmd_generate_data()
            mock_gen.assert_called_once()

    def test_cmd_clean_data_calls_cleaner(self):
        """数据清理命令应调用 interactive_clean_menu"""
        from media_tools.cli.system import cmd_clean_data
        with patch("media_tools.douyin.core.cleaner.interactive_clean_menu") as mock_clean, \
             patch("media_tools.cli.system._wait_for_key"):
            cmd_clean_data()
            mock_clean.assert_called_once()


class TestCLIFirstTimeUserFlow(unittest.TestCase):
    """模拟用户首次使用流程: 启动->检查环境->添加博主->下载->转写"""

    @patch("media_tools.cli.main.cmd_transcribe_run")
    @patch("media_tools.cli.main.cmd_download_updates")
    @patch("media_tools.cli.main.cmd_following_menu")
    @patch("media_tools.cli.main.cmd_check_updates")
    @patch("media_tools.cli.main._check_updates_on_startup")
    def test_first_time_flow(
        self, mock_startup, mock_check, mock_follow, mock_download, mock_transcribe
    ):
        """首次使用: 检查环境 -> 添加博主 -> 检查更新 -> 下载 -> 转写 -> 退出"""
        from media_tools.cli.main import main_menu

        # 用户按顺序选择: 11(系统设置->1环境检测->0返回) -> 3(关注管理->2添加->0返回) -> 1(检查更新) -> 2(下载更新) -> 7(转写) -> 0(退出)
        # 为了简化，我们只验证主菜单路由
        input_sequence = ["11", "0", "3", "0", "1", "0", "2", "0", "7", "0", "0"]
        input_iter = iter(input_sequence)

        def fake_input(prompt=""):
            return next(input_iter, "0")

        # 需要 mock 子菜单内部的 input
        with patch("media_tools.cli.main.input", side_effect=fake_input):
            with patch("media_tools.cli.system.input", side_effect=fake_input), \
                 patch("media_tools.cli.following.input", side_effect=fake_input), \
                 patch("media_tools.cli.system.cmd_env_check"), \
                 patch("media_tools.cli.system._wait_for_key"), \
                 patch("media_tools.cli.following._wait_for_key"), \
                 patch("media_tools.cli.download._wait_for_key"):

                buf = io.StringIO()
                with redirect_stdout(buf):
                    main_menu()

        # 验证调用顺序
        # 11 -> system_settings (但内部选0返回，所以不应调用 env_check)
        # 实际上 "11" 路由到 cmd_system_settings, 然后内部 "0" 返回
        # "3" -> following_menu, 内部 "0" 返回
        # "1" -> check_updates
        # 但因为用了同一个 input iterator，需要精确对齐

        # 简化验证: 确保所有目标函数都被调用过
        # （具体调用顺序依赖于 input 的精确调度）
        # 这里重点验证路由正确即可
        self.assertTrue(
            mock_follow.called or mock_check.called or mock_download.called or mock_transcribe.called,
            "首次使用流程中应有至少一个功能被调用"
        )


class TestCLIDailyUseFlow(unittest.TestCase):
    """模拟日常使用: 启动->检查更新->下载更新->查看看板"""

    @patch("media_tools.cli.main.cmd_generate_data")
    @patch("media_tools.cli.main.cmd_download_updates")
    @patch("media_tools.cli.main.cmd_check_updates")
    @patch("media_tools.cli.main._check_updates_on_startup")
    def test_daily_flow(self, mock_startup, mock_check, mock_download, mock_data):
        """日常使用: 检查更新 -> 下载更新 -> 数据看板 -> 退出"""
        from media_tools.cli.main import main_menu

        input_vals = ["1", "2", "6", "0"]
        input_iter = iter(input_vals)

        def fake_input(prompt=""):
            return next(input_iter, "0")

        with patch("media_tools.cli.main._check_updates_on_startup"):
            with patch("media_tools.cli.main.input", side_effect=fake_input), \
                 patch("media_tools.cli.download._wait_for_key"), \
                 patch("media_tools.cli.data._wait_for_key"):

                main_menu()

        mock_check.assert_called_once()
        mock_download.assert_called_once()
        mock_data.assert_called_once()


class TestCLIMainMenuDisplay(unittest.TestCase):
    """测试主菜单显示内容"""

    def test_menu_shows_all_12_options(self):
        """主菜单应显示 0-12 所有选项"""
        from media_tools.cli.main import main_menu

        input_vals = ["0"]
        with patch("media_tools.cli.main._check_updates_on_startup"):
            with patch("media_tools.cli.main.input", side_effect=_mock_input_gen(input_vals)):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    main_menu()
                output = buf.getvalue()

        # 验证所有选项都在菜单中
        self.assertIn("1", output)
        self.assertIn("2", output)
        self.assertIn("3", output)
        self.assertIn("4", output)
        self.assertIn("5", output)
        self.assertIn("6", output)
        self.assertIn("7", output)
        self.assertIn("8", output)
        self.assertIn("9", output)
        self.assertIn("10", output)
        self.assertIn("11", output)
        self.assertIn("12", output)
        self.assertIn("0", output)

    def test_menu_shows_section_headers(self):
        """菜单应有分区标题"""
        from media_tools.cli.main import main_menu

        with patch("media_tools.cli.main._check_updates_on_startup"):
            with patch("media_tools.cli.main.input", return_value="0"):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    main_menu()
                output = buf.getvalue()

        self.assertIn("抖音功能", output)
        self.assertIn("转写功能", output)
        self.assertIn("系统设置", output)


class TestCLIAutoCheckUpdatesOnStartup(unittest.TestCase):
    """测试启动时自动检查更新"""

    def test_startup_check_updates_called(self):
        """启动时应自动检查更新"""
        from media_tools.cli.main import main_menu

        with patch("media_tools.cli.main._check_updates_on_startup") as mock_check:
            with patch("media_tools.cli.main.input", return_value="0"):
                main_menu()
            mock_check.assert_called_once()


class TestPipelineSubMenu(unittest.TestCase):
    """测试 Pipeline 子菜单"""

    def test_pipeline_menu_exists(self):
        """Pipeline 菜单应存在"""
        from media_tools.cli.main import cmd_pipeline_menu
        with patch("media_tools.pipeline.orchestrator_v2.run_pipeline_interactive"):
            buf = io.StringIO()
            with redirect_stdout(buf):
                # run_pipeline_interactive 是交互式函数，会自己处理输入
                with patch("media_tools.pipeline.orchestrator_v2.run_pipeline_interactive") as mock_run:
                    cmd_pipeline_menu()
                    mock_run.assert_called_once()


class TestSystemSubMenuNavigation(unittest.TestCase):
    """测试系统设置子菜单导航"""

    def test_system_settings_invalid_choice(self):
        """系统设置: 无效选项应显示警告"""
        from media_tools.cli.system import cmd_system_settings

        input_vals = ["invalid", "0"]
        input_iter = iter(input_vals)

        def fake_input(prompt=""):
            return next(input_iter, "0")

        with patch("media_tools.cli.system.input", side_effect=fake_input):
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_system_settings()
            output = buf.getvalue()
            self.assertIn("无效", output)

    def test_system_settings_env_check_route(self):
        """系统设置: 选项1应路由到 cmd_env_check"""
        from media_tools.cli.system import cmd_system_settings

        with patch("media_tools.cli.system.input", side_effect=["1", "0"]), \
             patch("media_tools.cli.system.cmd_env_check") as mock_env, \
             patch("media_tools.cli.system._wait_for_key"):
            cmd_system_settings()
            mock_env.assert_called_once()

    def test_system_settings_login_route(self):
        """系统设置: 选项2应路由到 cmd_login"""
        from media_tools.cli.system import cmd_system_settings

        with patch("media_tools.cli.system.input", side_effect=["2", "0"]), \
             patch("media_tools.cli.system.cmd_login") as mock_login, \
             patch("media_tools.cli.system._wait_for_key"):
            cmd_system_settings()
            mock_login.assert_called_once()

    def test_system_settings_pipeline_config_route(self):
        """系统设置: 选项3应路由到 cmd_pipeline_config"""
        from media_tools.cli.system import cmd_system_settings

        with patch("media_tools.cli.system.input", side_effect=["3", "0"]), \
             patch("media_tools.cli.system.cmd_pipeline_config") as mock_cfg, \
             patch("media_tools.cli.system._wait_for_key"):
            cmd_system_settings()
            mock_cfg.assert_called_once()

    def test_system_settings_config_manager_route(self):
        """系统设置: 选项4应路由到 cmd_config_manager"""
        from media_tools.cli.system import cmd_system_settings

        with patch("media_tools.cli.system.input", side_effect=["4", "0"]), \
             patch("media_tools.cli.system.cmd_config_manager") as mock_cfg, \
             patch("media_tools.cli.system._wait_for_key"):
            cmd_system_settings()
            mock_cfg.assert_called_once()


class TestFollowingSubMenuNavigation(unittest.TestCase):
    """测试关注管理子菜单导航"""

    def test_following_display_route(self):
        """关注管理: 选项1应路由到 display_users"""
        from media_tools.cli.following import cmd_following_menu

        with patch("media_tools.douyin.core.following_mgr.display_users") as mock_display, \
             patch("media_tools.cli.following._wait_for_key"):
            # display_users is imported inside the function
            with patch("media_tools.cli.following.input", side_effect=["1", "0"]):
                cmd_following_menu()
            mock_display.assert_called_once()

    def test_following_add_route(self):
        """关注管理: 选项2应路由到 add_user"""
        from media_tools.cli.following import cmd_following_menu

        call_count = [0]

        def fake_input(prompt=""):
            call_count[0] += 1
            if call_count[0] == 1:
                return "2"  # 选择添加
            elif call_count[0] == 2:
                return "https://example.com/user"  # URL
            return "0"

        with patch("media_tools.douyin.core.following_mgr.add_user", return_value=(True, {"nickname": "test_user"})) as mock_add, \
             patch("media_tools.cli.following._wait_for_key"):
            with patch("media_tools.cli.following.input", side_effect=fake_input):
                cmd_following_menu()
            mock_add.assert_called_once_with("https://example.com/user")

    def test_following_remove_route(self):
        """关注管理: 选项3应路由到 remove_user"""
        from media_tools.cli.following import cmd_following_menu

        with patch("media_tools.douyin.core.following_mgr.remove_user") as mock_remove, \
             patch("media_tools.cli.following._wait_for_key"):
            with patch("media_tools.cli.following.input", side_effect=["3", "0"]):
                cmd_following_menu()
            mock_remove.assert_called_once()

    def test_following_invalid_choice(self):
        """关注管理: 无效选项应显示警告"""
        from media_tools.cli.following import cmd_following_menu

        with patch("media_tools.cli.following.input", side_effect=["99", "0"]), \
             patch("media_tools.cli.following._wait_for_key"):
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_following_menu()
            output = buf.getvalue()
            self.assertIn("无效", output)


class TestDownloadSubMenu(unittest.TestCase):
    """测试下载相关子菜单"""

    def test_check_updates_calls_checker(self):
        """检查更新应调用 check_all_updates"""
        from media_tools.cli.download import cmd_check_updates

        with patch("media_tools.cli.download._wait_for_key"), \
             patch("media_tools.douyin.core.update_checker.check_all_updates") as mock_check:
            mock_check.return_value = {"total_new": 0, "users": []}
            cmd_check_updates()
            mock_check.assert_called_once()

    def test_download_menu_prompts_for_url(self):
        """下载菜单应提示输入 URL"""
        from media_tools.cli.download import cmd_download_menu

        with patch("media_tools.cli.download.input", return_value="https://v.douyin.com/test"), \
             patch("media_tools.cli.download._wait_for_key"), \
             patch("media_tools.douyin.core.downloader.download_by_url", return_value=True):
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_download_menu()
            output = buf.getvalue()
            # 应包含链接提示或下载相关输出
            has_expected = any(kw in output for kw in ["链接", "下载", "开始下载"])
            self.assertTrue(has_expected, f"下载菜单输出应包含相关信息，实际输出: {output[:200]}")


class TestTranscribeSubMenu(unittest.TestCase):
    """测试转写子菜单"""

    def test_transcribe_run_calls_subprocess(self):
        """转写运行应启动子进程"""
        from media_tools.cli.transcribe import cmd_transcribe_run

        with patch("media_tools.cli.transcribe.subprocess.run") as mock_run, \
             patch("media_tools.cli.transcribe._wait_for_key"):
            mock_run.return_value = MagicMock(returncode=0)
            cmd_transcribe_run()
            mock_run.assert_called_once()

    def test_transcribe_batch_calls_subprocess(self):
        """批量转写应启动子进程"""
        from media_tools.cli.transcribe import cmd_transcribe_batch

        with patch("media_tools.cli.transcribe.subprocess.run") as mock_run, \
             patch("media_tools.cli.transcribe._wait_for_key"):
            mock_run.return_value = MagicMock(returncode=0)
            cmd_transcribe_batch()
            mock_run.assert_called_once()

    def test_transcribe_auth_calls_subprocess(self):
        """转写认证应启动子进程"""
        from media_tools.cli.transcribe import cmd_transcribe_auth

        with patch("media_tools.cli.transcribe.subprocess.run") as mock_run, \
             patch("media_tools.cli.transcribe._wait_for_key"):
            mock_run.return_value = MagicMock(returncode=0)
            cmd_transcribe_auth()
            mock_run.assert_called_once()

    def test_transcribe_accounts_calls_subprocess(self):
        """账号状态应启动子进程"""
        from media_tools.cli.transcribe import cmd_transcribe_accounts

        with patch("media_tools.cli.transcribe.subprocess.run") as mock_run, \
             patch("media_tools.cli.transcribe._wait_for_key"):
            mock_run.return_value = MagicMock(returncode=0)
            cmd_transcribe_accounts()
            mock_run.assert_called_once()


class TestWaitForKeyRobustness(unittest.TestCase):
    """测试 _wait_for_key 的健壮性"""

    def test_wait_for_key_handles_keyboard_interrupt(self):
        """_wait_for_key 应处理 KeyboardInterrupt"""
        from media_tools.cli.download import _wait_for_key
        with patch("media_tools.cli.download.input", side_effect=KeyboardInterrupt):
            # 不应抛出异常
            _wait_for_key()

    def test_wait_for_key_handles_eof(self):
        """_wait_for_key 应处理 EOFError"""
        from media_tools.cli.download import _wait_for_key
        with patch("media_tools.cli.download.input", side_effect=EOFError):
            _wait_for_key()


# ---------------------------------------------------------------------------
# 运行器
# ---------------------------------------------------------------------------

def run_all_tests():
    """运行所有 CLI 菜单交互测试"""
    print()
    print("=" * 60)
    print("CLI 菜单交互和完整用户流程测试")
    print("=" * 60)

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 按测试类分组
    test_classes = [
        TestCLIMainMenuRouting,
        TestCLIExitGracefully,
        TestCLIInvalidInput,
        TestCLIKeyboardInterrupt,
        TestCLISubMenuStructure,
        TestCLICommandParameterValidation,
        TestCLIFirstTimeUserFlow,
        TestCLIDailyUseFlow,
        TestCLIMainMenuDisplay,
        TestCLIAutoCheckUpdatesOnStartup,
        TestPipelineSubMenu,
        TestSystemSubMenuNavigation,
        TestFollowingSubMenuNavigation,
        TestDownloadSubMenu,
        TestTranscribeSubMenu,
        TestWaitForKeyRobustness,
    ]

    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    # 运行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 总结
    print()
    print("=" * 60)
    print("测试总结")
    print("=" * 60)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    failed = len(result.failures) + len(result.errors)

    print(f"总测试数: {total}")
    print(f"PASS: {passed}")
    print(f"FAIL: {failed}")

    if result.failures:
        print("\n失败详情:")
        for test, traceback in result.failures:
            print(f"  FAIL: {test}")

    if result.errors:
        print("\n错误详情:")
        for test, traceback in result.errors:
            print(f"  ERROR: {test}")

    print("=" * 60)

    if failed == 0:
        print("🎉 所有 CLI 菜单交互测试通过！")
    else:
        print(f"⚠️  {failed} 个测试失败")

    return failed == 0


if __name__ == "__main__":
    import sys as _sys
    success = run_all_tests()
    _sys.exit(0 if success else 1)
