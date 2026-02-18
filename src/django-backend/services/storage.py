"""S3-compatible storage service for Scaleway Object Storage."""

import uuid
from typing import Any

import boto3
from botocore.config import Config
from django.conf import settings


class StorageService:
    """Service for interacting with S3-compatible object storage."""

    def __init__(self) -> None:
        self._client: Any = None

    @property
    def client(self) -> Any:
        """Lazy-load the S3 client."""
        if self._client is None:
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


# Singleton instance
storage_service = StorageService()
