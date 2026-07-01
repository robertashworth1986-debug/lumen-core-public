from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "ops" / "BUILD_LUMA_VOICE_CONTEXT_CONSOLE.py"
spec = importlib.util.spec_from_file_location("voice_context_builder", MODULE_PATH)
voice = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(voice)


def test_voice_payload_uses_dashboard_safe_sources() -> None:
    payload = voice.build_payload()

    assert payload["schema"] == "luma_voice_context_console_v1"
    assert payload["scope"] == "dashboard_safe_voice_context"
    assert payload["grant_status"]["submitted_by_feed"] == 0
    assert "No live Kraken trading" in "\n".join(payload["hard_boundaries"])
    assert "No secrets" in "\n".join(payload["hard_boundaries"])
    assert payload["trading"]["live_policy"].startswith("No live trades")
    assert "dollar_claim_gate" in payload["sources"]
    assert "geometry_championship_bridge" in payload["sources"]
    assert "Dollar claim gate allows" in payload["narration"]["dollar_claims"]
    assert payload["geometry_championship_bridge"]["kraken_live_execution_allowed"] is False
    assert payload["geometry_championship_bridge"]["branching_benchmark_generated"] is True
    assert payload["geometry_championship_bridge"]["branching_field_validation"] is False
    assert payload["geometry_championship_bridge"]["branching_live_execution_allowed"] is False
    assert "latest generated branching-transport benchmark" in payload["narration"]["geometry"]


def test_goal_prompt_keeps_ambition_inside_evidence_boundaries() -> None:
    prompt = voice.render_goal_prompt()

    assert "proof-driven funding and traction engine" in prompt
    assert "No geometry is sacred until it wins" in prompt
    assert "Do not guarantee funding, profit" in prompt
    assert "Do not expose API keys" in prompt
    assert "Keep Kraken and all trading live execution blocked" in prompt


def test_writer_outputs_voice_console_without_secret_markers(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(voice, "VOICE_JSON", tmp_path / "voice.json")
    monkeypatch.setattr(voice, "VOICE_HTML", tmp_path / "voice.html")
    monkeypatch.setattr(voice, "GOAL_PROMPT_MD", tmp_path / "goal.md")

    payload = voice.build_payload()
    voice.write_outputs(payload)

    saved = json.loads((tmp_path / "voice.json").read_text(encoding="utf-8"))
    html = (tmp_path / "voice.html").read_text(encoding="utf-8")
    prompt = (tmp_path / "goal.md").read_text(encoding="utf-8")

    assert saved["schema"] == "luma_voice_context_console_v1"
    assert "speechSynthesis" in html
    assert "Speak Dollar Gate" in html
    assert "narration.dollar_claims" in html
    assert "LumaJarvis Legendary Long-Arc Goal Prompt" in prompt
    combined = json.dumps(saved) + html + prompt
    assert "sk-proj-" not in combined
    assert "KRAKEN_API_SECRET=" not in combined
