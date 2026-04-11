"""测试CLI交互界面完整功能"""
from __future__ import annotations

import sys
import io
import asyncio
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch, MagicMock

from media_tools.transcribe.cli.interactive_menu import (
    build_main_menu,
    build_group_menu,
    execute_direct_command,
    execute_sub_command,
)
from media_tools.transcribe.cli.main import DIRECT_COMMANDS, GROUP_COMMANDS


def test_main_menu_structure():
    """测试主菜单结构"""
    print("\n" + "=" * 60)
    print("测试 1: 主菜单结构")
    print("=" * 60)
    
    items = build_main_menu()
    expected_count = len(DIRECT_COMMANDS) + len(GROUP_COMMANDS) + 1
    assert len(items) == expected_count, f"菜单项数量不匹配: 期望 {expected_count}, 实际 {len(items)}"
    print(f"✅ 菜单项数量正确: {len(items)} 个")
    
    direct_items = [item for item in items if item.action.startswith("direct:")]
    assert len(direct_items) == len(DIRECT_COMMANDS), "直接命令数量不匹配"
    print(f"✅ 所有直接命令都在菜单中: {len(direct_items)} 个")
    
    group_items = [item for item in items if item.action.startswith("group:")]
    assert len(group_items) == len(GROUP_COMMANDS), "命令组数量不匹配"
    print(f"✅ 所有命令组都在菜单中: {len(group_items)} 个")
    
    exit_items = [item for item in items if item.action == "exit"]
    assert len(exit_items) == 1, "应该有且只有一个退出按钮"
    print(f"✅ 退出按钮存在")


def test_group_menu_structure():
    """测试子菜单结构"""
    print("\n" + "=" * 60)
    print("测试 2: 子菜单结构")
    print("=" * 60)
    
    for group_name in GROUP_COMMANDS:
        items = build_group_menu(group_name)
        _, subcommands = GROUP_COMMANDS[group_name]
        expected_count = len(subcommands) + 1
        assert len(items) == expected_count, f"{group_name} 子菜单项数量不匹配"
        print(f"✅ {group_name} 子菜单项数量正确: {len(items)} 个")
        
        sub_items = [item for item in items if item.action.startswith("sub:")]
        for sub_name in subcommands:
            actions = [item.action for item in sub_items]
            expected_action = f"sub:{group_name}:{sub_name}"
            assert expected_action in actions, f"{group_name} 的子命令 {sub_name} 未找到"
        print(f"✅ {group_name} 的所有子命令都在菜单中")
        
        back_items = [item for item in items if item.action == "back"]
        assert len(back_items) == 1, f"{group_name} 应该有返回按钮"
        print(f"✅ {group_name} 有返回按钮")


def test_menu_item_attributes():
    """测试菜单项属性"""
    print("\n" + "=" * 60)
    print("测试 3: 菜单项属性")
    print("=" * 60)
    
    items = build_main_menu()
    for item in items:
        assert item.title and len(item.title.strip()) > 0, f"菜单项 title 无效: {item}"
        assert item.description and len(item.description.strip()) > 0, f"菜单项 description 无效: {item}"
        assert item.action and len(item.action.strip()) > 0, f"菜单项 action 无效: {item}"
        assert item.icon and len(item.icon.strip()) > 0, f"菜单项 icon 无效: {item}"
    
    print(f"✅ 所有 {len(items)} 个菜单项的属性都正确")


def test_direct_command_execution():
    """测试直接命令执行"""
    print("\n" + "=" * 60)
    print("测试 4: 直接命令执行（错误处理）")
    print("=" * 60)
    
    buffer = io.StringIO()
    with redirect_stderr(buffer):
        exit_code = execute_direct_command("unknown_command", [])
    
    assert exit_code == 2, f"未知命令应返回错误码 2, 实际返回 {exit_code}"
    assert "unknown command" in buffer.getvalue().lower(), "应显示错误信息"
    print(f"✅ 未知命令正确返回错误码: {exit_code}")


def test_sub_command_execution():
    """测试子命令执行"""
    print("\n" + "=" * 60)
    print("测试 5: 子命令执行（错误处理）")
    print("=" * 60)
    
    buffer = io.StringIO()
    with redirect_stderr(buffer):
        exit_code = execute_sub_command("unknown_group", "sub1", [])
    assert exit_code == 2, f"未知组应返回错误码 2, 实际返回 {exit_code}"
    print(f"✅ 未知组正确返回错误码: {exit_code}")
    
    buffer = io.StringIO()
    with redirect_stderr(buffer):
        exit_code = execute_sub_command("quota", "unknown_sub", [])
    assert exit_code == 2, f"未知子命令应返回错误码 2, 实际返回 {exit_code}"
    print(f"✅ 未知子命令正确返回错误码: {exit_code}")


def test_all_commands_in_menu():
    """测试所有命令都能在菜单中找到"""
    print("\n" + "=" * 60)
    print("测试 6: 命令与菜单一致性检查")
    print("=" * 60)
    
    items = build_main_menu()
    menu_commands = {item.action.split(":", 1)[1] for item in items if item.action.startswith("direct:")}
    
    for cmd in DIRECT_COMMANDS:
        assert cmd in menu_commands, f"命令 {cmd} 在 DIRECT_COMMANDS 中但不在菜单中"
    for cmd in menu_commands:
        assert cmd in DIRECT_COMMANDS, f"命令 {cmd} 在菜单中但不在 DIRECT_COMMANDS 中"
    print(f"✅ 所有直接命令一致: {len(menu_commands)} 个")
    
    menu_groups = {item.action.split(":", 1)[1] for item in items if item.action.startswith("group:")}
    for group in GROUP_COMMANDS:
        assert group in menu_groups, f"命令组 {group} 在 GROUP_COMMANDS 中但不在菜单中"
    for group in menu_groups:
        assert group in GROUP_COMMANDS, f"命令组 {group} 在菜单中但不在 GROUP_COMMANDS 中"
    print(f"✅ 所有命令组一致: {len(menu_groups)} 个")
    
    for group_name in GROUP_COMMANDS:
        _, subcommands = GROUP_COMMANDS[group_name]
        group_items = build_group_menu(group_name)
        menu_subcommands = {item.action.split(":")[2] for item in group_items if item.action.startswith("sub:")}
        for sub in subcommands:
            assert sub in menu_subcommands, f"{group_name} 的子命令 {sub} 不一致"
        print(f"✅ {group_name} 子命令一致: {len(menu_subcommands)} 个")


def test_interactive_menu_async():
    """测试异步交互菜单"""
    print("\n" + "=" * 60)
    print("测试 7: 异步交互菜单（模拟退出）")
    print("=" * 60)
    
    async def test_exit():
        with patch('questionary.select') as mock_select:
            mock_instance = MagicMock()
            mock_instance.ask.return_value = "exit"
            mock_select.return_value = mock_instance
            
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                from media_tools.transcribe.cli.interactive_menu import run
                exit_code = await run([])
            
            assert exit_code == 0, f"选择 exit 应返回 0, 实际返回 {exit_code}"
            return True
    
    result = asyncio.run(test_exit())
    assert result, "异步退出测试失败"
    print(f"✅ 异步交互退出测试通过")


def run_all_tests():
    """运行所有测试"""
    print("\n")
    print("🚀 " * 20)
    print("开始测试 CLI 交互界面")
    print("🚀 " * 20)
    print("\n")
    
    tests = [
        ("主菜单结构", test_main_menu_structure),
        ("子菜单结构", test_group_menu_structure),
        ("菜单项属性", test_menu_item_attributes),
        ("直接命令执行", test_direct_command_execution),
        ("子命令执行", test_sub_command_execution),
        ("命令一致性", test_all_commands_in_menu),
        ("异步交互菜单", test_interactive_menu_async),
    ]
    
    passed = 0
    failed = 0
    errors = []
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
            print(f"✅ 测试 {passed}: {test_name} 通过\n")
        except Exception as e:
            failed += 1
            error_msg = f"❌ {test_name}: {e}"
            errors.append(error_msg)
            print(f"{error_msg}\n")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    print(f"总测试数: {len(tests)}")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    
    if errors:
        print("\n错误详情:")
        for error in errors:
            print(f"  {error}")
    
    print("=" * 60)
    
    if failed == 0:
        print("\n🎉 所有测试通过！CLI 交互界面工作正常！")
    else:
        print(f"\n⚠️  {failed} 个测试失败")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
