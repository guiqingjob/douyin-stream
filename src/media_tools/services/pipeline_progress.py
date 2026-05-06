from __future__ import annotations

from typing import Any, Optional, Union

ALLOWED_STAGES = {"list", "audit", "download", "upload", "transcribe", "export", "done", "failed"}


def _normalize_stage(raw: str) -> str:
    value = raw.strip().lower()
    mapping = {
        "initializing": "list",
        "scanning": "list",
        "queued": "list",
        "listing": "list",
        "list": "list",
        "audit": "audit",
        "reconcile": "audit",
        "downloading": "download",
        "download": "download",
        "uploading": "upload",
        "upload": "upload",
        "transcribing": "transcribe",
        "transcribe": "transcribe",
        "exporting": "export",
        "export": "export",
        "completed": "done",
        "success": "done",
        "done": "done",
        "failed": "failed",
        "error": "failed",
        "cancelled": "failed",
        "canceled": "failed",
    }
    normalized = mapping.get(value, value)
    return normalized if normalized in ALLOWED_STAGES else "download"


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


def build_pipeline_progress(
    task_type: str,
    status: str,
    progress: float | Optional[int],
    payload: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    if task_type != "pipeline" and task_type != "download" and not task_type.startswith("creator_sync"):
        return None

    payload = payload or {}
    overall = _clamp_progress(progress)

    stage: Optional[str] = None
    payload_pp = payload.get("pipeline_progress")
    if isinstance(payload_pp, dict):
        raw_stage = payload_pp.get("stage")
        if isinstance(raw_stage, str) and raw_stage.strip():
            stage = _normalize_stage(raw_stage)

    if status in ("COMPLETED", "SUCCESS"):
        stage = "done"
    elif status in ("FAILED", "ERROR", "CANCELLED"):
        stage = "failed"
    elif not stage:
        if task_type == "download":
            stage = "download"
        elif task_type.startswith("creator_sync"):
            stage = "download" if overall >= 0.1 else "list"
        else:
            stage = "download" if overall < 0.4 else "transcribe"

    stage = stage if stage in ALLOWED_STAGES else "download"

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

    return {
        "stage": stage,
        "list": {"done": int(list_done), "total": int(list_total)},
        "audit": {"missing": int(missing)},
        "download": {"done": int(download_done), "total": int(download_total)},
        "transcribe": {"done": int(transcribe_done), "total": int(transcribe_total)},
        "export": {
            "done": int(1 if export_done else 0),
            "total": 1,
            "file": export_file,
            "status": export_status,
        },
    }
