#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库辅助模块 - 提供安全的 SQLite 上下文管理
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .config_mgr import get_config


@contextmanager
def get_db_connection(db_path=None):
    """
    获取数据库连接的上下文管理器

    用法:
        with get_db_connection() as (conn, cursor):
            cursor.execute("SELECT * FROM table")
            results = cursor.fetchall()

    Args:
        db_path: 数据库路径，默认使用配置的数据库

    Yields:
        (conn, cursor) 元组
    """
    config = get_config()
    path = Path(db_path) if db_path else config.get_db_path()

    conn = None
    try:
        conn = sqlite3.connect(str(path))
        cursor = conn.cursor()
        yield conn, cursor
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def execute_query(query, params=None, db_path=None):
    """
    执行查询并返回结果

    Args:
        query: SQL 查询语句
        params: 查询参数
        db_path: 数据库路径

    Returns:
        查询结果列表
    """
    with get_db_connection(db_path) as (conn, cursor):
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.fetchall()


def execute_update(query, params=None, db_path=None):
    """
    执行更新操作

    Args:
        query: SQL 更新语句
        params: 更新参数
        db_path: 数据库路径

    Returns:
        影响的行数
    """
    with get_db_connection(db_path) as (conn, cursor):
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.rowcount
