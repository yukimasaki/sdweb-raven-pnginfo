import os
import sys

from modules import paths, script_callbacks, shared

# SD WebUI はスクリプトを scripts/ 内から実行するため、
# ravenapi パッケージを確実に import できるようにする
_scripts_dir = os.path.dirname(os.path.abspath(__file__))
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from ravenapi.client import RavenClient

path_root = paths.script_path


def on_ui_settings():
    """Settings 画面に Raven 連携の設定を追加"""

    section = ("raven_pnginfo", "Raven Pnginfo")

    shared.opts.add_option(
        "enable_raven_integration",
        shared.OptionInfo(
            False,
            "Enable Raven integration (auto-send images to Raven)",
            section=section,
        ),
    )
    shared.opts.add_option(
        "raven_server_url",
        shared.OptionInfo(
            "http://localhost:3000",
            "Raven server URL",
            section=section,
        ),
    )


def prompt_to_tags(prompt: str) -> list[str]:
    """プロンプト文字列をカンマ区切りでタグ配列に分割"""
    if not prompt or prompt.strip() == "":
        return []
    return [tag.strip() for tag in prompt.split(",") if tag.strip()]


def collect_generation_params(p) -> dict[str, str]:
    """生成パラメータを収集"""
    params = {}

    simple_attrs = {
        "Steps": ("steps", str),
        "Sampler": ("sampler_name", str),
        "CFG scale": ("cfg_scale", str),
        "Seed": ("seed", lambda v: str(v) if v is not None else None),
        "Size": (None, lambda _: f"{p.width}x{p.height}"),
        "Denoising strength": ("denoising_strength", lambda v: str(v) if v else None),
    }

    for key, (attr, converter) in simple_attrs.items():
        try:
            val = getattr(p, attr) if attr else None
            result = converter(val)
            if result is not None:
                params[key] = result
        except (AttributeError, TypeError):
            pass

    # Model — shared.opts から取得
    try:
        model = shared.opts.sd_model_checkpoint
        if model:
            params["Model"] = model
    except AttributeError:
        pass

    # Model hash
    try:
        model_hash = getattr(p, "sd_model_hash", None)
        if model_hash:
            params["Model hash"] = model_hash
    except AttributeError:
        pass

    # Clip skip
    try:
        clip_skip = getattr(p, "clip_skip", shared.opts.CLIP_stop_at_last_layers)
        if clip_skip and clip_skip > 1:
            params["Clip skip"] = str(clip_skip)
    except AttributeError:
        pass

    # Schedule type
    try:
        schedule_type = getattr(p, "scheduler", None)
        if schedule_type:
            params["Schedule type"] = str(schedule_type)
    except AttributeError:
        pass

    # Hires 関連
    try:
        if getattr(p, "enable_hr", False):
            hr_attrs = {
                "Hires upscale": "hr_scale",
                "Hires steps": "hr_second_pass_steps",
                "Hires upscaler": "hr_upscaler",
            }
            for key, attr in hr_attrs.items():
                val = getattr(p, attr, None)
                if val:
                    params[key] = str(val)
    except AttributeError:
        pass

    # Variation seed
    try:
        if getattr(p, "subseed_strength", 0) > 0:
            params["Variation seed"] = str(p.subseed)
            params["Variation seed strength"] = str(p.subseed_strength)
    except AttributeError:
        pass

    return params


def on_image_saved(params: script_callbacks.ImageSaveParams):
    """画像保存時のコールバック"""
    if not shared.opts.enable_raven_integration:
        return

    try:
        # ファイル情報
        full_path = os.path.join(path_root, params.filename)
        filename = os.path.splitext(os.path.basename(full_path))[0]

        # メタデータ収集
        positive_tags = prompt_to_tags(params.p.prompt)
        negative_tags = prompt_to_tags(params.p.negative_prompt)
        generation_params = collect_generation_params(params.p)

        # Raven に送信
        client = RavenClient(shared.opts.raven_server_url)
        client.ingest(
            file_path=full_path,
            name=filename,
            positive_tags=positive_tags,
            negative_tags=negative_tags,
            generation_params=generation_params,
        )
    except Exception as e:
        print(f"[Raven] Failed to send image: {e}")


# コールバック登録
script_callbacks.on_image_saved(on_image_saved)
script_callbacks.on_ui_settings(on_ui_settings)
