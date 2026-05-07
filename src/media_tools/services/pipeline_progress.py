from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from media_tools.domain.entities.task import Stage


ALLOWED_STAGES = {"fetching", "auditing", "downloading", "uploading", "transcribing", "exporting", "completed", "failed"}


def _normalize_stage(raw: str) -> str:
    value = raw.strip().lower()
    mapping = {
        "initializing": "fetching",
        "scanning": "fetching",
        "queued": "fetching",
        "listing": "fetching",
        "list": "fetching",
        "created": "fetching",
        "fetching": "fetching",
        "audit": "auditing",
        "reconcile": "auditing",
        "auditing": "auditing",
        "downloading": "downloading",
        "download": "downloading",
        "uploading": "uploading",
        "upload": "uploading",
        "transcribing": "transcribing",
        "transcribe": "transcribing",
        "exporting": "exporting",
        "export": "exporting",
        "completed": "completed",
        "success": "completed",
        "done": "completed",
        "failed": "failed",
        "error": "failed",
        "cancelled": "failed",
        "canceled": "failed",
    }
    normalized = mapping.get(value, value)
    return normalized if normalized in ALLOWED_STAGES else "downloading"


def stage_to_enum(raw_stage: str) -> Stage:
    normalized = _normalize_stage(raw_stage)
    mapping = {
        "fetching": Stage.FETCHING,
        "auditing": Stage.AUDITING,
        "downloading": Stage.DOWNLOADING,
        "uploading": Stage.TRANSCRIBING,
        "transcribing": Stage.TRANSCRIBING,
        "exporting": Stage.EXPORTING,
        "completed": Stage.COMPLETED,
        "failed": Stage.FAILED,
    }
    return mapping.get(normalized, Stage.DOWNLOADING)


def _clamp_progress(progress: float | Optional[int]) -> float:
    try:
        value = float(progress or 0.0)
    except (TypeError, ValueError):
        value = 0.0
    return max(0.0, min(value, 1.0))


def _estimate_count(done_ratio: float, total: int) -> int:
    if total <= 0:
        return 0
    ratio = max(0.0, min(done_ratio, 1.0))
    return min(total, int(ratio * total + 0.5))


def _extract_missing_count(payload: dict[str, Any]) -> int:
    raw = payload.get("missing_items")
    if isinstance(raw, list):
        return len(raw)
    return 0


def _extract_result_summary_counts(payload: dict[str, Any]) -> tuple[int, int]:
    summary = payload.get("result_summary")
    if isinstance(summary, dict):
        try:
            total = int(summary.get("total") or 0)
        except (TypeError, ValueError):
            total = 0
        try:
            done = int((summary.get("success") or 0)) + int((summary.get("failed") or 0))
        except (TypeError, ValueError):
            done = 0
        return max(done, 0), max(total, 0)

    subtasks = payload.get("subtasks")
    if isinstance(subtasks, list) and subtasks:
        total = len(subtasks)
        done = 0
        for item in subtasks:
            if isinstance(item, dict) and str(item.get("status") or "").lower() in ("completed", "failed", "success", "error"):
                done += 1
        return done, total

    return 0, 0


def _extract_export_meta(payload: dict[str, Any]) -> tuple[Optional[str], str | Optional[int]]:
    pipeline_progress = payload.get("pipeline_progress")
    if isinstance(pipeline_progress, dict):
        export = pipeline_progress.get("export")
        if isinstance(export, dict):
            file = export.get("file")
            status = export.get("status")
            return (str(file) if isinstance(file, str) and file else None), (status if status is not None else None)
        file = pipeline_progress.get("file")
        status = pipeline_progress.get("status")
        return (str(file) if isinstance(file, str) and file else None), (status if status is not None else None)

    top_file = payload.get("export_file") or payload.get("export_path")
    top_status = payload.get("export_status")
    if isinstance(top_file, str) and top_file.strip():
        return top_file.strip(), (top_status if top_status is not None else None)

    subtasks = payload.get("subtasks")
    if isinstance(subtasks, list) and subtasks:
        for item in reversed(subtasks):
            if not isinstance(item, dict):
                continue
            candidate = item.get("transcript_path") or item.get("export_file") or item.get("file")
            if isinstance(candidate, str) and candidate.strip():
                status = item.get("export_status") or item.get("status")
                return candidate.strip(), (status if status is not None else None)

    return None, None


def _estimate_time_remaining(
    progress: float,
    start_time: Optional[str],
    stage: str,
    download_total: int,
    download_done: int,
) -> Optional[str]:
    """估算剩余时间"""
    if progress <= 0 or not start_time:
        return None

    try:
        start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        now = datetime.now(start.tzinfo)
        elapsed = (now - start).total_seconds()

        if elapsed < 10:
            return None

        if progress >= 1.0:
            return "已完成"

        estimated_total = elapsed / progress
        remaining = estimated_total - elapsed

        if remaining < 60:
            return f"{int(remaining)} 秒"
        elif remaining < 3600:
            minutes = int(remaining / 60)
            seconds = int(remaining % 60)
            if seconds > 0:
                return f"{minutes} 分 {seconds} 秒"
            return f"{minutes} 分钟"
        else:
            hours = int(remaining / 3600)
            minutes = int((remaining % 3600) / 60)
            if minutes > 0:
                return f"{hours} 小时 {minutes} 分钟"
            return f"{hours} 小时"

    except Exception:
        return None


def build_pipeline_progress(
    task_type: str,
    status: str,
    progress: float | Optional[int],
    payload: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    if task_type != "pipeline" and task_type != "download" and not task_type.startswith("creator_sync"):
        return None

    payload = payload or {}
    overall = _clamp_progress(progress)

    stage_str: Optional[str] = None
    payload_pp = payload.get("pipeline_progress")
    if isinstance(payload_pp, dict):
        raw_stage = payload_pp.get("stage")
        if isinstance(raw_stage, str) and raw_stage.strip():
            stage_str = _normalize_stage(raw_stage)

    if status in ("COMPLETED", "SUCCESS"):
        stage_str = "completed"
    elif status in ("FAILED", "ERROR", "CANCELLED"):
        stage_str = "failed"
    elif not stage_str:
        if task_type == "download":
            stage_str = "downloading"
        elif task_type.startswith("creator_sync"):
            stage_str = "downloading" if overall >= 0.1 else "fetching"
        else:
            stage_str = "downloading" if overall < 0.4 else "transcribing"

    stage_str = stage_str if stage_str in ALLOWED_STAGES else "downloading"

    list_done = 1
    list_total = 1

    missing = _extract_missing_count(payload)

    download_total = 0
    if isinstance(payload.get("batch_size"), int):
        download_total = int(payload.get("batch_size") or 0)
    elif isinstance(payload.get("video_urls"), list):
        download_total = len(payload.get("video_urls") or [])
    elif isinstance(payload.get("max_counts"), int):
        download_total = int(payload.get("max_counts") or 0)
    if download_total <= 0:
        download_total = 1

    if task_type == "download":
        download_done = _estimate_count(overall, download_total)
    elif task_type.startswith("creator_sync"):
        download_done = _estimate_count(min(overall, 0.7) / 0.7 if overall > 0 else 0.0, download_total)
    else:
        download_done = _estimate_count(min(overall, 0.4) / 0.4 if overall > 0 else 0.0, download_total)

    transcribe_done, transcribe_total = _extract_result_summary_counts(payload)
    if transcribe_total <= 0:
        transcribe_total = download_total if task_type != "download" else 0
    if transcribe_total > 0 and transcribe_done <= 0 and task_type == "pipeline" and overall > 0.4:
        transcribe_done = _estimate_count((overall - 0.4) / 0.6, transcribe_total)

    export_file, export_status = _extract_export_meta(payload)
    export_done: int = 1 if status in ("COMPLETED", "SUCCESS") else 0

    download_progress_data = payload_pp.get("download_progress") if isinstance(payload_pp, dict) else None
    transcribe_progress_data = payload_pp.get("transcribe_progress") if isinstance(payload_pp, dict) else None

    download_current_video = ""
    download_current_video_progress = 0.0
    download_current_index = 0
    if isinstance(download_progress_data, dict):
        download_current_video = str(download_progress_data.get("current_video", ""))
        download_current_video_progress = float(download_progress_data.get("current_video_progress", 0.0))
        download_current_index = int(download_progress_data.get("current_index", 0))

    transcribe_current_video = ""
    transcribe_account = ""
    if isinstance(transcribe_progress_data, dict):
        transcribe_current_video = str(transcribe_progress_data.get("current_video", ""))
        transcribe_account = str(transcribe_progress_data.get("current_account", ""))

    return {
        "stage": stage_str,
        "list": {"done": int(list_done), "total": int(list_total)},
        "audit": {"missing": int(missing)},
        "download": {
            "done": int(download_done),
            "total": int(download_total),
            "current_video": download_current_video,
            "current_video_progress": download_current_video_progress,
            "current_index": download_current_index,
        },
        "transcribe": {
            "done": int(transcribe_done),
            "total": int(transcribe_total),
            "current_video": transcribe_current_video,
            "account_id": transcribe_account,
        },
        "export": {
            "done": int(1 if export_done else 0),
            "total": 1,
            "file": export_file,
            "status": export_status,
        },
    }


def build_task_progress(
    task_type: str,
    status: str,
    progress: float | Optional[int],
    payload: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    """构建完整任务进度信息（新版格式）"""
    pp = build_pipeline_progress(task_type, status, progress, payload)
    if not pp:
        return None

    payload = payload or {}
    stage_enum = stage_to_enum(pp["stage"])

    payload_pp = payload.get("pipeline_progress") if isinstance(payload, dict) else None
    download_progress_data = payload_pp.get("download_progress") if isinstance(payload_pp, dict) else None
    transcribe_progress_data = payload_pp.get("transcribe_progress") if isinstance(payload_pp, dict) else None

    from media_tools.domain.entities.task import DownloadProgress, TranscribeProgress

    download_progress = None
    if download_progress_data or pp.get("download"):
        dp_data = download_progress_data or {}
        pp_dl = pp.get("download", {})
        download_progress = DownloadProgress(
            downloaded=dp_data.get("downloaded", pp_dl.get("done", 0)),
            skipped=dp_data.get("skipped", 0),
            failed=dp_data.get("failed", 0),
            total=dp_data.get("total", pp_dl.get("total", 0)),
            current_video=dp_data.get("current_video", pp_dl.get("current_video", "")),
            current_video_progress=float(dp_data.get("current_video_progress", pp_dl.get("current_video_progress", 0.0))),
            current_index=dp_data.get("current_index", pp_dl.get("current_index", 0)),
        )

    transcribe_progress = None
    if transcribe_progress_data or pp.get("transcribe"):
        tp_data = transcribe_progress_data or {}
        pp_tp = pp.get("transcribe", {})
        transcribe_progress = TranscribeProgress(
            done=tp_data.get("done", pp_tp.get("done", 0)),
            skipped=tp_data.get("skipped", 0),
            failed=tp_data.get("failed", 0),
            total=tp_data.get("total", pp_tp.get("total", 0)),
            current_video=tp_data.get("current_video", pp_tp.get("current_video", "")),
            current_account=tp_data.get("current_account", pp_tp.get("account_id", "")),
        )

    errors = []
    error_details = []
    if isinstance(payload_pp, dict):
        errors = list(payload_pp.get("errors", []))
        for err in errors:
            if isinstance(err, dict):
                error_details.append({
                    "code": err.get("code", "UNKNOWN"),
                    "message": err.get("message", str(err)),
                    "suggestion": err.get("suggestion", ""),
                    "timestamp": err.get("timestamp", ""),
                })
            else:
                error_details.append({
                    "code": "UNKNOWN",
                    "message": str(err),
                    "suggestion": "",
                    "timestamp": "",
                })
    error_count = len(errors)

    start_time = payload.get("start_time") if isinstance(payload, dict) else None
    estimated_remaining = _estimate_time_remaining(
        float(progress or 0),
        start_time,
        pp["stage"],
        pp["download"]["total"],
        pp["download"]["done"],
    )

    return {
        "stage": stage_enum.value,
        "stage_label": _get_stage_label(stage_enum.value),
        "stage_icon": _get_stage_icon(stage_enum.value),
        "overall_percent": float(progress or 0) * 100,
        "download_progress": download_progress.to_dict() if download_progress else None,
        "transcribe_progress": transcribe_progress.to_dict() if transcribe_progress else None,
        "error_count": error_count,
        "errors": error_details,
        "start_time": start_time,
        "estimated_time_remaining": estimated_remaining,
        "message": _build_progress_message(
            stage_enum.value,
            download_progress,
            transcribe_progress,
            error_count,
            status,
        ),
    }


def _get_stage_label(stage: str) -> str:
    """获取阶段显示名称"""
    mapping = {
        "created": "等待中",
        "fetching": "获取列表",
        "auditing": "对账中",
        "downloading": "下载中",
        "transcribing": "转写中",
        "exporting": "导出中",
        "completed": "已完成",
        "failed": "失败",
        "cancelled": "已取消",
    }
    return mapping.get(stage, stage)


def _get_stage_icon(stage: str) -> str:
    """获取阶段图标"""
    mapping = {
        "created": "⏳",
        "fetching": "📋",
        "auditing": "✔️",
        "downloading": "⬇️",
        "transcribing": "✍️",
        "exporting": "📤",
        "completed": "✅",
        "failed": "❌",
        "cancelled": "🚫",
    }
    return mapping.get(stage, "📦")


def _build_progress_message(
    stage: str,
    download_progress: Any,
    transcribe_progress: Any,
    error_count: int,
    status: str,
) -> str:
    """构建进度显示消息"""
    if status in ("COMPLETED", "SUCCESS"):
        dl_done = download_progress.downloaded if download_progress else 0
        dl_total = download_progress.total if download_progress else 0
        tr_done = transcribe_progress.done if transcribe_progress else 0
        tr_total = transcribe_progress.total if transcribe_progress else 0
        
        parts = []
        if dl_done > 0 or dl_total > 0:
            parts.append(f"下载 {dl_done}/{dl_total}")
        if tr_done > 0 or tr_total > 0:
            parts.append(f"转写 {tr_done}/{tr_total}")
        if error_count > 0:
            parts.append(f"失败 {error_count}")
        
        if parts:
            return f"已完成：{', '.join(parts)}"
        return "已完成"
    
    if status in ("FAILED", "ERROR"):
        return f"失败：{error_count} 个错误"
    
    if stage == "downloading" and download_progress:
        current_video = download_progress.current_video or "视频"
        return f"正在下载 ({download_progress.downloaded}/{download_progress.total})：{current_video}"
    
    if stage == "transcribing" and transcribe_progress:
        current_video = transcribe_progress.current_video or "视频"
        account = transcribe_progress.current_account
        account_suffix = f" [{account}]" if account else ""
        return f"正在转写 ({transcribe_progress.done}/{transcribe_progress.total}){account_suffix}：{current_video}"
    
    stage_labels = {
        "created": "等待开始...",
        "fetching": "正在获取视频列表...",
        "auditing": "对账中...",
        "exporting": "正在导出...",
        "cancelled": "已取消",
    }
    
    return stage_labels.get(stage, "处理中...")
