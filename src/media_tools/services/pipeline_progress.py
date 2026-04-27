from __future__ import annotations

from typing import Any


def build_pipeline_progress(task_type: str, status: str, progress: float | int | None) -> dict[str, Any] | None:
    if task_type != "pipeline":
        return None

    try:
        overall = float(progress or 0.0)
    except (TypeError, ValueError):
        overall = 0.0

    overall = max(0.0, min(overall, 1.0))

    if status == "COMPLETED":
        stage = "completed"
        stage_progress = 1.0
    elif status == "FAILED":
        stage = "failed"
        stage_progress = 0.0
    elif status == "CANCELLED":
        stage = "cancelled"
        stage_progress = 0.0
    else:
        if overall < 0.4:
            stage = "downloading"
            stage_progress = overall / 0.4
        else:
            stage = "transcribing"
            stage_progress = (overall - 0.4) / 0.6

        stage_progress = max(0.0, min(stage_progress, 1.0))

    return {
        "stage": stage,
        "stage_progress": stage_progress,
        "overall_progress": overall,
    }
