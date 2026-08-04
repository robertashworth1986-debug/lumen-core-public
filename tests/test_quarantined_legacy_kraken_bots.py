import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(filename: str):
    path = ROOT / "code" / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module, path


def test_legacy_kraken_bots_are_quarantined_without_key_or_order_code(capsys):
    for filename in ("micro_position_kraken_bot.py", "kraken_swing_hunter.py"):
        module, path = load_module(filename)
        assert module.main() == 2
        text = path.read_text(encoding="utf-8")
        assert "luma_live_keys.env" not in text
        assert "AddOrder" not in text
        assert "requests." not in text

    output = capsys.readouterr().out
    assert output.count("QUARANTINED_LEGACY_LIVE_BOT") == 2
