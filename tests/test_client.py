import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# scripts/ をパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from ravenapi.client import RavenClient


class TestRavenClientIngest:
    @patch("ravenapi.client.requests")
    def test_ingest_201_成功(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"id": 1, "externalId": "uuid-001"}
        mock_requests.post.return_value = mock_resp

        client = RavenClient("http://localhost:3000")
        result = client.ingest(
            file_path="/path/to/image.png",
            name="00001-1234567890",
            positive_tags=["1girl"],
        )

        assert result["id"] == 1
        assert result["externalId"] == "uuid-001"
        mock_requests.post.assert_called_once()

    @patch("ravenapi.client.requests")
    def test_ingest_409_重複(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 409
        mock_resp.json.return_value = {"error": "DUPLICATE_IMPORT"}
        mock_requests.post.return_value = mock_resp

        client = RavenClient("http://localhost:3000")
        result = client.ingest(file_path="/path/to/image.png", name="test")

        assert result["error"] == "DUPLICATE_IMPORT"

    @patch("ravenapi.client.requests")
    def test_ingest_500_エラー(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = Exception("Server Error")
        mock_requests.post.return_value = mock_resp

        client = RavenClient("http://localhost:3000")
        with pytest.raises(Exception, match="Server Error"):
            client.ingest(file_path="/path/to/image.png", name="test")

    @patch("ravenapi.client.requests")
    def test_ingest_ペイロードが正しいこと(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"id": 1, "externalId": "uuid"}
        mock_requests.post.return_value = mock_resp

        client = RavenClient("http://localhost:3000")
        client.ingest(
            file_path="/path/to/image.png",
            name="test-001",
            positive_tags=["1girl", "solo"],
            negative_tags=["low quality"],
            generation_params={"Steps": "20"},
        )

        call_args = mock_requests.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["filePath"] == "/path/to/image.png"
        assert payload["name"] == "test-001"
        assert payload["positiveTags"] == ["1girl", "solo"]
        assert payload["negativeTags"] == ["low quality"]
        assert payload["generationParams"] == {"Steps": "20"}

    @patch("ravenapi.client.requests")
    def test_ingest_オプション省略時はペイロードに含まれないこと(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"id": 1, "externalId": "uuid"}
        mock_requests.post.return_value = mock_resp

        client = RavenClient("http://localhost:3000")
        client.ingest(file_path="/path/to/image.png", name="test")

        call_args = mock_requests.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert "positiveTags" not in payload
        assert "negativeTags" not in payload
        assert "generationParams" not in payload

    @patch("ravenapi.client.requests")
    def test_ingest_URL末尾のスラッシュが除去されること(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"id": 1, "externalId": "uuid"}
        mock_requests.post.return_value = mock_resp

        client = RavenClient("http://localhost:3000/")
        client.ingest(file_path="/path/to/image.png", name="test")

        call_args = mock_requests.post.call_args
        url = call_args.args[0] if call_args.args else call_args[0][0]
        assert url == "http://localhost:3000/api/ingest"


class TestRavenClientHealth:
    @patch("ravenapi.client.requests")
    def test_health_200_成功(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_requests.get.return_value = mock_resp

        client = RavenClient("http://localhost:3000")
        assert client.health() is True

    @patch("ravenapi.client.requests")
    def test_health_接続失敗(self, mock_requests):
        import requests as real_requests
        mock_requests.get.side_effect = real_requests.RequestException("Connection refused")
        mock_requests.RequestException = real_requests.RequestException

        client = RavenClient("http://localhost:3000")
        assert client.health() is False
