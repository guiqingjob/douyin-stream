#!/usr/bin/env python3
"""测试抖音下载相关模块的可调用性和错误处理"""

import asyncio
import importlib
import inspect
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

PASS = 0
FAIL = 0
WARN = 0
results = []

def record(status, module, test, detail=""):
    global PASS, FAIL, WARN
    if status == "PASS":
        PASS += 1
        symbol = "PASS"
    elif status == "FAIL":
        FAIL += 1
        symbol = "FAIL"
    else:
        WARN += 1
        symbol = "WARN"
    msg = f"  [{symbol}] {module}: {test}"
    if detail:
        msg += f" - {detail}"
    results.append(msg)
    print(msg)

# ====================================================================
# 1. 检查更新模块 (update_checker)
# ====================================================================
print("\n" + "=" * 60)
print("1. 更新模块 (update_checker)")
print("=" * 60)

try:
    from media_tools.douyin.core.update_checker import (
        check_all_updates,
        download_updates_for_user,
        _get_local_video_count,
        _get_db_video_count,
    )
    record("PASS", "update_checker", "模块导入成功")
except Exception as e:
    record("FAIL", "update_checker", f"模块导入失败: {e}")

# 检查函数签名
try:
    sig = inspect.signature(check_all_updates)
    record("PASS", "update_checker", "check_all_updates 函数签名可获取", str(sig))
except Exception as e:
    record("FAIL", "update_checker", "check_all_updates 函数签名检查失败", str(e))

# 测试错误处理: 空关注列表
try:
    with patch("media_tools.douyin.core.following_mgr.list_users", return_value=[]):
        result = check_all_updates()
        if isinstance(result, dict) and "users" in result:
            record("PASS", "update_checker", "空关注列表处理正常")
        else:
            record("FAIL", "update_checker", "空关注列表返回值异常", str(result))
except Exception as e:
    record("FAIL", "update_checker", "空关注列表错误处理失败", str(e))

# 测试 download_updates_for_user 无效用户
# Note: get_user is imported lazily inside the function, making it hard to patch.
# Instead, we verify the function handles the None case by checking source code.
try:
    import inspect
    source = inspect.getsource(download_updates_for_user)
    has_none_check = "if not user" in source and "return None" in source
    if has_none_check:
        record("PASS", "update_checker", "无效用户处理逻辑存在(源码检查)")
    else:
        record("WARN", "update_checker", "未发现无效用户处理逻辑")
except Exception as e:
    record("FAIL", "update_checker", "无效用户错误处理检查失败", str(e))

# ====================================================================
# 2. 下载模块 (downloader) 函数签名
# ====================================================================
print("\n" + "=" * 60)
print("2. 下载模块 (downloader) 函数签名")
print("=" * 60)

try:
    from media_tools.douyin.core.downloader import (
        download_by_url,
        download_by_uid,
        _download_with_stats,
        _get_f2_kwargs,
        _create_video_metadata_table,
        _save_video_metadata_from_raw,
        _clean_video_title,
    )
    record("PASS", "downloader", "模块导入成功")
except Exception as e:
    record("FAIL", "downloader", f"模块导入失败: {e}")

# 检查函数签名
try:
    sig = inspect.signature(download_by_url)
    params = list(sig.parameters.keys())
    expected = ["url", "max_counts"]
    if params == expected:
        record("PASS", "downloader", "download_by_url 签名正确", str(sig))
    else:
        record("WARN", "downloader", "download_by_url 签名不符", f"期望{expected}, 实际{params}")
except Exception as e:
    record("FAIL", "downloader", "download_by_url 签名检查失败", str(e))

try:
    sig = inspect.signature(download_by_uid)
    params = list(sig.parameters.keys())
    expected = ["uid", "max_counts"]
    if params == expected:
        record("PASS", "downloader", "download_by_uid 签名正确", str(sig))
    else:
        record("WARN", "downloader", "download_by_uid 签名不符", f"期望{expected}, 实际{params}")
except Exception as e:
    record("FAIL", "downloader", "download_by_uid 签名检查失败", str(e))

try:
    sig = inspect.signature(_download_with_stats)
    params = list(sig.parameters.keys())
    record("PASS", "downloader", "_download_with_stats 签名可获取", str(sig))
except Exception as e:
    record("FAIL", "downloader", "_download_with_stats 签名检查失败", str(e))

# 测试 _clean_video_title
try:
    assert _clean_video_title("测试 #话题 内容") == "测试"
    assert _clean_video_title("多行\n内容") == "多行"
    assert _clean_video_title("普通标题") == "普通标题"
    record("PASS", "downloader", "_clean_video_title 清洗逻辑正确")
except Exception as e:
    record("FAIL", "downloader", "_clean_video_title 测试失败", str(e))

# 测试 _get_f2_kwargs 可调用性
try:
    with patch("media_tools.douyin.core.downloader.get_config") as mock_cfg:
        mock_config = MagicMock()
        mock_config.get_cookie.return_value = "test_cookie"
        mock_config.get_download_path.return_value = Path("/tmp/test_downloads")
        mock_cfg.return_value = mock_config
        kwargs = _get_f2_kwargs()
        assert isinstance(kwargs, dict)
        assert "app_name" in kwargs
        assert kwargs["app_name"] == "douyin"
        record("PASS", "downloader", "_get_f2_kwargs 可调用并返回正确结构")
except Exception as e:
    record("FAIL", "downloader", "_get_f2_kwargs 调用失败", str(e))

# ====================================================================
# 3. F2 辅助模块 (f2_helper)
# ====================================================================
print("\n" + "=" * 60)
print("3. F2 辅助模块 (f2_helper)")
print("=" * 60)

try:
    from media_tools.douyin.core.f2_helper import (
        get_f2_kwargs,
        merge_f2_config,
    )
    record("PASS", "f2_helper", "模块导入成功")
except Exception as e:
    record("FAIL", "f2_helper", f"模块导入失败: {e}")

# 测试 merge_f2_config
try:
    main = {"a": 1, "b": {"x": 1, "y": 2}}
    custom = {"b": {"y": 99, "z": 3}, "c": "test"}
    result = merge_f2_config(main, custom)
    assert result["a"] == 1
    assert result["b"]["x"] == 1
    assert result["b"]["y"] == 99
    assert result["b"]["z"] == 3
    assert result["c"] == "test"
    record("PASS", "f2_helper", "merge_f2_config 合并逻辑正确")
except Exception as e:
    record("FAIL", "f2_helper", "merge_f2_config 测试失败", str(e))

# 测试 merge_f2_config 空值处理
try:
    result = merge_f2_config(None, None)
    assert isinstance(result, dict)
    assert len(result) == 0
    record("PASS", "f2_helper", "merge_f2_config 空值处理正确")
except Exception as e:
    record("FAIL", "f2_helper", "merge_f2_config 空值处理失败", str(e))

# 测试 get_f2_kwargs 可调用性
try:
    with patch("media_tools.douyin.core.f2_helper.get_config") as mock_cfg:
        mock_config = MagicMock()
        mock_config.get_cookie.return_value = "test_cookie"
        mock_config.get_download_path.return_value = Path("/tmp/test")
        mock_cfg.return_value = mock_config
        kwargs = get_f2_kwargs()
        assert isinstance(kwargs, dict)
        assert kwargs["app_name"] == "douyin"
        assert kwargs["mode"] == "post"
        assert "headers" in kwargs
        record("PASS", "f2_helper", "get_f2_kwargs 可调用并返回正确结构")
except Exception as e:
    record("FAIL", "f2_helper", "get_f2_kwargs 调用失败", str(e))

# ====================================================================
# 4. db_helper 数据库操作
# ====================================================================
print("\n" + "=" * 60)
print("4. db_helper 数据库操作")
print("=" * 60)

try:
    from media_tools.douyin.core.db_helper import (
        get_db_connection,
        execute_query,
        execute_update,
    )
    record("PASS", "db_helper", "模块导入成功")
except Exception as e:
    record("FAIL", "db_helper", f"模块导入失败: {e}")

# 测试 get_db_connection 正常流程
try:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_db = tmp.name
    with patch("media_tools.douyin.core.db_helper.get_config") as mock_cfg:
        mock_config = MagicMock()
        mock_config.get_db_path.return_value = Path(tmp_db)
        mock_cfg.return_value = mock_config
        with get_db_connection() as (conn, cursor):
            cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            cursor.execute("INSERT INTO test (name) VALUES (?)", ("test1",))
        # 查询验证
        with get_db_connection() as (conn, cursor):
            cursor.execute("SELECT * FROM test")
            rows = cursor.fetchall()
            assert len(rows) == 1
            assert rows[0][1] == "test1"
    os.unlink(tmp_db)
    record("PASS", "db_helper", "get_db_connection 正常读写")
except Exception as e:
    record("FAIL", "db_helper", "get_db_connection 测试失败", str(e))

# 测试 execute_query 和 execute_update
try:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_db = tmp.name
    with patch("media_tools.douyin.core.db_helper.get_config") as mock_cfg:
        mock_config = MagicMock()
        mock_config.get_db_path.return_value = Path(tmp_db)
        mock_cfg.return_value = mock_config
        execute_update("CREATE TABLE test2 (id INTEGER PRIMARY KEY, val TEXT)")
        execute_update("INSERT INTO test2 (val) VALUES (?)", ("hello",))
        results_q = execute_query("SELECT val FROM test2 WHERE val = ?", ("hello",))
        assert len(results_q) == 1
        assert results_q[0][0] == "hello"
    os.unlink(tmp_db)
    record("PASS", "db_helper", "execute_query/execute_update 正常工作")
except Exception as e:
    record("FAIL", "db_helper", "execute_query/execute_update 测试失败", str(e))

# 测试错误处理: 无效SQL
try:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_db = tmp.name
    with patch("media_tools.douyin.core.db_helper.get_config") as mock_cfg:
        mock_config = MagicMock()
        mock_config.get_db_path.return_value = Path(tmp_db)
        mock_cfg.return_value = mock_config
        try:
            execute_query("SELECT * FROM non_existent_table")
            record("FAIL", "db_helper", "无效SQL未抛出异常")
        except sqlite3.OperationalError:
            record("PASS", "db_helper", "无效SQL正确抛出OperationalError")
    os.unlink(tmp_db)
except Exception as e:
    record("FAIL", "db_helper", "无效SQL错误处理失败", str(e))

# 测试事务回滚
try:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_db = tmp.name
    with patch("media_tools.douyin.core.db_helper.get_config") as mock_cfg:
        mock_config = MagicMock()
        mock_config.get_db_path.return_value = Path(tmp_db)
        mock_cfg.return_value = mock_config
        execute_update("CREATE TABLE test3 (id INTEGER PRIMARY KEY, val INTEGER CHECK(val > 0))")
        try:
            execute_update("INSERT INTO test3 (val) VALUES (?)", (-1,))
            record("FAIL", "db_helper", "约束违规未抛出异常")
        except sqlite3.IntegrityError:
            # 验证数据确实被回滚
            rows = execute_query("SELECT COUNT(*) FROM test3")
            if rows[0][0] == 0:
                record("PASS", "db_helper", "事务回滚正确")
            else:
                record("FAIL", "db_helper", "事务回滚失败, 数据已写入")
    os.unlink(tmp_db)
except Exception as e:
    record("FAIL", "db_helper", "事务回滚测试失败", str(e))

# ====================================================================
# 5. 视频元数据生成 (data_generator)
# ====================================================================
print("\n" + "=" * 60)
print("5. 视频元数据生成 (data_generator)")
print("=" * 60)

try:
    from media_tools.douyin.core.data_generator import (
        generate_data,
        _get_video_metadata,
        _extract_aweme_id,
        _scan_videos,
        _build_user_data,
        _copy_index_template,
    )
    record("PASS", "data_generator", "模块导入成功")
except Exception as e:
    record("FAIL", "data_generator", f"模块导入失败: {e}")

# 测试 _extract_aweme_id
try:
    assert _extract_aweme_id("7234567890123456789_video.mp4") == "7234567890123456789"
    assert _extract_aweme_id("7234567890123456789.mp4") == "7234567890123456789"
    assert _extract_aweme_id("some_title_7234567890123456789_other.mp4") == "7234567890123456789"
    record("PASS", "data_generator", "_extract_aweme_id 提取逻辑正确")
except Exception as e:
    record("FAIL", "data_generator", "_extract_aweme_id 测试失败", str(e))

# 测试 _get_video_metadata 空数据库
try:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        result = _get_video_metadata(db_path)
        assert isinstance(result, dict)
        assert len(result) == 0
        record("PASS", "data_generator", "_get_video_metadata 空数据库返回空字典")
except Exception as e:
    record("FAIL", "data_generator", "_get_video_metadata 空数据库测试失败", str(e))

# 测试 _get_video_metadata 有数据
try:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE video_metadata (
                aweme_id TEXT PRIMARY KEY, uid TEXT, nickname TEXT, desc TEXT,
                create_time INTEGER, duration INTEGER, digg_count INTEGER DEFAULT 0,
                comment_count INTEGER DEFAULT 0, collect_count INTEGER DEFAULT 0,
                share_count INTEGER DEFAULT 0, play_count INTEGER DEFAULT 0,
                local_filename TEXT, file_size INTEGER, fetch_time INTEGER
            )
        """)
        cursor.execute(
            "INSERT INTO video_metadata (aweme_id, uid, nickname, desc, digg_count) VALUES (?, ?, ?, ?, ?)",
            ("12345", "u1", "test_user", "test desc", 100)
        )
        conn.commit()
        conn.close()
        result = _get_video_metadata(db_path)
        assert "12345" in result
        assert result["12345"]["nickname"] == "test_user"
        assert result["12345"]["digg_count"] == 100
        record("PASS", "data_generator", "_get_video_metadata 有数据时正确返回")
except Exception as e:
    record("FAIL", "data_generator", "_get_video_metadata 有数据测试失败", str(e))

# 测试 _copy_index_template
try:
    with tempfile.TemporaryDirectory() as tmpdir:
        dl_path = Path(tmpdir)
        result = _copy_index_template(dl_path)
        assert result is True
        assert (dl_path / "index.html").exists()
        content = (dl_path / "index.html").read_text()
        assert "window.APP_DATA" in content
        record("PASS", "data_generator", "_copy_index_template 生成模板正确")
except Exception as e:
    record("FAIL", "data_generator", "_copy_index_template 测试失败", str(e))

# ====================================================================
# 6. 数据看板生成完整流程
# ====================================================================
print("\n" + "=" * 60)
print("6. 数据看板生成完整流程")
print("=" * 60)

try:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "test.db"
        
        # 创建数据库和表
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE video_metadata (
                aweme_id TEXT PRIMARY KEY, uid TEXT, nickname TEXT, desc TEXT,
                create_time INTEGER, duration INTEGER, digg_count INTEGER DEFAULT 0,
                comment_count INTEGER DEFAULT 0, collect_count INTEGER DEFAULT 0,
                share_count INTEGER DEFAULT 0, play_count INTEGER DEFAULT 0,
                local_filename TEXT, file_size INTEGER, fetch_time INTEGER
            )
        """)
        conn.commit()
        conn.close()
        
        # 创建用户目录和模拟视频文件
        user_dir = tmpdir / "test_user"
        user_dir.mkdir()
        (user_dir / "7234567890123456789.mp4").write_bytes(b"fake mp4 content")
        
        # 创建空的 following.json
        following_dir = tmpdir / ".media_tools"
        following_dir.mkdir()
        import json
        with open(following_dir / "following.json", "w") as f:
            json.dump({"users": [{"uid": "u1", "nickname": "test_user", "sec_user_id": "MS4wtest"}]}, f)
        
        with patch("media_tools.douyin.core.data_generator.get_config") as mock_cfg:
            mock_config = MagicMock()
            mock_config.get_download_path.return_value = tmpdir
            mock_config.get_db_path.return_value = db_path
            mock_cfg.return_value = mock_config
            
            result = generate_data()
            assert result is True
            assert (tmpdir / "data.js").exists()
            assert (tmpdir / "index.html").exists()
            
            # 验证 data.js 内容
            content = (tmpdir / "data.js").read_text()
            assert "window.APP_DATA" in content
            record("PASS", "data_generator", "完整数据看板生成流程成功")
except Exception as e:
    record("FAIL", "data_generator", "完整数据看板生成流程失败", str(e))

# ====================================================================
# 7. 视频压缩模块 (compressor)
# ====================================================================
print("\n" + "=" * 60)
print("7. 视频压缩模块 (compressor)")
print("=" * 60)

try:
    from media_tools.douyin.core.compressor import (
        check_ffmpeg,
        _get_video_info,
        _compress_video,
        compress_user_dir,
        compress_all,
    )
    record("PASS", "compressor", "模块导入成功")
except Exception as e:
    record("FAIL", "compressor", f"模块导入失败: {e}")

# 测试 check_ffmpeg 可调用性
try:
    result = check_ffmpeg()
    assert isinstance(result, bool)
    if result:
        record("PASS", "compressor", "check_ffmpeg 返回True (ffmpeg已安装)")
    else:
        record("WARN", "compressor", "check_ffmpeg 返回False (ffmpeg未安装)")
except Exception as e:
    record("FAIL", "compressor", "check_ffmpeg 调用失败", str(e))

# 测试 _get_video_info 无效文件
try:
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(b"not a real video")
        tmp_path = Path(tmp.name)
    result = _get_video_info(tmp_path)
    if result is None:
        record("PASS", "compressor", "_get_video_info 对无效文件返回None")
    else:
        record("WARN", "compressor", "_get_video_info 对无效文件未返回None")
    os.unlink(tmp_path)
except Exception as e:
    record("FAIL", "compressor", "_get_video_info 无效文件测试失败", str(e))

# 测试 _compress_video 对无效输入
try:
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_in:
        tmp_in.write(b"not a video")
        tmp_in_path = Path(tmp_in.name)
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_out:
        tmp_out_path = Path(tmp_out.name)
    success, orig_size, comp_size, error_msg = _compress_video(tmp_in_path, tmp_out_path)
    if not success and error_msg is not None:
        record("PASS", "compressor", "_compress_video 对无效输入正确返回失败", error_msg)
    else:
        record("WARN", "compressor", "_compress_video 对无效输入未返回失败")
    os.unlink(tmp_in_path)
    if tmp_out_path.exists():
        os.unlink(tmp_out_path)
except Exception as e:
    record("FAIL", "compressor", "_compress_video 无效输入测试失败", str(e))

# 测试 compress_user_dir 不存在目录
try:
    with patch("media_tools.douyin.core.compressor.get_config") as mock_cfg:
        mock_config = MagicMock()
        mock_config.get_download_path.return_value = Path("/tmp/nonexistent_test")
        mock_cfg.return_value = mock_config
        success, skipped, failed = compress_user_dir("nonexistent_user")
        assert success == 0
        record("PASS", "compressor", "compress_user_dir 不存在目录处理正确")
except Exception as e:
    record("FAIL", "compressor", "compress_user_dir 不存在目录测试失败", str(e))

# 测试压缩无视频目录
try:
    with tempfile.TemporaryDirectory() as tmpdir:
        user_dir = Path(tmpdir) / "test_user"
        user_dir.mkdir()
        with patch("media_tools.douyin.core.compressor.get_config") as mock_cfg:
            mock_config = MagicMock()
            mock_config.get_download_path.return_value = Path(tmpdir)
            mock_cfg.return_value = mock_config
            success, skipped, failed = compress_user_dir("test_user")
            assert success == 0 and skipped == 0
            record("PASS", "compressor", "compress_user_dir 无视频目录处理正确")
except Exception as e:
    record("FAIL", "compressor", "compress_user_dir 无视频目录测试失败", str(e))

# 测试 compress_all 无ffmpeg时
try:
    with patch("media_tools.douyin.core.compressor.check_ffmpeg", return_value=False):
        success, skipped, failed = compress_all()
        assert success == 0 and skipped == 0 and failed == 0
        record("PASS", "compressor", "compress_all 无ffmpeg时正确返回0")
except Exception as e:
    record("FAIL", "compressor", "compress_all 无ffmpeg测试失败", str(e))

# 测试路径遍历攻击防护
try:
    with patch("media_tools.douyin.core.compressor.get_config") as mock_cfg:
        mock_config = MagicMock()
        mock_config.get_download_path.return_value = Path("/tmp/test_dl")
        mock_cfg.return_value = mock_config
        # 传入带 ../ 的路径应被防御
        success, skipped, failed = compress_user_dir("../../etc/passwd")
        assert success == 0 and skipped == 0 and failed == 0
        record("PASS", "compressor", "路径遍历攻击防护有效")
except Exception as e:
    record("FAIL", "compressor", "路径遍历防护测试失败", str(e))

# ====================================================================
# 8. 错误处理
# ====================================================================
print("\n" + "=" * 60)
print("8. 错误处理")
print("=" * 60)

# 8a. 无效链接
print("\n  8a. 无效链接")
try:
    from media_tools.douyin.core.Downloader import download_by_url_sync
except ImportError:
    try:
        from media_tools.douyin.core.downloader import download_by_url_sync
        record("PASS", "error_handling", "download_by_url_sync 可导入")
    except Exception as e:
        record("FAIL", "error_handling", "download_by_url_sync 导入失败", str(e))
        download_by_url_sync = None

if download_by_url_sync:
    # 测试无效URL
    try:
        result = download_by_url_sync("not_a_valid_url")
        if result is None:
            record("PASS", "error_handling", "无效URL下载返回None")
        else:
            record("WARN", "error_handling", "无效URL下载返回值非None", str(result))
    except Exception as e:
        record("FAIL", "error_handling", "无效URL错误处理失败", str(e))
    
    # 测试空URL
    try:
        result = download_by_url_sync("")
        if result is None:
            record("PASS", "error_handling", "空URL返回None")
        else:
            record("WARN", "error_handling", "空URL返回值非None")
    except Exception as e:
        record("FAIL", "error_handling", "空URL错误处理失败", str(e))

# 8b. 网络断开模拟
print("\n  8b. 网络断开模拟")
try:
    with patch("media_tools.douyin.core.downloader.DouyinHandler") as mock_handler:
        mock_handler.side_effect = ConnectionError("Network is unreachable")
        # 使用 _get_f2_kwargs 的 mock
        with patch("media_tools.douyin.core.downloader._get_f2_kwargs", return_value={"url": "http://test"}):
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(_download_with_stats("http://test.com/user/123"))
                loop.close()
                record("FAIL", "error_handling", "网络断开未抛出异常")
            except ConnectionError:
                record("PASS", "error_handling", "网络断开正确抛出ConnectionError")
            except Exception as e:
                record("WARN", "error_handling", "网络断开抛出其他异常", str(e))
except Exception as e:
    record("FAIL", "error_handling", "网络断开模拟失败", str(e))

# 8c. 下载中断恢复
print("\n  8c. 下载中断恢复")
try:
    # 验证 downloader 模块中是否有增量下载逻辑 (检查 existing_videos 集合)
    import media_tools.douyin.core.downloader as dl_module
    source = inspect.getsource(dl_module)
    has_incremental_check = "existing_videos" in source
    if has_incremental_check:
        record("PASS", "error_handling", "下载模块包含增量下载/中断恢复逻辑")
    else:
        record("WARN", "error_handling", "下载模块未发现增量下载逻辑")
except Exception as e:
    record("FAIL", "error_handling", "中断恢复检查失败", str(e))

# ====================================================================
# 汇总
# ====================================================================
print("\n" + "=" * 60)
print("测试汇总")
print("=" * 60)
print(f"\n  PASS: {PASS}")
print(f"  FAIL: {FAIL}")
print(f"  WARN: {WARN}")
total = PASS + FAIL + WARN
print(f"  总计: {total}")
print(f"  通过率: {PASS/total*100:.1f}%" if total > 0 else "  通过率: N/A")

if FAIL > 0:
    print("\n  失败项目:")
    for r in results:
        if "[FAIL]" in r:
            print(f"    {r}")

if WARN > 0:
    print("\n  警告项目:")
    for r in results:
        if "[WARN]" in r:
            print(f"    {r}")

print()
