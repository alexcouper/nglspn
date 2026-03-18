from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

LEONARDO_BASE_URL = "https://cloud.leonardo.ai/api/rest/v1"

# Model IDs
PHOENIX_MODEL_ID = "de7d3faf-762f-48e0-b3b7-9d0ac3a3fcf3"
FLUX_KONTEXT_MODEL_ID = "28aeddf8-bd19-4803-80fc-79602d1a9989"

POLL_INTERVAL_SECONDS = 2.0
POLL_MAX_WAIT_SECONDS = 120.0


@dataclass
class GeneratedImage:
    url: str
    leonardo_id: str


@dataclass
class GenerationResult:
    generation_id: str
    status: str
    images: list[GeneratedImage]


class LeonardoAPIClient:
    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or getattr(settings, "LEONARDO_API_KEY", "")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def create_generation(
        self,
        *,
        prompt: str,
        model_id: str,
        width: int,
        height: int,
        num_images: int = 1,
        negative_prompt: str = "",
        preset_style: str | None = None,
        alchemy: bool = True,
        context_image_id: str | None = None,
    ) -> str:
        """Create a generation request. Returns the generation ID."""
        body: dict = {
            "prompt": prompt,
            "modelId": model_id,
            "width": width,
            "height": height,
            "num_images": num_images,
            "alchemy": alchemy,
        }
        if negative_prompt:
            body["negative_prompt"] = negative_prompt
        if preset_style:
            body["presetStyle"] = preset_style
        if context_image_id:
            body["contextImages"] = [{"type": "UPLOADED", "id": context_image_id}]

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{LEONARDO_BASE_URL}/generations",
                headers=self._headers(),
                json=body,
            )
            response.raise_for_status()
            data = response.json()

        generation_id = data["sdGenerationJob"]["generationId"]
        logger.info("Leonardo generation created: %s", generation_id)
        return generation_id

    def get_generation(self, generation_id: str) -> GenerationResult:
        """Get the status and results of a generation."""
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{LEONARDO_BASE_URL}/generations/{generation_id}",
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()

        gen = data["generations_by_pk"]
        status = gen.get("status", "PENDING")
        images = (
            [
                GeneratedImage(
                    url=img["url"],
                    leonardo_id=img["id"],
                )
                for img in gen.get("generated_images", [])
            ]
            if status == "COMPLETE"
            else []
        )

        return GenerationResult(
            generation_id=generation_id,
            status=status,
            images=images,
        )

    def poll_until_complete(self, generation_id: str) -> GenerationResult:
        """Poll a generation until it completes or fails."""
        elapsed = 0.0
        while elapsed < POLL_MAX_WAIT_SECONDS:
            result = self.get_generation(generation_id)
            if result.status == "COMPLETE":
                return result
            if result.status == "FAILED":
                return result
            time.sleep(POLL_INTERVAL_SECONDS)
            elapsed += POLL_INTERVAL_SECONDS

        return GenerationResult(
            generation_id=generation_id,
            status="TIMEOUT",
            images=[],
        )

    def upload_init_image(self, image_bytes: bytes, extension: str = "png") -> str:
        """Upload an image to Leonardo for use as a reference. Returns the image ID."""
        with httpx.Client(timeout=30.0) as client:
            # Step 1: Get presigned URL
            response = client.post(
                f"{LEONARDO_BASE_URL}/init-image",
                headers=self._headers(),
                json={"extension": extension},
            )
            response.raise_for_status()
            data = response.json()

            upload_data = data["uploadInitImage"]
            presigned_url = upload_data["url"]
            fields = upload_data["fields"]
            image_id = upload_data["id"]

            # Fields from Leonardo are JSON-encoded
            if isinstance(fields, str):
                fields = json.loads(fields)

            files = {"file": ("image." + extension, image_bytes)}
            response = client.post(
                presigned_url,
                data=fields,
                files=files,
                headers={},  # Don't send auth headers to S3
            )
            response.raise_for_status()

        logger.info("Leonardo init image uploaded: %s", image_id)
        return image_id

    def download_image(self, url: str) -> bytes:
        """Download an image from a Leonardo CDN URL."""
        with httpx.Client(timeout=60.0) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.content
