from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ADVANCED_FLEET_VALIDATION.py"


def load_module():
    spec = importlib.util.spec_from_file_location("advanced_fleet_validation", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_local_evidence_profiles_rows_without_promoting_dollar_claims(tmp_path):
    module = load_module()
    (tmp_path / "fred_CPIAUCSL.csv").write_text("date,value\n2026-01-01,100\n2026-02-01,101\n", encoding="utf-8")
    (tmp_path / "kraken_live.csv").write_text("timestamp,pair,close\n2026-01-01,BTCUSD,100\n", encoding="utf-8")
    (tmp_path / "Nuclear_Plant_Outages_for_3_6_2026.csv").write_text(
        '"meta"\n"Plant Name","Outage Amount (MW)"\n"Plant A",10\n"Plant B",0\n',
        encoding="utf-8",
    )
    (tmp_path / "Net_generation_United_States_all_sectors_monthly.csv").write_text(
        "Net generation United States all sectors monthly\n"
        "https://www.eia.gov/electricity/data/browser/#/topic/0?agg=2,0,1\n"
        "Data source: U.S. Energy Information Administration\n"
        "Month,all fuels,coal,natural gas\n"
        "Dec 2025,382193,66871,148027\n"
        "Nov 2025,334985,54489,131565\n",
        encoding="utf-8",
    )

    evidence = module.build_local_evidence(tmp_path)

    assert evidence["macro"]["measured_rows"] == 2
    assert evidence["market_data"]["measured_rows"] == 1
    assert evidence["energy"]["measured_rows"] == 4
    assert evidence["macro"]["local_evidence_score"] > 0
    assert str(tmp_path) in evidence["energy"]["data_roots"]

    sector_matrix = {
        "sectors": {
            "macro": {"outage_count": 0, "total_loss_usd": 0, "recoverable_annual_usd": 0},
            "market_data": {"outage_count": 0, "total_loss_usd": 0, "recoverable_annual_usd": 0},
            "energy": {"outage_count": 0, "total_loss_usd": 0, "recoverable_annual_usd": 0},
        }
    }
    opp_gain = {"sectors": {}}
    records = module.to_records(sector_matrix, opp_gain, evidence)
    by_sector = {row["sector"]: row for row in records}

    assert by_sector["macro"]["local_measured_rows"] == 2
    assert by_sector["macro"]["annual_recoverable_usd"] == 0
    assert by_sector["energy"]["local_source_count"] == 2


def test_report_and_html_surface_measured_row_columns():
    module = load_module()
    evidence = {
        "energy": {
            "source_count": 1,
            "measured_rows": 3,
            "bytes": 100,
            "source_files": [{"file": "Nuclear_Plant_Outages_for_3_6_2026.csv"}],
            "measurement_modes": ["csv_rows"],
            "local_evidence_score": 2.5,
        }
    }
    sector_matrix = {
        "sectors": {
            "energy": {"outage_count": 0, "total_loss_usd": 0, "recoverable_annual_usd": 0},
        }
    }
    opp_gain = {"sectors": {"energy": {"avg_savings_pct": 0, "annual_recoverable_usd": 0, "sharpe_improvement": 0}}}
    records = module.to_records(sector_matrix, opp_gain, evidence)
    pack = module.compute_with_polars(records)

    assert pack is not None
    assert pack["top_sectors"][0]["local_measured_rows"] == 3
    assert pack["top_sectors"][0]["institutional_score"] > 0

    html = module.build_html(
        {
            "generated_utc": "2026-06-24T00:00:00+00:00",
            "stack": "test",
            "sectors_scored": 1,
            "top_sectors": pack["top_sectors"],
            "anomalies": [],
        }
    )
    assert "Measured Rows" in html
    assert "Recoverable annual remains tied to the economic model" in html
    assert json.dumps(pack)
