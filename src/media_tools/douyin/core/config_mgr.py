#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一配置管理模块
"""

import os
from pathlib import Path

import yaml


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_path=None):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径，默认使用项目根目录的 config/config.yaml
        """
        if config_path is None:
            # 自动检测项目根目录（src/media_tools/douyin/core/ 的上 4 级）
            project_root = Path(__file__).parent.parent.parent.parent.parent.resolve()
            config_path = project_root / "config" / "config.yaml"

        self.config_path = Path(config_path)
        self._config = {}
        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
        else:
            self._config = {}

    def reload(self):
        """重新加载配置"""
        self._load_config()

    def get(self, key, default=None):
        """
        获取配置值

        Args:
            key: 配置键，支持点号分隔的嵌套键，如 'download.path'
            default: 默认值

        Returns:
            配置值
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key, value):
        """
        设置配置值（仅内存，不写入文件）

        Args:
            key: 配置键
            value: 配置值
        """
        keys = key.split(".")
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def save(self, config_path=None):
        """
        保存配置到文件

        Args:
            config_path: 保存路径，默认使用初始化时的路径
        """
        save_path = Path(config_path) if config_path else self.config_path
        save_path.parent.mkdir(parents=True, exist_ok=True)

        with open(save_path, "w", encoding="utf-8") as f:
            yaml.dump(self._config, f, allow_unicode=True, default_flow_style=False)

    def has_cookie(self):
        """检查是否配置了 Cookie"""
        cookie = self.get("cookie") or self.get("douyin.cookie")
        return bool(cookie) and len(cookie.strip()) > 0

    def get_cookie(self):
        """获取 Cookie 字符串"""
        return self.get("cookie") or self.get("douyin.cookie", "")

    def get_download_path(self):
        """获取下载路径"""
        path = self.get("download.path")
        if path:
            return Path(path)

        # 默认使用项目根目录下的 downloads/
        project_root = Path(__file__).parent.parent.parent.parent.parent.resolve()
        return project_root / "downloads"

    def get_db_path(self):
        """获取数据库路径"""
        path = self.get("database.path")
        if path:
            return Path(path)

        # 默认使用项目根目录下的 douyin_users.db
        project_root = Path(__file__).parent.parent.parent.parent.parent.resolve()
        return project_root / "douyin_users.db"

    def get_naming(self):
        """获取文件命名格式"""
        return self.get("naming", "{desc}_{aweme_id}")

    def is_auto_transcribe(self):
        """获取是否开启自动转写"""
        val = self.get("auto_transcribe", False)
        # 兼容字符串 'true' 和布尔值 True
        if isinstance(val, str):
            return val.lower() in ('true', '1', 'yes')
        return bool(val)

    def is_auto_delete_video(self):
        """获取是否开启转写成功后自动删除视频"""
        val = self.get("auto_delete_video", True) # 默认为 True，节省空间
        if isinstance(val, str):
            return val.lower() in ('true', '1', 'yes')
        return bool(val)

    def get_following_path(self):
        """获取关注列表路径"""
        path = self.get("following.path")
        if path:
            return Path(path)

        # 默认使用项目根目录下的 config/following.json
        project_root = Path(__file__).parent.parent.parent.parent.parent.resolve()
        return project_root / "config" / "following.json"

    def validate(self):
        """
        验证配置是否完整

        Returns:
            (is_valid, errors) 元组
        """
        errors = []

        # 检查配置文件是否存在
        if not self.config_path.exists():
            errors.append(f"配置文件不存在: {self.config_path}")
            return False, errors

        # 检查 Cookie
        if not self.has_cookie():
            errors.append("未配置 Cookie，请运行登录功能获取")

        # 检查下载路径
        download_path = self.get_download_path()
        if not download_path.exists():
            try:
                download_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"无法创建下载目录: {e}")

        return len(errors) == 0, errors


# 全局配置实例（单例模式）
_config_instance = None


def get_config(config_path=None):
    """
    获取全局配置实例

    Args:
        config_path: 配置文件路径

    Returns:
        ConfigManager 实例
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager(config_path)
    return _config_instance


def reset_config():
    """重置配置实例（用于测试）"""
    global _config_instance
    _config_instance = None
