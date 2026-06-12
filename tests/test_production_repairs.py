from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT / "code" / "ops"))

import grant_application_factory as grant_factory
from grant_submission_kit import build_preflight
from build_symbol_timing_edge_model import Candle, analyze_symbol
from collect_kraken_hourly_history import merge_rows
from ensure_dashboard_command_fabric import ensure_fabric
from assert_runtime_safety import assert_paper_mode


class ProductionRepairTests(unittest.TestCase):
    def test_budget_never_exceeds_ceiling(self) -> None:
        for ceiling in (75_000, 100_000, 200_000, 305_000, 1_100_000):
            budget = grant_factory.render_budget(
                {
                    "ceiling_usd": ceiling,
                    "duration_months": 12,
                },
                {},
            )
            self.assertEqual(budget["total"], ceiling)

    def test_submission_preflight_blocks_placeholders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            required = {
                "application.json": (
                    '{"agency":"Test","program":"Test","deadline_typical":"2099-01-01",'
                    '"current_state":"open","applicant":{"sam_gov_status":"active",'
                    '"sam_gov_verified_utc":"2098-01-01","sam_gov_expiration_date":"2099-12-31"},'
                    '"submission_readiness":{"grants_gov_account_verified":true,'
                    '"aor_authority_verified":true},"eligibility":{"eligible":true},'
                    '"budget":{"ceiling_usd":100000,"total":100000}}'
                ),
                "application.md": "TO_BE_FILLED - unresolved claim\n",
                "technical_volume.md": "ok\n",
                "commercialization_plan.md": "ok\n",
                "cover_letter.md": "ok\n",
                "budget.json": "{}",
                "eligibility_report.json": "{}",
                "evidence_manifest.json": "{}",
                "manifest.sha256.json": "{}",
                "approval_state.json": '{"state":"approved"}',
            }
            for name, content in required.items():
                (run_dir / name).write_text(content, encoding="utf-8")
            preflight = build_preflight("test_grant", run_dir, None)
            self.assertFalse(preflight["ready"])
            self.assertTrue(
                any("TO_BE_FILLED" in blocker for blocker in preflight["blockers"])
            )

    def test_submission_preflight_allows_request_below_maximum_ceiling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            required = {
                "application.json": (
                    '{"agency":"Test","program":"Test","deadline_typical":"2099-01-01",'
                    '"current_state":"open","applicant":{"sam_gov_status":"active",'
                    '"sam_gov_verified_utc":"2098-01-01","sam_gov_expiration_date":"2099-12-31"},'
                    '"submission_readiness":{"grants_gov_account_verified":true,'
                    '"aor_authority_verified":true},"eligibility":{"eligible":true},'
                    '"budget":{"ceiling_usd":150000,"total":125000}}'
                ),
                "application.md": "complete\n",
                "technical_volume.md": "complete\n",
                "commercialization_plan.md": "complete\n",
                "cover_letter.md": "complete\n",
                "budget.json": "{}",
                "eligibility_report.json": "{}",
                "evidence_manifest.json": "{}",
                "manifest.sha256.json": "{}",
                "approval_state.json": '{"state":"approved"}',
            }
            for name, content in required.items():
                (run_dir / name).write_text(content, encoding="utf-8")
            preflight = build_preflight(
                "test_grant",
                run_dir,
                {
                    "deadline_typical": "2099-01-01",
                    "current_state": "open",
                    "source_verified_utc": "2098-01-01",
                    "ceiling_usd": 150000,
                },
            )
            self.assertFalse(
                any("budget total" in blocker for blocker in preflight["blockers"])
            )
            self.assertTrue(
                any("maximum" in warning for warning in preflight["warnings"])
            )

    def test_known_low_hour_is_selected_in_training(self) -> None:
        candles: list[Candle] = []
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        for offset in range(24 * 45):
            ts = start + timedelta(hours=offset)
            close = 100.0
            if ts.hour == 3:
                close = 95.0
            elif ts.hour == 20:
                close = 105.0
            candles.append(
                Candle(
                    ts=ts,
                    open=close,
                    high=close * 1.001,
                    low=close * 0.999,
                    close=close,
                    volume=1000.0,
                )
            )
        args = SimpleNamespace(
            horizon_hours=24,
            roundtrip_cost_bps=10.0,
            daily_extreme_tolerance_bps=20.0,
            train_fraction=0.70,
            prior_strength=20.0,
            min_bucket_samples=5,
            min_weekday_hour_samples=2,
            top_windows=3,
            moonshot_thresholds_pct=[10.0, 20.0],
            moonshot_horizon_hours=48,
        )
        result = analyze_symbol(
            symbol="TEST",
            quote="USD",
            source_file=ROOT / "synthetic.csv",
            candles=candles,
            args=args,
            auxiliary_clusters={},
        )
        selected = [
            row["hour_utc"]
            for row in result["best_buy_windows_train"]
        ]
        self.assertIn(3, selected)
        self.assertFalse(result["execution_authorized"])

    def test_history_merge_is_deduplicated_and_drops_open_candle(self) -> None:
        now_ts = int(datetime.now(timezone.utc).timestamp())
        completed_ts = now_ts - 7200
        open_ts = now_ts
        existing = {
            completed_ts: [
                datetime.fromtimestamp(completed_ts, tz=timezone.utc).isoformat(),
                "1", "1", "1", "1", "1", "1", "1",
            ]
        }
        fetched = [
            [completed_ts, "1", "2", "0.5", "1.5", "1.2", "10", "4"],
            [open_ts, "1.5", "2", "1", "1.8", "1.6", "12", "5"],
        ]
        merged, added = merge_rows(existing, fetched, interval_min=60)
        self.assertEqual(len(merged), 1)
        self.assertEqual(added, 0)
        self.assertEqual(merged[completed_ts][4], "1.5")

    def test_runtime_preflight_fails_closed(self) -> None:
        self.assertEqual(
            assert_paper_mode(
                {
                    "mode": "paper",
                    "allow_live_orders": False,
                    "paper_enabled": True,
                }
            ),
            [],
        )
        failures = assert_paper_mode(
            {
                "mode": "live",
                "allow_live_orders": True,
                "paper_enabled": False,
            }
        )
        self.assertEqual(len(failures), 3)

    def test_spike_hunter_uses_cross_platform_runtime_root(self) -> None:
        source = (ROOT / "code" / "kraken_spike_hunter_live.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('os.environ.get("LUMA_ROOT")', source)
        self.assertNotIn(
            'Path(r"C:\\LumaTrader\\INSTITUTIONAL_STACK_V2")',
            source,
        )

    def test_dashboard_command_fabric_injection_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "mission_control.html"
            page.write_text(
                "<html><head></head><body><main>test</main></body></html>",
                encoding="utf-8",
            )
            self.assertTrue(ensure_fabric(page))
            first = page.read_text(encoding="utf-8")
            self.assertIn("luma_command_fabric.css", first)
            self.assertIn("luma_command_fabric.js", first)
            self.assertFalse(ensure_fabric(page))
            self.assertEqual(first, page.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
