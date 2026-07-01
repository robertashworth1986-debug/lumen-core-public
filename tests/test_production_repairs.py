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
sys.path.insert(0, str(ROOT / "code" / "execution"))

import grant_application_factory as grant_factory
import luma_experience_gateway as gateway
import multi_exchange_paper_ticker as paper_ticker
from grant_submission_kit import build_preflight
from build_symbol_timing_edge_model import Candle, analyze_symbol
from collect_kraken_hourly_history import merge_rows
from ensure_dashboard_command_fabric import ensure_fabric
from assert_runtime_safety import assert_paper_mode
from benchmark_beater import _fib_prox, simulate_vs_benchmark


class ProductionRepairTests(unittest.TestCase):
    def test_gateway_exposes_legacy_dashboard_compatibility_feeds(self) -> None:
        live_status = gateway.live_status_json()
        federal_brief = gateway.federal_brief_json()
        evidence_summary = gateway.evidence_summary_json()
        executor_heartbeat = gateway.executor_heartbeat_json()

        self.assertEqual(
            live_status["schema"],
            "lumencore_live_status_compat_v1",
        )
        self.assertIn("execution_gate", live_status)
        self.assertEqual(
            federal_brief["schema"],
            "lumencore_federal_brief_compat_v1",
        )
        self.assertIn("claim_boundary", federal_brief)
        self.assertEqual(
            evidence_summary["schema"],
            "lumencore_evidence_summary_compat_v1",
        )
        self.assertIn("claim_boundary", evidence_summary)
        self.assertEqual(
            executor_heartbeat["schema"],
            "lumencore_executor_heartbeat_compat_v1",
        )
        self.assertIn("source_meta", executor_heartbeat)

    def test_agent_approval_hub_is_restored_to_public_dashboard_surface(self) -> None:
        hub = ROOT / "dashboard" / "agent_approval_hub.html"
        self.assertTrue(hub.exists())
        text = hub.read_text(encoding="utf-8")
        self.assertIn("LumenCore — Agent Approval Hub", text)
        self.assertIn("/api/agents/queue", text)

    def test_paper_ticker_cycle_ledger_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "paper_ticker.jsonl"
            status = Path(tmp) / "paper_ticker_rotation.json"
            ledger.write_text(
                "".join(
                    f'{{"row": {idx}, "payload": "{("x" * 30)}"}}\n'
                    for idx in range(40)
                ),
                encoding="utf-8",
            )
            before = ledger.stat().st_size
            rotation = paper_ticker.append_bounded_jsonl(
                ledger,
                {"row": "new", "payload": "latest"},
                max_bytes=500,
                tail_bytes=180,
                status_path=status,
            )
            after = ledger.stat().st_size
            text = ledger.read_text(encoding="utf-8")

            self.assertGreater(before, 500)
            self.assertTrue(rotation["rotated"])
            self.assertLess(after, before)
            self.assertIn('"row"', text)
            self.assertIn('"new"', text)
            self.assertTrue(status.exists())

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
                "HEILMEIER_CATECHISM.md": "ok\n",
                "BENCHMARK_BREADTH_ADDENDUM.md": "ok\n",
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
                "HEILMEIER_CATECHISM.md": "complete\n",
                "BENCHMARK_BREADTH_ADDENDUM.md": "complete\n",
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

    def test_released_future_opportunity_is_draftable_not_actionable(self) -> None:
        verified = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        window = grant_factory._program_window_assessment(
            {
                "current_state": "pre_release_released",
                "source_verified_utc": verified,
                "open_date": "2099-06-24",
                "close_date": "2099-07-22",
            }
        )
        self.assertEqual(window["status"], "upcoming")
        self.assertTrue(window["draftable"])
        self.assertFalse(window["actionable"])

    def test_heilmeier_renderer_uses_topic_specific_strategy(self) -> None:
        rendered = grant_factory.render_heilmeier_catechism(
            {
                "topic_area": "Adaptive Sensor Management",
                "duration_months": 6,
                "proposal_strategy": {
                    "title": "SenseDirector",
                    "today": "Allocate four radars under hard constraints.",
                    "metrics": ["Mission-weighted information gain."],
                    "risks": ["Simulation-to-hardware transfer."],
                },
            },
            {"company": {"dba": "Luma"}},
            {"run_utc": "20260613T000000Z"},
        )
        self.assertIn("SenseDirector", rendered)
        self.assertIn("Allocate four radars", rendered)
        self.assertIn("Mission-weighted information gain", rendered)

    def test_dod_preflight_blocks_upcoming_unverified_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            verified = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            app = {
                "agency": "U.S. Navy / NAVSEA",
                "program": "DoD SBIR Phase I",
                "deadline_typical": "2099-07-22",
                "open_date": "2099-06-24",
                "close_date": "2099-07-22",
                "current_state": "pre_release_released",
                "source_verified_utc": verified,
                "funding_cap_verified": False,
                "applicant": {
                    "sam_gov_status": "active",
                    "sam_gov_verified_utc": verified,
                    "sam_gov_expiration_date": "2099-12-31",
                },
                "submission_readiness": {
                    "dsip_account_verified": False,
                    "dod_compliance_verified": False,
                },
                "eligibility": {"eligible": True},
                "budget": {"ceiling_usd": 250000, "total": 250000},
            }
            files = {
                "application.json": __import__("json").dumps(app),
                "application.md": "complete\n",
                "technical_volume.md": "complete\n",
                "commercialization_plan.md": "complete\n",
                "cover_letter.md": "complete\n",
                "HEILMEIER_CATECHISM.md": "complete\n",
                "BENCHMARK_BREADTH_ADDENDUM.md": "complete\n",
                "budget.json": "{}",
                "eligibility_report.json": "{}",
                "evidence_manifest.json": "{}",
                "manifest.sha256.json": "{}",
                "approval_state.json": '{"state":"approved"}',
            }
            for name, content in files.items():
                (run_dir / name).write_text(content, encoding="utf-8")
            preflight = build_preflight(
                "dod_sbir_test",
                run_dir,
                {
                    "deadline_typical": "2099-07-22",
                    "open_date": "2099-06-24",
                    "current_state": "pre_release_released",
                    "source_verified_utc": verified,
                    "ceiling_usd": 250000,
                },
            )
            blockers = "\n".join(preflight["blockers"])
            self.assertIn("not verified open", blockers)
            self.assertIn("funding ceiling", blockers)
            self.assertIn("DSIP account", blockers)
            self.assertIn("DoD compliance review", blockers)

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

    def test_benchmark_beater_preserves_warmup_for_short_windows(self) -> None:
        prices = [
            100.0 + index * 0.1 + 3.0 * __import__("math").sin(index / 7.0)
            for index in range(180)
        ]
        result = simulate_vs_benchmark(
            prices,
            lookback_days=7,
            roundtrip_cost_bps=10.0,
            slippage_bps=2.0,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["bars_simulated"], 7)
        self.assertEqual(
            result["win_rate_definition"],
            "positive_net_active_bar_rate",
        )

    def test_benchmark_beater_fibonacci_proximity_uses_current_price(self) -> None:
        prices = [100.0, 200.0] + [150.0] * 52 + [161.8]
        self.assertAlmostEqual(_fib_prox(prices, 55), 0.0, places=6)

    def test_benchmark_beater_costs_reduce_strategy_return(self) -> None:
        math = __import__("math")
        prices = [
            100.0 + index * 0.03 + 8.0 * math.sin(index / 4.0)
            for index in range(220)
        ]
        frictionless = simulate_vs_benchmark(
            prices,
            lookback_days=90,
            roundtrip_cost_bps=0.0,
            slippage_bps=0.0,
        )
        costed = simulate_vs_benchmark(
            prices,
            lookback_days=90,
            roundtrip_cost_bps=40.0,
            slippage_bps=10.0,
        )
        self.assertTrue(frictionless["ok"])
        self.assertTrue(costed["ok"])
        self.assertLessEqual(
            costed["strategy_return_pct"],
            frictionless["strategy_return_pct"],
        )

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
