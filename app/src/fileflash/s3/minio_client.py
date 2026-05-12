from __future__ import annotations

import asyncio
import hashlib
import io
import logging
from dataclasses import dataclass
from typing import Iterable

from collections.abc import AsyncIterator

from minio import Minio
from minio.commonconfig import ComposeSource
from minio.deleteobjects import DeleteObject
from minio.error import S3Error

from ..core.settings import Settings

logger = logging.getLogger(__name__)
AUTH_ERROR_CODES = frozenset({"SignatureDoesNotMatch", "InvalidAccessKeyId", "AccessDenied"})


class ObjectStorageError(RuntimeError):
    """Base exception for object storage integration errors."""


class ObjectStorageAuthError(ObjectStorageError):
    """Raised when object storage credentials or signature are invalid."""


class ObjectStorageUnavailableError(ObjectStorageError):
    """Raised when object storage is unavailable for non-auth reasons."""


@dataclass(slots=True)
class ObjectWriteResult:
    etag: str | None
    version_id: str | None


@dataclass(slots=True)
class ObjectStat:
    size: int
    etag: str | None
    version_id: str | None
    content_type: str | None


class MinioObjectStorageClient:
    def __init__(
        self,
        *,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        secure: bool,
        region: str | None,
    ) -> None:
        self.bucket_name = bucket_name
        self.region = region
        self._client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
            region=region,
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> "MinioObjectStorageClient":
        return cls(
            endpoint=settings.object_storage_endpoint,
            access_key=settings.object_storage_access_key,
            secret_key=settings.object_storage_secret_key,
            bucket_name=settings.object_storage_bucket,
            secure=settings.object_storage_secure,
            region=settings.object_storage_region,
        )

    async def ensure_bucket(self) -> None:
        def _run() -> None:
            try:
                if self._client.bucket_exists(self.bucket_name):
                    return
                self._client.make_bucket(self.bucket_name, location=self.region)
            except S3Error as exc:
                if exc.code in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
                    return
                raise self._classify_s3_error(exc) from exc
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "Object storage availability check failed for bucket=%s",
                    self.bucket_name,
                )
                raise ObjectStorageUnavailableError("Object storage unavailable") from exc

        await asyncio.to_thread(_run)

    def _classify_s3_error(self, exc: S3Error) -> ObjectStorageError:
        code = exc.code or "UnknownS3Error"
        logger.error(
            "Object storage S3 error bucket=%s code=%s requestId=%s",
            self.bucket_name,
            code,
            getattr(exc, "request_id", None),
        )
        if code in AUTH_ERROR_CODES:
            return ObjectStorageAuthError(f"Object storage authentication failed: {code}")
        return ObjectStorageUnavailableError(f"Object storage unavailable: {code}")

    async def put_bytes(self, *, object_key: str, data: bytes, content_type: str) -> ObjectWriteResult:
        await self.ensure_bucket()

        def _run() -> ObjectWriteResult:
            result = self._client.put_object(
                self.bucket_name,
                object_key,
                io.BytesIO(data),
                len(data),
                content_type=content_type,
            )
            return ObjectWriteResult(etag=result.etag, version_id=result.version_id)

        return await asyncio.to_thread(_run)

    async def compose_object(self, *, object_key: str, source_keys: list[str]) -> ObjectWriteResult:
        await self.ensure_bucket()

        def _run() -> ObjectWriteResult:
            sources = [ComposeSource(self.bucket_name, source_key) for source_key in source_keys]
            result = self._client.compose_object(self.bucket_name, object_key, sources)
            return ObjectWriteResult(etag=result.etag, version_id=result.version_id)

        return await asyncio.to_thread(_run)

    async def stat_object(self, *, object_key: str) -> ObjectStat:
        def _run() -> ObjectStat:
            stat = self._client.stat_object(self.bucket_name, object_key)
            return ObjectStat(
                size=stat.size,
                etag=getattr(stat, "etag", None),
                version_id=getattr(stat, "version_id", None),
                content_type=getattr(stat, "content_type", None),
            )

        return await asyncio.to_thread(_run)

    async def remove_object(self, *, object_key: str) -> None:
        def _run() -> None:
            self._client.remove_object(self.bucket_name, object_key)

        await asyncio.to_thread(_run)

    async def remove_objects(self, *, object_keys: Iterable[str]) -> None:
        keys = [key for key in object_keys if key]
        if not keys:
            return

        def _run() -> None:
            errors = list(
                self._client.remove_objects(
                    self.bucket_name,
                    (DeleteObject(key) for key in keys),
                )
            )
            if errors:
                error_text = ", ".join(f"{error.object_name}:{error.code}" for error in errors)
                raise RuntimeError(f"Failed to remove objects: {error_text}")

        await asyncio.to_thread(_run)

    async def compute_object_hash(self, *, object_key: str, algorithm: str) -> str:
        def _run() -> str:
            hasher = hashlib.new(algorithm)
            response = self._client.get_object(self.bucket_name, object_key)
            try:
                for chunk in response.stream(1024 * 1024):
                    hasher.update(chunk)
            finally:
                response.close()
                response.release_conn()
            return hasher.hexdigest()

        return await asyncio.to_thread(_run)

    async def iter_object(self, *, object_key: str, chunk_size: int = 1024 * 1024) -> AsyncIterator[bytes]:
        await self.ensure_bucket()

        response = await asyncio.to_thread(self._client.get_object, self.bucket_name, object_key)
        try:
            while True:
                chunk = await asyncio.to_thread(response.read, chunk_size)
                if not chunk:
                    break
                yield chunk
        finally:
            await asyncio.to_thread(response.close)
            await asyncio.to_thread(response.release_conn)

    async def iter_object_range(
        self,
        *,
        object_key: str,
        start: int,
        end: int,
        chunk_size: int = 1024 * 1024,
    ) -> AsyncIterator[bytes]:
        await self.ensure_bucket()

        if start < 0 or end < start:
            raise ValueError("Invalid byte range")

        length = end - start + 1
        response = await asyncio.to_thread(
            self._client.get_object,
            self.bucket_name,
            object_key,
            start,
            length,
        )
        remaining = length
        try:
            while remaining > 0:
                read_size = min(chunk_size, remaining)
                chunk = await asyncio.to_thread(response.read, read_size)
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk
        finally:
            await asyncio.to_thread(response.close)
            await asyncio.to_thread(response.release_conn)
