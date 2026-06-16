"""Config-driven object-storage factory (mirrors ai/ and cache/).

Selecting the backend is a settings change, not a code change. The S3 import is
lazy so boto3 only loads when S3 is actually used — keeping the vendor dependency
off the local-dev import path.
"""
from __future__ import annotations

from app.storage.interface import ObjectStorage
from app.storage.local_fs import LocalFileStorage


def build_storage(settings) -> ObjectStorage:
    backend = (settings.storage_backend or "local").lower()
    if backend == "local":
        return LocalFileStorage(settings.local_storage_dir)
    if backend == "s3":
        from app.storage.s3 import S3Storage  # lazy: boto3 only when needed

        return S3Storage(
            endpoint_url=settings.s3_endpoint_url,
            bucket=settings.s3_bucket,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            region=settings.s3_region,
        )
    raise ValueError(f"unknown storage backend '{backend}' (have: local, s3)")
