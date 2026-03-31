import sys
import os
import types
from unittest.mock import MagicMock, patch

import pytest

# SD WebUI の modules をモック化してから import する
mock_modules = types.ModuleType("modules")
mock_paths = types.ModuleType("modules.paths")
mock_paths.script_path = "/fake/webui"
mock_callbacks = types.ModuleType("modules.script_callbacks")
mock_callbacks.on_image_saved = MagicMock()
mock_callbacks.on_ui_settings = MagicMock()
mock_callbacks.ImageSaveParams = type("ImageSaveParams", (), {})
mock_shared = types.ModuleType("modules.shared")
mock_shared.opts = MagicMock()
mock_shared.OptionInfo = MagicMock()

sys.modules["modules"] = mock_modules
sys.modules["modules.paths"] = mock_paths
sys.modules["modules.script_callbacks"] = mock_callbacks
sys.modules["modules.shared"] = mock_shared
mock_modules.paths = mock_paths
mock_modules.script_callbacks = mock_callbacks
mock_modules.shared = mock_shared

# scripts/ をパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

# モック注入後にインポート
import importlib
raven_pnginfo = importlib.import_module("raven-pnginfo")


class TestPromptToTags:
    def test_通常のプロンプト(self):
        result = raven_pnginfo.prompt_to_tags("1girl, solo, long hair")
        assert result == ["1girl", "solo", "long hair"]

    def test_空文字列(self):
        assert raven_pnginfo.prompt_to_tags("") == []

    def test_None(self):
        assert raven_pnginfo.prompt_to_tags(None) == []

    def test_空白のみのタグ(self):
        result = raven_pnginfo.prompt_to_tags("a, , b")
        assert result == ["a", "b"]

    def test_重み付き構文(self):
        result = raven_pnginfo.prompt_to_tags("(1girl:1.2), solo")
        assert result == ["(1girl:1.2)", "solo"]

    def test_前後空白(self):
        result = raven_pnginfo.prompt_to_tags(" 1girl , solo ")
        assert result == ["1girl", "solo"]


class TestToWslPath:
    def test_Windowsパスを変換(self):
        assert raven_pnginfo.to_wsl_path(r"D:\Apps\outputs\image.png") == "/mnt/d/Apps/outputs/image.png"

    def test_大文字ドライブレターを小文字に変換(self):
        assert raven_pnginfo.to_wsl_path(r"C:\Users\test.png") == "/mnt/c/Users/test.png"

    def test_スラッシュ区切りのWindowsパス(self):
        assert raven_pnginfo.to_wsl_path("D:/Apps/outputs/image.png") == "/mnt/d/Apps/outputs/image.png"

    def test_Linuxパスはそのまま(self):
        assert raven_pnginfo.to_wsl_path("/home/user/image.png") == "/home/user/image.png"

    def test_相対パスはそのまま(self):
        assert raven_pnginfo.to_wsl_path("outputs/image.png") == "outputs/image.png"


class MockProcessing:
    def __init__(self, **kwargs):
        self.steps = kwargs.get("steps", 20)
        self.sampler_name = kwargs.get("sampler_name", "Euler a")
        self.cfg_scale = kwargs.get("cfg_scale", 7)
        self.seed = kwargs.get("seed", 1234567890)
        self.width = kwargs.get("width", 512)
        self.height = kwargs.get("height", 768)
        self.denoising_strength = kwargs.get("denoising_strength", None)
        self.enable_hr = kwargs.get("enable_hr", False)
        self.hr_scale = kwargs.get("hr_scale", None)
        self.hr_second_pass_steps = kwargs.get("hr_second_pass_steps", None)
        self.hr_upscaler = kwargs.get("hr_upscaler", None)
        self.subseed_strength = kwargs.get("subseed_strength", 0)
        self.subseed = kwargs.get("subseed", 0)
        if "scheduler" in kwargs:
            self.scheduler = kwargs["scheduler"]


class TestCollectGenerationParams:
    def test_基本パラメータ(self):
        p = MockProcessing()
        mock_shared.opts.sd_model_checkpoint = "animagine-xl-3.1"
        mock_shared.opts.CLIP_stop_at_last_layers = 1

        params = raven_pnginfo.collect_generation_params(p)

        assert params["Steps"] == "20"
        assert params["Sampler"] == "Euler a"
        assert params["CFG scale"] == "7"
        assert params["Seed"] == "1234567890"
        assert params["Size"] == "512x768"
        assert params["Model"] == "animagine-xl-3.1"

    def test_オプションパラメータが_None_なら含まれないこと(self):
        p = MockProcessing(denoising_strength=None)
        mock_shared.opts.sd_model_checkpoint = None
        mock_shared.opts.CLIP_stop_at_last_layers = 1

        params = raven_pnginfo.collect_generation_params(p)

        assert "Denoising strength" not in params
        assert "Model" not in params

    def test_Hires有効時(self):
        p = MockProcessing(
            enable_hr=True,
            hr_scale=2.0,
            hr_second_pass_steps=10,
            hr_upscaler="Latent",
        )
        mock_shared.opts.sd_model_checkpoint = None
        mock_shared.opts.CLIP_stop_at_last_layers = 1

        params = raven_pnginfo.collect_generation_params(p)

        assert params["Hires upscale"] == "2.0"
        assert params["Hires steps"] == "10"
        assert params["Hires upscaler"] == "Latent"

    def test_属性欠損(self):
        """属性が存在しない場合に例外にならないこと"""
        p = object()  # 属性が一切ない
        mock_shared.opts.sd_model_checkpoint = None
        mock_shared.opts.CLIP_stop_at_last_layers = 1

        params = raven_pnginfo.collect_generation_params(p)

        # 例外が発生せず、空 dict が返ること
        assert isinstance(params, dict)

    def test_Schedule_type(self):
        p = MockProcessing(scheduler="Karras")
        mock_shared.opts.sd_model_checkpoint = None
        mock_shared.opts.CLIP_stop_at_last_layers = 1

        params = raven_pnginfo.collect_generation_params(p)

        assert params["Schedule type"] == "Karras"


class TestOnImageSaved:
    def test_有効時に送信されること(self):
        mock_shared.opts.enable_raven_integration = True
        mock_shared.opts.raven_server_url = "http://localhost:3000"
        mock_shared.opts.raven_api_token = "test-token"
        mock_shared.opts.sd_model_checkpoint = "animagine-xl-3.1"
        mock_shared.opts.CLIP_stop_at_last_layers = 1

        mock_params = MagicMock()
        mock_params.filename = "outputs/txt2img/00001-123.png"
        mock_params.p = MockProcessing(
            steps=20,
            sampler_name="Euler a",
            cfg_scale=7,
            seed=123,
            width=512,
            height=768,
        )
        mock_params.p.prompt = "1girl, solo"
        mock_params.p.negative_prompt = "low quality"
        mock_params.pnginfo = {"parameters": "1girl, solo\nSteps: 20, Sampler: Euler a"}

        mock_client = MagicMock()
        with patch.object(raven_pnginfo, "RavenClient", return_value=mock_client) as MockClient:
            raven_pnginfo.on_image_saved(mock_params)

            MockClient.assert_called_once_with("http://localhost:3000", api_token="test-token")
            mock_client.ingest.assert_called_once()
            call_kwargs = mock_client.ingest.call_args.kwargs
            assert call_kwargs["name"] == "00001-123"
            assert "1girl" in call_kwargs["positive_tags"]
            assert call_kwargs["annotation"] == "1girl, solo\nSteps: 20, Sampler: Euler a"

    def test_トークン空文字時はNoneが渡されること(self):
        mock_shared.opts.enable_raven_integration = True
        mock_shared.opts.raven_server_url = "http://localhost:3000"
        mock_shared.opts.raven_api_token = ""
        mock_shared.opts.sd_model_checkpoint = "animagine-xl-3.1"
        mock_shared.opts.CLIP_stop_at_last_layers = 1

        mock_params = MagicMock()
        mock_params.filename = "outputs/txt2img/00001-123.png"
        mock_params.p = MockProcessing()
        mock_params.p.prompt = "1girl"
        mock_params.p.negative_prompt = ""
        mock_params.pnginfo = {"parameters": "1girl"}

        mock_client = MagicMock()
        with patch.object(raven_pnginfo, "RavenClient", return_value=mock_client) as MockClient:
            raven_pnginfo.on_image_saved(mock_params)

            MockClient.assert_called_once_with("http://localhost:3000", api_token=None)

    def test_無効時に送信されないこと(self):
        mock_shared.opts.enable_raven_integration = False

        mock_params = MagicMock()

        with patch.object(raven_pnginfo, "RavenClient") as MockClient:
            raven_pnginfo.on_image_saved(mock_params)
            MockClient.assert_not_called()

    def test_APIエラー時に画像生成を中断しないこと(self):
        mock_shared.opts.enable_raven_integration = True
        mock_shared.opts.raven_server_url = "http://localhost:3000"

        mock_params = MagicMock()
        mock_params.filename = "outputs/txt2img/00001-123.png"
        mock_params.p.prompt = "1girl"
        mock_params.p.negative_prompt = ""

        mock_client = MagicMock()
        mock_client.ingest.side_effect = Exception("Connection refused")
        with patch.object(raven_pnginfo, "RavenClient", return_value=mock_client):
            # 例外が発生しないことを確認
            raven_pnginfo.on_image_saved(mock_params)
