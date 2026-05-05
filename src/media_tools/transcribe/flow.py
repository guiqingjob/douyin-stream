from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from media_tools.logger import get_logger
logger = get_logger(__name__)

from .auth_state import resolve_qwen_cookie_string
from .config import load_config
from .export_utils import FlowDebugArtifacts, _get_video_title_from_db, build_export_output_path, save_debug_artifacts
from .http import RequestsApiContext, api_json, download_file
from .oss_upload import upload_file_to_oss
from .quota import get_quota_snapshot, record_quota_consumption
from .runtime import ExportConfig, ensure_dir, guess_mime_type, now_stamp


@dataclass(frozen=True, slots=True)
class FlowResult:
    record_id: str
    gen_record_id: str
    export_path: Path
    remote_deleted: bool


@dataclass(frozen=True, slots=True)
class ResumeState:
    """从 transcribe_runs 拿到的续传上下文。

    每个字段都可空，flow 根据已知字段决定从哪里续做：
    - export_url 存在 -> 直接 download_file，零额度消耗（Step 13a）
    - gen_record_id 存在 -> 跳过 token/upload/heartbeat/start，从 poll 继续（Step 13b）
    - 都没有 -> 走完整流程
    """
    stage: str = "queued"
    record_id: str | None = None
    gen_record_id: str | None = None
    batch_id: str | None = None
    export_url: str | None = None


def build_upload_tag(file_path: str | Path, mime_type: str) -> dict[str, Any]:
    parsed = Path(file_path)
    is_video = 1 if mime_type.startswith("video/") else 0
    return {
        "showName": parsed.stem,
        "fileFormat": parsed.suffix.removeprefix("."),
        "fileType": "local",
        "lang": "cn",
        "roleSplitNum": -1,
        "translateSwitch": 0,
        "transTargetValue": 0,
        "originalTag": json.dumps({"isVideo": is_video}),
        "client": "web",
    }


def transcript_headers(gen_record_id: str) -> dict[str, str]:
    return {
        "referer": f"https://www.qianwen.com/efficiency/doc/transcripts/{gen_record_id}?source=2",
        "x-tw-from": "tongyi",
    }


async def poll_until_done(context: Any, gen_record_id: str, timeout_seconds: float = 15 * 60) -> dict[str, Any]:
    url = "https://api.qianwen.com/assistant/api/record/list/poll?c=tongyi-web"
    payload = {
        "status": [10, 20, 30, 40, 41],
        "fileTypes": [],
        "beginTime": "",
        "mediaType": "",
        "endTime": "",
        "showName": "",
        "read": "",
        "lang": "",
        "shareUserId": "",
        "pageNo": 1,
        "pageSize": 1000,
        "recordSources": ["chat", "zhiwen", "tingwu"],
        "taskTypes": ["local", "net_source", "doc_read", "url_read", "paper_read", "book_read"],
        "terminal": "web",
        "module": "uploadhistory",
    }

    async def _poll_loop() -> dict[str, Any]:
        while True:
            response = await api_json(context, url, payload)
            # 部分错误响应会返回 {"data": null}，dict.get 默认值在 key 存在但值为 None 时不生效
            data = response.get("data") or {}
            for batch in data.get("batchRecord", []):
                for record in batch.get("recordList", []):
                    if record.get("genRecordId") == gen_record_id:
                        status = record.get("recordStatus")
                        if status == 30:
                            return record
                        # 转写失败状态：立即报错，不等超时
                        if status in (40, 41):
                            fail_reason = record.get("failReason") or record.get("errorMessage") or f"recordStatus={status}"
                            raise RuntimeError(f"转写失败: {fail_reason}")
            import random
            await asyncio.sleep(5 + random.uniform(0, 2))

    try:
        return await asyncio.wait_for(_poll_loop(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        raise RuntimeError(f"Polling timed out after {timeout_seconds}s for genRecordId={gen_record_id}")


async def delete_record(context: Any, record_ids: list[str]) -> bool:
    if not record_ids:
        return False
    response = await api_json(
        context,
        "https://api.qianwen.com/assistant/api/record/task/delete?c=tongyi-web",
        {"recordIds": record_ids},
    )
    return response.get("data") is True


async def export_file(context: Any, gen_record_id: str, export_config: ExportConfig) -> str:
    headers = transcript_headers(gen_record_id)
    app_config = load_config()
    max_attempts = app_config.export_max_retries
    initial_backoff = app_config.export_initial_backoff_seconds
    export_task_id = ""
    export_start_json: Any = {}
    for attempt in range(max_attempts):
        export_start_json = await api_json(
            context,
            "https://audio-api.qianwen.com/api/export/request?c=tongyi-web",
            {
                "action": "exportTrans",
                "transIds": [gen_record_id],
                "exportDetails": [
                    {
                        "docType": 1,
                        "fileType": export_config.file_type,
                        "withSpeaker": True,
                        "withTimeStamp": True,
                    }
                ],
            },
            headers,
        )
        export_task_id = str((export_start_json.get("data") or {}).get("exportTaskId", "")).strip()
        if export_task_id:
            break
        code = str(export_start_json.get("code", ""))
        message = str(export_start_json.get("message", "")).lower()
        request_too_fast = code == "EPO.RequestTooFast" or "request too fast" in message
        if not request_too_fast or attempt == max_attempts - 1:
            raise RuntimeError(f"Export start response missing exportTaskId: {export_start_json}")
        await asyncio.sleep(initial_backoff * (2**attempt))

    if not export_task_id:
        raise RuntimeError(f"Export start response missing exportTaskId: {export_start_json}")

    for _ in range(60):
        export_poll_json = await api_json(
            context,
            "https://audio-api.qianwen.com/api/export/request?c=tongyi-web",
            {
                "action": "getExportStatus",
                "exportTaskId": export_task_id,
            },
            headers,
        )
        export_data = export_poll_json.get("data") or {}
        if export_data.get("exportStatus") == 1:
            export_urls = export_data.get("exportUrls", [])
            export_url = export_urls[0].get("url", "") if export_urls else ""
            if export_url:
                return export_url
        await asyncio.sleep(5)

    raise RuntimeError(f"Export did not produce a downloadable URL for exportTaskId={export_task_id}")




def record_flow_quota_usage(
    *,
    account_id: str,
    before_snapshot,
    after_snapshot,
    log,
) -> int:
    consumed_minutes = max(0, before_snapshot.remaining_upload - after_snapshot.remaining_upload)
    record_quota_consumption(
        account_id=account_id,
        consumed_minutes=consumed_minutes,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
    )
    log(f"quota upload remaining after run: {after_snapshot.remaining_upload}/{after_snapshot.total_upload}")
    log(f"tracked quota consumption for this run: {consumed_minutes} minutes")
    return consumed_minutes


async def run_real_flow(
    *,
    file_path: str | Path,
    auth_state_path: str | Path,
    download_dir: str | Path,
    export_config: ExportConfig,
    should_delete: bool = False,
    account_id: str = "",
    cookie_string: str = "",
    export_gate: asyncio.Semaphore | None = None,
    title: str | None = None,
    shared_api: Any | None = None,
    run_id: str | None = None,
    resume_state: ResumeState | None = None,
) -> FlowResult:
    """执行单个视频的转写流程。

    Args:
        shared_api: 可选的 HTTP API 上下文（RequestsApiContext），由调用方共享。
            提供时跳过 token 解析与上下文创建，避免每个视频都重复鉴权。
        run_id: 可选的 transcribe_runs.run_id；提供时会在 4 个关键节点把 stage
            推进到 uploaded / transcribing / exporting / saved，让上传后失败可以
            被 orchestrator 通过 find_resumable 续做。失败由调用方 mark_failed。
        resume_state: 可选续传上下文。如有 export_url，直接 download 跳过所有 Qwen API；
            如有 gen_record_id（Step 13b），从 poll 继续。续传分支任何异常会
            自动 fallback 到完整流程，保证业务永远跑得通。
    """
    input_path = Path(file_path).resolve()
    output_dir = Path(download_dir).resolve()
    mime_type = guess_mime_type(input_path)
    stats = input_path.stat()
    quota_before = await get_quota_snapshot(
        auth_state_path=auth_state_path,
        account_id=account_id,
        cookie_string=cookie_string,
    )
    log = _make_flow_logger(input_path.name)

    # 仅在 run_id 存在时才 import + 写 transcribe_runs，避免给单元测试增加依赖
    def _checkpoint(stage: str, extra: dict[str, Any] | None = None) -> None:
        if not run_id:
            return
        try:
            from media_tools.repositories.transcribe_run_repository import TranscribeRunRepository
            TranscribeRunRepository.update_stage(run_id, stage, extra)
        except Exception as exc:  # noqa: BLE001  打卡失败不应中断主流程
            logger.warning(f"transcribe_runs 打卡失败 (run_id={run_id}, stage={stage}): {exc}")

    async def _do_flow(api: Any) -> FlowResult:
        log(f"Using file: {input_path}")
        log(f"File size: {stats.st_size}")
        log(f"quota upload remaining: {quota_before.remaining_upload}/{quota_before.total_upload}")

        token_json = await api_json(
            api,
            "https://api.qianwen.com/assistant/api/record/oss/token/get?c=tongyi-web",
            {
                "taskType": "local",
                "useSts": 1,
                "fileSize": stats.st_size,
                "dirIdStr": "",
                "fileContentType": mime_type,
                "bizTerminal": "web",
                "tag": build_upload_tag(input_path, mime_type),
            },
        )
        if not isinstance(token_json, dict) or "data" not in token_json:
            raise RuntimeError(f"获取上传凭证失败: {token_json}")
        token = token_json["data"]
        log(f"genRecordId: {token['genRecordId']}")
        log(f"recordId: {token['recordId']}")

        await upload_file_to_oss(
            token=token,
            file_path=input_path,
            mime_type=mime_type,
            on_progress=_make_upload_progress_logger(log),
        )

        await api_json(
            api,
            "https://api.qianwen.com/assistant/api/record/upload_heartbeat?c=tongyi-web",
            {"genRecordId": token["genRecordId"]},
        )
        log("upload heartbeat sent")

        # 打卡点 1：上传完成。Qwen 端文件已落，下次失败重试可以从这里续做
        _checkpoint("uploaded", {
            "record_id": token["recordId"],
            "gen_record_id": token["genRecordId"],
        })

        start_json = await api_json(
            api,
            "https://api.qianwen.com/assistant/api/record/start?c=tongyi-web",
            {
                "taskType": "local",
                "tingwuRequest": {
                    "fileLink": token["getLink"],
                    "transId": token["genRecordId"],
                    "fileSize": stats.st_size,
                },
                "bizTerminal": "web",
                "dirIdStr": "",
            },
        )
        log(f"started batchId={start_json['data']['batchId']}")

        # 打卡点 2：record/start 已提交，进入轮询阶段
        _checkpoint("transcribing", {"batch_id": start_json["data"]["batchId"]})

        completed_record = await poll_until_done(api, token["genRecordId"])
        log(f"record completed with status={completed_record['recordStatus']}")

        await api_json(
            api,
            "https://api.qianwen.com/assistant/api/record/read?c=tongyi-web",
            {"recordIds": [token["recordId"]]},
        )

        # 打卡点 3：进入导出阶段
        _checkpoint("exporting")

        if export_gate is None:
            export_url = await export_file(api, token["genRecordId"], export_config)
        else:
            async with export_gate:
                export_url = await export_file(api, token["genRecordId"], export_config)

        # 打卡点 4：拿到 export_url，准备下载到本地
        _checkpoint("downloading", {"export_url": export_url})

        run_stamp = now_stamp()

        resolved_title = title or _get_video_title_from_db(input_path)

        export_out = build_export_output_path(
            input_path=input_path,
            output_dir=output_dir,
            export_config=export_config,
            run_stamp=run_stamp,
            title=resolved_title,
        )

        ensure_dir(output_dir)
        await download_file(export_url, export_out)

        log(f"{export_config.label} saved: {export_out}")

        if load_config().save_debug_json:
            headers = transcript_headers(token["genRecordId"])
            transcript_json = await api_json(
                api,
                "https://audio-api.qianwen.com/api/trans/getTransResult?c=tongyi-web",
                {
                    "action": "getTransResult",
                    "version": "1.0",
                    "transId": token["genRecordId"],
                },
                headers,
            )
            doc_edit_json = await api_json(
                api,
                "https://api.qianwen.com/api/doc/getTransDocEdit?c=tongyi-web",
                {
                    "action": "getTransDocEdit",
                    "version": "1.0",
                    "transId": token["genRecordId"],
                },
                headers,
            )
            output_base = input_path.stem
            debug_artifacts = save_debug_artifacts(
                output_dir=output_dir,
                output_base=output_base,
                run_stamp=run_stamp,
                transcript_json=transcript_json,
                doc_edit_json=doc_edit_json,
            )
            log(f"transcript saved: {debug_artifacts.transcript_path}")
            log(f"doc edit saved: {debug_artifacts.doc_edit_path}")

        deleted = False
        if should_delete:
            deleted = await delete_record(api, [token["recordId"]])
            log(f"delete status: {'success' if deleted else 'failed'}")

        quota_after = await get_quota_snapshot(
            auth_state_path=auth_state_path,
            account_id=account_id,
            cookie_string=cookie_string,
        )
        record_flow_quota_usage(
            account_id=account_id,
            before_snapshot=quota_before,
            after_snapshot=quota_after,
            log=log,
        )
        return FlowResult(
            record_id=token["recordId"],
            gen_record_id=token["genRecordId"],
            export_path=export_out,
            remote_deleted=deleted,
        )

    async def _try_resume_export_only() -> FlowResult | None:
        """Step 13a 续传分支：已有 export_url 时直接 download，跳过所有 Qwen API。

        命中条件：resume_state 存在且有 export_url。
        失败时返回 None，由外层走完整 flow（保险机制：任何续传异常都不影响业务）。
        """
        if resume_state is None or not resume_state.export_url:
            return None
        try:
            log(f"resume[export_url]: download only, gen_record_id={resume_state.gen_record_id}")
            run_stamp = now_stamp()
            resolved_title = title or _get_video_title_from_db(input_path)
            export_out = build_export_output_path(
                input_path=input_path,
                output_dir=output_dir,
                export_config=export_config,
                run_stamp=run_stamp,
                title=resolved_title,
            )
            ensure_dir(output_dir)
            await download_file(resume_state.export_url, export_out)
            log(f"{export_config.label} resumed: {export_out}")
            # 续传分支不重新打 stage（已是 downloading），但成功后由 orchestrator mark_saved
            return FlowResult(
                record_id=resume_state.record_id or "",
                gen_record_id=resume_state.gen_record_id or "",
                export_path=export_out,
                remote_deleted=False,
            )
        except Exception as exc:  # noqa: BLE001  续传失败一律 fallback 到完整 flow
            logger.warning(
                f"resume[export_url] 失败，回退到完整 flow: {exc}",
                exc_info=True,
            )
            # 让 orchestrator 知道这次续传未生效（stage 已是 downloading，回退到 queued
            # 才能在完整 flow 中重新被 _checkpoint 推进）
            if run_id:
                try:
                    from media_tools.repositories.transcribe_run_repository import TranscribeRunRepository
                    TranscribeRunRepository.update_stage(run_id, "queued")
                except Exception:  # noqa: BLE001
                    logger.debug("重置 stage 失败，但不影响 fallback 流程", exc_info=True)
            return None

    async def _try_resume_from_gen_record(api: Any) -> FlowResult | None:
        """Step 13b 续传分支：已有 gen_record_id 时跳过 token/upload/heartbeat/start。

        命中条件：resume_state 有 gen_record_id + record_id 但没有 export_url。
        从 poll_until_done 继续 -> export_file -> download_file。

        风险点：Qwen API 的可重入语义未经实测保证。任何异常都会让 stage 回退
        到 queued 并由完整 flow 接管，确保业务永远跑得通（即便代价是重新上传）。
        """
        if resume_state is None or not resume_state.gen_record_id or not resume_state.record_id:
            return None
        if resume_state.export_url:
            # 应当已被 _try_resume_export_only 处理；走到这里说明那一步失败重置了，
            # 此时 resume_state 仍是入参的旧值，但 stage 已被重置成 queued
            # —— 我们也跳过 gen_record_id 续传，让完整 flow 接管
            return None

        try:
            log(
                f"resume[gen_record_id]: skip upload, "
                f"gen_record_id={resume_state.gen_record_id} record_id={resume_state.record_id}"
            )

            completed_record = await poll_until_done(api, resume_state.gen_record_id)
            log(f"resumed record completed with status={completed_record['recordStatus']}")

            # record/read 是幂等性最难判断的一步，但失败也只影响"已读"标记
            try:
                await api_json(
                    api,
                    "https://api.qianwen.com/assistant/api/record/read?c=tongyi-web",
                    {"recordIds": [resume_state.record_id]},
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug(f"resume: record/read 失败但不影响后续: {exc}")

            _checkpoint("exporting")

            if export_gate is None:
                export_url = await export_file(api, resume_state.gen_record_id, export_config)
            else:
                async with export_gate:
                    export_url = await export_file(api, resume_state.gen_record_id, export_config)

            _checkpoint("downloading", {"export_url": export_url})

            run_stamp = now_stamp()
            resolved_title = title or _get_video_title_from_db(input_path)
            export_out = build_export_output_path(
                input_path=input_path,
                output_dir=output_dir,
                export_config=export_config,
                run_stamp=run_stamp,
                title=resolved_title,
            )
            ensure_dir(output_dir)
            await download_file(export_url, export_out)
            log(f"{export_config.label} resumed: {export_out}")

            return FlowResult(
                record_id=resume_state.record_id,
                gen_record_id=resume_state.gen_record_id,
                export_path=export_out,
                remote_deleted=False,
            )
        except Exception as exc:  # noqa: BLE001  续传失败一律 fallback
            logger.warning(
                f"resume[gen_record_id] 失败，回退到完整 flow: {exc}",
                exc_info=True,
            )
            if run_id:
                try:
                    from media_tools.repositories.transcribe_run_repository import TranscribeRunRepository
                    TranscribeRunRepository.update_stage(run_id, "queued")
                except Exception:  # noqa: BLE001
                    logger.debug("重置 stage 失败，但不影响 fallback 流程", exc_info=True)
            return None

    # 续传 fast-path：在调用 Qwen API 之前尝试，命中则零额度成本完成
    resumed = await _try_resume_export_only()
    if resumed is not None:
        return resumed

    # 如果调用方提供了共享 API context，直接使用（不重新解析 token）
    if shared_api is not None:
        # gen_record_id 续传需要 api，命中则跳过上传节省额度；失败 fallback 到完整 flow
        from_gen = await _try_resume_from_gen_record(shared_api)
        if from_gen is not None:
            return from_gen
        return await _do_flow(shared_api)

    resolved_cookie = cookie_string.strip() or resolve_qwen_cookie_string(
        auth_state_path=auth_state_path,
        account_id=account_id,
    )
    api = RequestsApiContext(cookie_string=resolved_cookie)
    try:
        from_gen = await _try_resume_from_gen_record(api)
        if from_gen is not None:
            return from_gen
        return await _do_flow(api)
    finally:
        await api.dispose()


def _make_flow_logger(file_name: str):
    def log(message: str) -> None:
        logger.info(f"[{file_name}] {message}")

    return log


def _make_upload_progress_logger(log):
    last_bucket = -1

    def handle_event(event: dict[str, Any]) -> None:
        nonlocal last_bucket
        event_type = event.get("type")
        if event_type == "direct-upload-complete":
            log("direct presigned upload completed")
        elif event_type == "direct-upload-failed":
            error = event.get("error")
            if event.get("mode") == "auto":
                log(f"direct upload failed, falling back to multipart: {error}")
            else:
                log(f"direct upload failed: {error}")
        elif event_type == "multipart-started":
            log(f"uploadId: {event.get('uploadId')}")
        elif event_type == "part-uploaded":
            part_number = int(event.get("partNumber") or 0)
            total_parts = int(event.get("totalParts") or 0)
            if total_parts <= 0:
                return
            percent = max(1, round(part_number * 100 / total_parts))
            bucket = min(10, percent // 10)
            should_log = part_number == 1 or part_number == total_parts or bucket > last_bucket
            if should_log:
                last_bucket = bucket
                log(f"upload progress: {part_number}/{total_parts} ({percent}%)")
        elif event_type == "multipart-complete":
            log("multipart upload completed")

    return handle_event
