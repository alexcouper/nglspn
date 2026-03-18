from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from services.leonardo.django_impl.client import (
    GeneratedImage,
    GenerationResult,
    LeonardoAPIClient,
)


@pytest.fixture
def client():
    return LeonardoAPIClient(api_key="test-key")


def _mock_response(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.raise_for_status.return_value = None
    resp.content = b""
    return resp


class TestCreateGeneration:
    def test_returns_generation_id(self, client):
        mock_resp = _mock_response(json_data={
            "sdGenerationJob": {"generationId": "gen-123"}
        })
        with patch("httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__ = lambda s: s
            mock_client_cls.return_value.__exit__ = lambda s, *a: None
            mock_client_cls.return_value.post.return_value = mock_resp

            result = client.create_generation(
                prompt="test prompt",
                model_id="model-123",
                width=1024,
                height=1024,
            )

        assert result == "gen-123"

    def test_sends_context_image_when_provided(self, client):
        mock_resp = _mock_response(json_data={
            "sdGenerationJob": {"generationId": "gen-456"}
        })
        with patch("httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__ = lambda s: s
            mock_client_cls.return_value.__exit__ = lambda s, *a: None
            mock_client_cls.return_value.post.return_value = mock_resp

            client.create_generation(
                prompt="test",
                model_id="model-123",
                width=1024,
                height=768,
                context_image_id="img-789",
            )

            call_args = mock_client_cls.return_value.post.call_args
            body = call_args.kwargs["json"]
            assert body["contextImages"] == [{"type": "UPLOADED", "id": "img-789"}]


class TestGetGeneration:
    def test_returns_complete_with_images(self, client):
        mock_resp = _mock_response(json_data={
            "generations_by_pk": {
                "status": "COMPLETE",
                "generated_images": [
                    {"id": "img-1", "url": "https://cdn.leonardo.ai/img1.png"},
                    {"id": "img-2", "url": "https://cdn.leonardo.ai/img2.png"},
                ],
            }
        })
        with patch("httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__ = lambda s: s
            mock_client_cls.return_value.__exit__ = lambda s, *a: None
            mock_client_cls.return_value.get.return_value = mock_resp

            result = client.get_generation("gen-123")

        assert result == GenerationResult(
            generation_id="gen-123",
            status="COMPLETE",
            images=[
                GeneratedImage(url="https://cdn.leonardo.ai/img1.png", leonardo_id="img-1"),
                GeneratedImage(url="https://cdn.leonardo.ai/img2.png", leonardo_id="img-2"),
            ],
        )

    def test_returns_pending_with_no_images(self, client):
        mock_resp = _mock_response(json_data={
            "generations_by_pk": {
                "status": "PENDING",
                "generated_images": [],
            }
        })
        with patch("httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__ = lambda s: s
            mock_client_cls.return_value.__exit__ = lambda s, *a: None
            mock_client_cls.return_value.get.return_value = mock_resp

            result = client.get_generation("gen-123")

        assert result.status == "PENDING"
        assert result.images == []


class TestPollUntilComplete:
    def test_polls_until_complete(self, client):
        pending = GenerationResult("gen-1", "PENDING", [])
        complete = GenerationResult(
            "gen-1",
            "COMPLETE",
            [GeneratedImage("https://cdn.leonardo.ai/img.png", "img-1")],
        )
        call_count = 0

        def mock_get(gen_id):
            nonlocal call_count
            call_count += 1
            return complete if call_count >= 2 else pending

        with patch.object(client, "get_generation", side_effect=mock_get):
            with patch("services.leonardo.django_impl.client.time.sleep"):
                result = client.poll_until_complete("gen-1")

        assert result.status == "COMPLETE"
        assert len(result.images) == 1

    def test_returns_failed_status(self, client):
        failed = GenerationResult("gen-1", "FAILED", [])
        with patch.object(client, "get_generation", return_value=failed):
            result = client.poll_until_complete("gen-1")

        assert result.status == "FAILED"
