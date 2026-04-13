#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版交互菜单 - 使用 questionary 提供方向键选择体验
"""

try:
    import questionary
    HAS_QUESTIONARY = True
except ImportError:
    HAS_QUESTIONARY = False


def select_menu(title, choices, style=None):
    """
    显示选择菜单

    Args:
        title: 菜单标题
        choices: 选项列表，每个元素为 (key, description) 元组
        style: questionary 样式

    Returns:
        用户选择的 key，如果取消则返回 None
    """
    if not HAS_QUESTIONARY:
        # 回退到普通 input
        return None

    # 构建 choices 列表
    display_choices = []
    for key, desc in choices:
        display_choices.append(questionary.Choice(title=f"{key}. {desc}", value=key))

    # 添加退出选项
    display_choices.append(questionary.Separator())
    display_choices.append(questionary.Choice(title="0. 退出程序", value="0"))

    try:
        result = questionary.select(
            title,
            choices=display_choices,
            style=style,
        ).ask()

        return result
    except KeyboardInterrupt:
        return None


def confirm(message, default=False):
    """
    显示确认提示

    Args:
        message: 提示信息
        default: 默认值

    Returns:
        用户是否确认
    """
    if not HAS_QUESTIONARY:
        # 回退到普通 input
        try:
            result = input(f"{message} (y/N): ").strip().lower()
            return result == "y"
        except (EOFError, KeyboardInterrupt):
            return False

    try:
        return questionary.confirm(message, default=default).ask()
    except KeyboardInterrupt:
        return False


def input_text(message, default="", validate_func=None):
    """
    输入文本

    Args:
        message: 提示信息
        default: 默认值
        validate_func: 验证函数

    Returns:
        用户输入的文本
    """
    if not HAS_QUESTIONARY:
        try:
            result = input(f"{message}: ").strip()
            return result or default
        except (EOFError, KeyboardInterrupt):
            return default

    try:
        kwargs = {"message": message, "default": default}
        if validate_func:
            kwargs["validate"] = validate_func

        return questionary.text(**kwargs).ask()
    except KeyboardInterrupt:
        return default
