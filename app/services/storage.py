"""Where workout photos live.

Local disk is fine for development, but containers lose their disk on redeploy and can't share it
between replicas, so production should set S3_BUCKET. The bucket stays private; readers get
short-lived presigned links instead.
"""

from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.core.config import settings


class PhotoStorage(Protocol):
    def save(self, key: str, data: bytes, content_type: str) -> None: ...

    def delete(self, key: str) -> None: ...

    def url(self, key: str) -> str: ...


class LocalStorage:
    def __init__(self, directory: Path):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    def save(self, key: str, data: bytes, content_type: str) -> None:
        (self.directory / key).write_bytes(data)

    def delete(self, key: str) -> None:
        (self.directory / key).unlink(missing_ok=True)

    def url(self, key: str) -> str:
        return f"/media/{key}"


class S3Storage:
    def __init__(self, bucket: str, region: str | None = None, endpoint_url: str | None = None):
        import boto3

        self.bucket = bucket
        self.client = boto3.client("s3", region_name=region, endpoint_url=endpoint_url)

    def save(self, key: str, data: bytes, content_type: str) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def url(self, key: str) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=settings.s3_url_expire_seconds,
        )


@lru_cache
def get_storage() -> PhotoStorage:
    if settings.s3_bucket:
        return S3Storage(settings.s3_bucket, settings.s3_region, settings.s3_endpoint_url)
    return LocalStorage(settings.upload_dir)
