"""Storage service with S3 and local filesystem backends."""

import logging
import uuid
from pathlib import Path
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


class StorageService:
    """Service for interacting with S3-compatible object storage."""

    def __init__(self) -> None:
        self._client: Any = None

    @property
    def client(self) -> Any:
        """Lazy-load the S3 client."""
        if self._client is None:
            import boto3  # noqa: PLC0415
            from botocore.config import Config  # noqa: PLC0415

            self._client = boto3.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT_URL,
                region_name=settings.S3_REGION,
                aws_access_key_id=settings.SCW_ACCESS_KEY,
                aws_secret_access_key=settings.SCW_SECRET_KEY,
                config=Config(signature_version="s3v4"),
            )
        return self._client

    def generate_upload_key(self, project_id: str, filename: str) -> str:
        """Generate a unique storage key for an upload.

        Format: projects/{project_id}/{uuid}/{filename}
        """
        unique_id = uuid.uuid4().hex[:12]
        # Sanitize filename - keep only alphanumeric, dots, hyphens, underscores
        safe_filename = "".join(c for c in filename if c.isalnum() or c in ".-_")
        if not safe_filename:
            safe_filename = "image"
        return f"projects/{project_id}/{unique_id}/{safe_filename}"

    def generate_presigned_upload_url(
        self,
        key: str,
        content_type: str,
        expires_in: int = 3600,
    ) -> dict:
        """Generate a presigned URL for uploading an object via PUT."""
        url = self.client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.S3_BUCKET_NAME,
                "Key": key,
                "ContentType": content_type,
                "ACL": "public-read",
            },
            ExpiresIn=expires_in,
            HttpMethod="PUT",
        )
        return {
            "upload_url": url,
            "method": "PUT",
            "headers": {
                "Content-Type": content_type,
                "x-amz-acl": "public-read",
            },
        }

    def download_object(self, key: str) -> bytes:
        """Download an object from storage and return its contents."""
        response = self.client.get_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=key,
        )
        return response["Body"].read()

    def upload_object(
        self,
        key: str,
        data: bytes,
        content_type: str,
        acl: str = "public-read",
    ) -> None:
        """Upload bytes to storage."""
        self.client.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=key,
            Body=data,
            ContentType=content_type,
            ACL=acl,
        )

    def delete_object(self, key: str) -> None:
        """Delete an object from storage."""
        self.client.delete_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=key,
        )

    def object_exists(self, key: str) -> bool:
        """Check if an object exists in storage."""
        try:
            self.client.head_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=key,
            )
        except self.client.exceptions.ClientError:
            return False
        else:
            return True


class LocalStorageService:
    """Filesystem-based storage for local development."""

    def __init__(self) -> None:
        self._base_dir = Path(settings.BASE_DIR) / "media" / "storage"
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def generate_upload_key(self, project_id: str, filename: str) -> str:
        unique_id = uuid.uuid4().hex[:12]
        safe_filename = "".join(c for c in filename if c.isalnum() or c in ".-_")
        if not safe_filename:
            safe_filename = "image"
        return f"projects/{project_id}/{unique_id}/{safe_filename}"

    def generate_presigned_upload_url(
        self,
        key: str,
        content_type: str,
        expires_in: int = 3600,
    ) -> dict:
        """For local dev, return a URL pointing to the Django media upload endpoint."""
        # Read the actual port from .backend-port if available
        port_file = Path(settings.BASE_DIR).parent.parent / ".backend-port"
        port = "8000"
        if port_file.exists():
            port = port_file.read_text().strip()
        return {
            "upload_url": f"http://localhost:{port}/media/upload/{key}",
            "method": "PUT",
            "headers": {
                "Content-Type": content_type,
            },
        }

    def download_object(self, key: str) -> bytes:
        file_path = self._base_dir / key
        return file_path.read_bytes()

    def upload_object(
        self,
        key: str,
        data: bytes,
        content_type: str,
        acl: str = "public-read",
    ) -> None:
        file_path = self._base_dir / key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(data)
        logger.info("Local storage: saved %d bytes to %s", len(data), file_path)

    def delete_object(self, key: str) -> None:
        file_path = self._base_dir / key
        if file_path.exists():
            file_path.unlink()

    def object_exists(self, key: str) -> bool:
        return (self._base_dir / key).exists()


class _LazyStorageService:
    """Lazy proxy that creates the real storage service on first access."""

    def __init__(self) -> None:
        self._instance: StorageService | LocalStorageService | None = None

    def _get_instance(self) -> StorageService | LocalStorageService:
        if self._instance is None:
            backend = getattr(settings, "STORAGE_BACKEND", "s3")
            self._instance = (
                LocalStorageService() if backend == "local" else StorageService()
            )
        return self._instance

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get_instance(), name)


# Singleton instance — lazily creates the real backend on first use
storage_service: Any = _LazyStorageService()
