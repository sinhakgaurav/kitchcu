"""Kitchen media storage — MinIO (dev/prod) or local filesystem (tests)."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Protocol

from ckac_common.config import get_settings


class MediaStorage(Protocol):
    def upload(
        self,
        *,
        kitchen_id: str,
        context: str,
        data: bytes,
        content_type: str,
        extension: str,
    ) -> str: ...


class MinioMediaStorage:
    def __init__(self) -> None:
        from minio import Minio

        settings = get_settings()
        self._bucket = settings.minio_bucket
        self._public_url = settings.minio_public_url.rstrip("/")
        self._client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)
        try:
            policy = (
                '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":["*"]},'
                f'"Action":["s3:GetObject"],"Resource":["arn:aws:s3:::{self._bucket}/*"]}}]}}'
            )
            self._client.set_bucket_policy(self._bucket, policy)
        except Exception:
            pass

    def upload(
        self,
        *,
        kitchen_id: str,
        context: str,
        data: bytes,
        content_type: str,
        extension: str,
    ) -> str:
        from io import BytesIO

        safe_context = "".join(c if c.isalnum() or c in "-_" else "-" for c in context)[:40]
        object_key = f"{kitchen_id}/{safe_context}/{uuid.uuid4()}.{extension}"
        self._client.put_object(
            self._bucket,
            object_key,
            BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return f"{self._public_url}/{self._bucket}/{object_key}"


class LocalMediaStorage:
    def __init__(self) -> None:
        settings = get_settings()
        self._root = Path(settings.media_local_dir)
        self._root.mkdir(parents=True, exist_ok=True)

    def upload(
        self,
        *,
        kitchen_id: str,
        context: str,
        data: bytes,
        content_type: str,
        extension: str,
    ) -> str:
        safe_context = "".join(c if c.isalnum() or c in "-_" else "-" for c in context)[:40]
        rel = Path(kitchen_id) / safe_context / f"{uuid.uuid4()}.{extension}"
        dest = self._root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return f"file://{dest.as_posix()}"


_storage: MediaStorage | None = None


def get_media_storage() -> MediaStorage:
    global _storage
    if _storage is None:
        backend = get_settings().media_storage_backend.lower()
        _storage = LocalMediaStorage() if backend == "local" else MinioMediaStorage()
    return _storage


def reset_media_storage() -> None:
    global _storage
    _storage = None
