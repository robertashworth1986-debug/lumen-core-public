from __future__ import annotations

import importlib.util
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "generate_logo.py"


def load_module():
    spec = importlib.util.spec_from_file_location("generate_logo", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_light_and_dark_logo_variants_render_distinct_backgrounds(tmp_path):
    module = load_module()
    module.OUT = tmp_path

    module.render(256, True, "dark.png", theme="dark")
    module.render(256, True, "light.png", theme="light")

    with Image.open(tmp_path / "dark.png") as dark:
        assert dark.size == (256, 256)
        dark_corner = dark.convert("RGB").getpixel((0, 0))

    with Image.open(tmp_path / "light.png") as light:
        assert light.size == (256, 256)
        light_corner = light.convert("RGB").getpixel((0, 0))

    assert max(dark_corner) < 40
    assert min(light_corner) > 240
    assert dark_corner != light_corner
