from pydantic import BaseModel, field_validator
from typing import List


class PipelineRequest(BaseModel):
    url: str
    max_counts: int = 5
    auto_delete: bool = True


class BatchPipelineRequest(BaseModel):
    video_urls: List[str]
    auto_delete: bool = True

    @field_validator("video_urls")
    @classmethod
    def limit_batch_size(cls, v):
        if len(v) > 200:
            raise ValueError("单次批量操作最多 200 条")
        return v


class DownloadBatchRequest(BaseModel):
    video_urls: List[str]

    @field_validator("video_urls")
    @classmethod
    def limit_batch_size(cls, v):
        if len(v) > 200:
            raise ValueError("单次批量操作最多 200 条")
        return v


class CreatorDownloadRequest(BaseModel):
    uid: str
    mode: str = "incremental"
    batch_size: int | None = None


class FullSyncRequest(BaseModel):
    mode: str = "incremental"
    batch_size: int | None = None


class LocalTranscribeRequest(BaseModel):
    file_paths: List[str]
    delete_after: bool | None = None
    directory_root: str | None = None


class CreatorTranscribeRequest(BaseModel):
    uid: str


class ScanDirectoryRequest(BaseModel):
    directory: str


class RecoverAwemeTranscribeRequest(BaseModel):
    creator_uid: str
    aweme_id: str
    title: str = ""


class CreatorTranscribeCleanupRetryRequest(BaseModel):
    task_id: str
