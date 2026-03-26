import requests

TIMEOUT = 10  # seconds


class RavenClient:
    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip("/")

    def health(self) -> bool:
        """Raven サーバーの起動状態を確認"""
        try:
            resp = requests.get(f"{self.server_url}/api/health", timeout=TIMEOUT)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def ingest(
        self,
        file_path: str,
        name: str,
        positive_tags: list[str] | None = None,
        negative_tags: list[str] | None = None,
        generation_params: dict[str, str] | None = None,
        annotation: str | None = None,
    ) -> dict:
        """画像を Raven に送信"""
        payload = {
            "filePath": file_path,
            "name": name,
        }
        if positive_tags:
            payload["positiveTags"] = positive_tags
        if negative_tags:
            payload["negativeTags"] = negative_tags
        if generation_params:
            payload["generationParams"] = generation_params
        if annotation:
            payload["annotation"] = annotation

        resp = requests.post(
            f"{self.server_url}/api/ingest",
            json=payload,
            timeout=TIMEOUT,
        )

        if resp.status_code == 201:
            print(f"[Raven] Image sent: {name}")
            return resp.json()
        elif resp.status_code == 409:
            print(f"[Raven] Image already exists: {name}")
            return resp.json()
        else:
            resp.raise_for_status()
