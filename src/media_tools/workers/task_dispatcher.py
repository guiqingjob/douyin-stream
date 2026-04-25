from typing import Any
import uuid

from media_tools.api.schemas import (
    PipelineRequest,
    BatchPipelineRequest,
    DownloadBatchRequest,
    LocalTranscribeRequest,
)
from media_tools.repositories.task_repository import TaskRepository
from media_tools.services.task_ops import notify_task_update
from media_tools.services.task_state import _register_background_task
from media_tools.services.local_asset_service import _register_local_assets
from media_tools.workers.pipeline_worker import (
    _background_pipeline_worker,
    _background_batch_worker,
    _background_download_worker,
)
from media_tools.workers.full_sync_worker import _background_full_sync_worker
from media_tools.workers.local_transcribe_worker import _background_local_transcribe_worker


async def _create_task(task_id: str, task_type: str, request_params: dict):
    msg = "任务已启动，准备执行..."
    payload = {**request_params, "msg": msg}
    TaskRepository.create_running(task_id, task_type, payload)
    await notify_task_update(task_id, 0.0, msg, "RUNNING", task_type)


async def _start_task_worker(task_id: str, task_type: str, original_params: dict[str, Any]):
    if task_type == "pipeline" and "url" in original_params:
        req = PipelineRequest(
            url=original_params.get("url", ""),
            max_counts=original_params.get("max_counts", 5),
            auto_delete=original_params.get("auto_delete", True)
        )
        _register_background_task(task_id, _background_pipeline_worker(task_id, req))
        return {"task_id": task_id, "status": "started", "message": "Pipeline task rerun"}

    elif task_type == "pipeline" and "video_urls" in original_params:
        batch_req = BatchPipelineRequest(
            video_urls=original_params.get("video_urls", []),
            auto_delete=original_params.get("auto_delete", True)
        )
        _register_background_task(task_id, _background_batch_worker(task_id, batch_req))
        return {"task_id": task_id, "status": "started", "message": "Batch pipeline task rerun"}

    elif task_type == "download" and "video_urls" in original_params:
        dl_req = DownloadBatchRequest(video_urls=original_params.get("video_urls", []))
        _register_background_task(task_id, _background_download_worker(task_id, dl_req))
        return {"task_id": task_id, "status": "started", "message": "Download task rerun"}

    elif task_type.startswith("creator_sync") and "uid" in original_params:
        uid = str(original_params.get("uid", ""))
        mode = str(original_params.get("mode", "incremental"))
        batch_size: int | None = original_params.get("batch_size")
        from media_tools.workers.creator_sync import background_creator_download_worker
        _register_background_task(task_id, background_creator_download_worker(task_id, uid, mode, batch_size, original_params))
        return {"task_id": task_id, "status": "started", "message": "Creator sync task rerun"}

    elif task_type.startswith("full_sync") and "mode" in original_params:
        mode = str(original_params.get("mode", "incremental"))
        batch_size: int | None = original_params.get("batch_size")
        _register_background_task(task_id, _background_full_sync_worker(task_id, mode, batch_size, original_params))
        return {"task_id": task_id, "status": "started", "message": "Full sync task rerun"}

    elif task_type == "local_transcribe" and "file_paths" in original_params:
        local_req = LocalTranscribeRequest(
            file_paths=original_params.get("file_paths", []),
            delete_after=original_params.get("delete_after", False),
            directory_root=original_params.get("directory_root")
        )
        _register_background_task(task_id, _background_local_transcribe_worker(task_id, local_req))
        return {"task_id": task_id, "status": "started", "message": "Local transcribe task rerun"}

    else:
        return {"status": "error", "message": f"Unsupported task type: {task_type}"}


async def _retry_task_worker(task_id: str, task_type: str, original_params: dict[str, Any]):
    """创建新任务并重试原任务逻辑。"""
    original_params.pop("msg", None)

    if task_type == "pipeline" and "url" in original_params:
        req = PipelineRequest(
            url=original_params.get("url", ""),
            max_counts=original_params.get("max_counts", 5),
            auto_delete=original_params.get("auto_delete", True)
        )
        new_task_id = str(uuid.uuid4())
        await _create_task(
            new_task_id,
            task_type,
            {"url": req.url, "max_counts": req.max_counts, "auto_delete": req.auto_delete},
        )
        _register_background_task(new_task_id, _background_pipeline_worker(new_task_id, req))
        return {"task_id": new_task_id, "status": "started", "message": "Pipeline task retry started"}

    elif task_type == "pipeline" and "video_urls" in original_params:
        batch_req = BatchPipelineRequest(
            video_urls=original_params.get("video_urls", []),
            auto_delete=original_params.get("auto_delete", True)
        )
        new_task_id = str(uuid.uuid4())
        await _create_task(
            new_task_id,
            task_type,
            {"video_urls": batch_req.video_urls, "auto_delete": batch_req.auto_delete},
        )
        _register_background_task(new_task_id, _background_batch_worker(new_task_id, batch_req))
        return {"task_id": new_task_id, "status": "started", "message": "Batch pipeline task retry started"}

    elif task_type == "download" and "video_urls" in original_params:
        dl_req = DownloadBatchRequest(video_urls=original_params.get("video_urls", []))
        new_task_id = str(uuid.uuid4())
        await _create_task(new_task_id, task_type, {"video_urls": dl_req.video_urls})
        _register_background_task(new_task_id, _background_download_worker(new_task_id, dl_req))
        return {"task_id": new_task_id, "status": "started", "message": "Download task retry started"}

    elif task_type.startswith("creator_sync") and "uid" in original_params:
        uid = str(original_params.get("uid", ""))
        mode = str(original_params.get("mode", "incremental"))
        batch_size: int | None = original_params.get("batch_size")
        new_task_id = str(uuid.uuid4())
        await _create_task(new_task_id, f"creator_sync_{mode}", {"uid": uid, "mode": mode, "batch_size": batch_size})
        from media_tools.workers.creator_sync import background_creator_download_worker
        _register_background_task(new_task_id, background_creator_download_worker(new_task_id, uid, mode, batch_size, original_params))
        return {"task_id": new_task_id, "status": "started", "message": "Creator download task retry started"}

    elif task_type.startswith("full_sync") and "mode" in original_params:
        mode = str(original_params.get("mode", "incremental"))
        batch_size: int | None = original_params.get("batch_size")
        new_task_id = str(uuid.uuid4())
        await _create_task(new_task_id, f"full_sync_{mode}", {"mode": mode, "batch_size": batch_size})
        _register_background_task(new_task_id, _background_full_sync_worker(new_task_id, mode, batch_size, original_params))
        return {"task_id": new_task_id, "status": "started", "message": "Full sync task retry started"}

    elif task_type == "local_transcribe" and "file_paths" in original_params:
        local_req = LocalTranscribeRequest(
            file_paths=original_params.get("file_paths", []),
            delete_after=original_params.get("delete_after", False),
            directory_root=original_params.get("directory_root")
        )
        _register_local_assets(local_req.file_paths, local_req.delete_after, local_req.directory_root)
        new_task_id = str(uuid.uuid4())
        await _create_task(
            new_task_id,
            task_type,
            {
                "file_paths": local_req.file_paths,
                "delete_after": local_req.delete_after,
                "directory_root": local_req.directory_root,
            },
        )
        _register_background_task(new_task_id, _background_local_transcribe_worker(new_task_id, local_req))
        return {"task_id": new_task_id, "status": "started", "message": "Local transcribe task retry started"}

    else:
        return {"status": "error", "message": f"Unsupported task type for retry: {task_type}"}
