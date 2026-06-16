# LumenCore Grant Evidence Benchmark Lab

Generated UTC: 2026-06-16T01:41:25.554155+00:00

Live trading allowed: false
Secret values in report: false

## Executive Result

This report builds a reproducible grant evidence package with benchmark lanes, SHA-256 hashes, blocker audit, and reviewer-safe language.

## Benchmark Lane Summary

| Lane | Existing | Ran | Passed | Failed | Timed Out | Claim Type |
|---|---:|---:|---:|---:|---:|---|
| DARPA_DICE | 2 | 2 | 2 | 0 | 0 | bounded preliminary decision intelligence benchmark |
| Navy_HarborSentinel | 4 | 4 | 3 | 0 | 1 | synthetic validation and anomaly monitoring |
| DLA_MissionWeave | 2 | 2 | 2 | 0 | 0 | workflow orchestration and mission support automation |
| NSF_Project_Pitch | 3 | 3 | 2 | 1 | 0 | research novelty, reproducibility, and evaluation protocol |
| Navy_TrackCast | 3 | 3 | 0 | 3 | 0 | signal tracking, forecasting, and early warning |
| Safety_Runtime_Truth | 4 | 4 | 4 | 0 | 0 | safe autonomy and runtime governance |

## Wins / Not Blocking

- UEI exists according to operator
- CAGE exists according to operator
- SAM.gov registration exists according to operator
- SAM.gov API key exists in local registry according to operator
- Grants.gov API key exists in local registry according to operator
- DARPA_DICE: 2 command(s) passed
- Navy_HarborSentinel: 3 command(s) passed
- DLA_MissionWeave: 2 command(s) passed
- NSF_Project_Pitch: 2 command(s) passed
- Safety_Runtime_Truth: 4 command(s) passed

## Detected Blockers

- Navy_TrackCast: scripts exist but no passing benchmark yet

## Likely Remaining Grant Blockers

- agency-specific one-page technical abstract
- reviewer-safe benchmark table
- budget justification mapped to milestones
- commercialization or transition pathway
- letters of support or pilot validation
- final portal field mapping

## Env / Registry Readiness, No Values

```json
{
  "environment_variables_present_no_values": {
    "CAGE": false,
    "CAGE_CODE": false,
    "EIA_API_KEY": true,
    "FRED_API_KEY": true,
    "GRANTS_API_KEY": false,
    "GRANTS_GOV_API_KEY": false,
    "KRAKEN_API_KEY": true,
    "KRAKEN_API_SECRET": true,
    "OPENAI_API_KEY": true,
    "SAM_API_KEY": false,
    "SAM_GOV_API_KEY": false,
    "UEI": false
  },
  "local_env_files_found_no_values": [
    "C:\\LumaTrader\\INSTITUTIONAL_STACK_V2\\config\\luma_live_keys.env",
    "C:\\LumenCore\\ai_workflow_bridge\\.env"
  ],
  "variable_names_seen_in_local_env_files_no_values": [
    "ALLOW_FILE_WRITES",
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET",
    "ALPHAVANTAGE_API_KEY",
    "BEA_API_KEY",
    "BLS_API_KEY",
    "CENSUS_API_KEY",
    "EIA_API_KEY",
    "EPA_AQS_EMAIL",
    "EPA_AQS_KEY",
    "FINNHUB_API_KEY",
    "FRED_API_KEY",
    "KRAKEN_API_KEY",
    "KRAKEN_API_SECRET",
    "LIVE_EXECUTION",
    "MASSIVE_API_KEY",
    "MAX_FILES_TO_SCAN",
    "NASA_API_KEY",
    "NOAA_API_TOKEN",
    "NREL_API_KEY",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "REGISTRY_ROOT",
    "TWELVE_DATA_API_KEY",
    "USGS_WATER_API_KEY",
    "WEBHOOK_SHARED_SECRET"
  ]
}
```

## Premium / Grant Artifact Catalog

Artifacts found: 134

- out/harbor_sentinel/20260616T013840Z/alerts.csv | size 15330803 | sha256 1869b2382b63110f07799fe6fc333266bb72c8edd7d289f9e812c8d569347a9f
- dashboard/mission_control.html | size 134140 | sha256 602a0a7c38110395284fedba247a5065a050477864888c112611129dc68f6703
- code/grant_application_factory.py | size 100139 | sha256 db149bdde033985e770fdbcac4def66845afc8c4bda26833b59ba423bc3e2a66
- dashboard/grants.html | size 81992 | sha256 f1fd6cf4faf1381c4d402cdc33d9475ef722c4b89c9d584ead350b4c73029905
- out/missionweave_validation/scenario_summary.csv | size 62304 | sha256 ee3e66425bcbede263bf8325fa92da047b4d91157ab093ed35840641a90edfe4
- code/grant_hunter_v2.py | size 53925 | sha256 e8418fdd98d0a96e78af85cbacbf503b497c9e05ed532cb1f082aa6f869d0c3a
- code/ops/investor_proof_sweep.py | size 53357 | sha256 73eac2118fd94a9a71d8120629385f19cfc79dbe9e9de025e9281e5b7920eacd
- code/ops/LOCK_AUTONOMOUS_GRANT_WIN.py | size 39392 | sha256 031923ca4398c22f3b61c9dfed9ba0837ad134c96ce865f9b2bd4a581dcf5e06
- code/build_vps_growth_proof.py | size 35851 | sha256 51387ea52d356a170ca2dd44ac8929d3663db63207e182be4ad4be29be8a3291
- code/ops/BUILD_INVESTOR_MISSION_CONTROL_PACK.py | size 35790 | sha256 ae1ba52fd9121f8bd11f45d76bd1df9f6a874a7b0bcfc0617bcd008499523f53
- code/grants_api.py | size 35340 | sha256 c8c84cb5fecb09d624296a4d79987e9c1163363000a6bf85fd2b374d748aa078
- code/harbor_sentinel_benchmark.py | size 33742 | sha256 8ec80504efd01d6be6a31f8b50c3d4757fabd233ed7a37640adc698d1b470c3d
- code/master_universe_benchmark_v2.py | size 33443 | sha256 dea30096181f9af975a68337daa9c927dbeb32bbf5d20c75e528c46f8465587e
- code/build_gov_grade_coherence_report.py | size 32219 | sha256 9ba1927e86ee518873f2e3297bc5c8e61d303e4794b2d8b446a8568aafd06ea6
- code/ops/BUILD_GRANT_SUBMIT_FIT_PACK.py | size 32029 | sha256 a9cd574095001a19d397b881bc7c35db92fd3206ad19c2f17e6a76ea47577655
- code/ops/run_healthcare_grants_engine.py | size 29754 | sha256 7524b51f280a175e99d52a0f211e78bf06e2329f4c4861a07e9a76539bac48c4
- code/ops/BUILD_GRANT_EVIDENCE_DELTA_PACK.py | size 29007 | sha256 b66e3ba0d6707f55c60c2a0f550327e6b2b53ccb1ab9f29514c1d7222181631d
- code/grant_submission_kit.py | size 28768 | sha256 547554f9d26415cb5df492cb9a751e85ba4384e0b559702607d45eb14f85a543
- code/master_universe_benchmark.py | size 28026 | sha256 f4755f4fbcd43f534851e5e5fda502195eb3b09086fdf1e83215f2b59b3f1b56
- code/ops/BUILD_SITE_REACH_AND_DOMAIN_MISSION_PUSH.py | size 27806 | sha256 289336b20ed73d0d5f7f9839c32bdc2dee5559d0ac8dbb0a4503cebb77c2ae09
- code/missionweave_benchmark.py | size 27799 | sha256 ecff9ead66347b48aff093ffd7affe8958f355bf93273be8820dc5326331e39d
- code/ops/BUILD_PREMIUM_3MIN_DROPMIC_DECK.py | size 27243 | sha256 50b60b08b145f57bfe6b3107f57efb6dada70786647fae379d309c184d61bc12
- code/BUILD_ALPACA_PREMIUM_DASHBOARD.py | size 26421 | sha256 1caf521e3777ff9a439dea261533eb3d97323566c0ede5df1b108eea1b96f35b
- dashboard/evidence/index.html | size 25917 | sha256 699de4ef2eed56f4417c8e7a058dd67aea065afb7cf995ecb3ce8c20552567ba
- code/BUILD_LAMASCOUT_PREMIUM_DASHBOARD.py | size 23193 | sha256 b1bd30f7c17742a0b67f865285c4dcfc0f76f40cbecf336c2690575abe02af8a
- code/execution/fleet_coherence_monitor.py | size 22851 | sha256 bb99320fedcc3ff10436e2d13bc1afe65b5a787319fe56928e8cab25270c3d7c
- code/PATCH_SEED_VALIDATION_READER_FIX2.py | size 22404 | sha256 dc2d6af18f29fbfc90204f659db65f4cdc58c52cc09ec648f7f9dda3523252fd
- code/execution/seed_validation_reader.py | size 22404 | sha256 dc2d6af18f29fbfc90204f659db65f4cdc58c52cc09ec648f7f9dda3523252fd
- code/FORCE_REBUILD_SEED_VALIDATION.py | size 22105 | sha256 49081000d64c12700eeabca5ff528833789a671826fbeb9862a76f83dcc247cc
- code/execution/harmonic_backprop_proofpack.py | size 21909 | sha256 c7bbf6c63b3c9e0d7e144432dac2a2b5413b8d7dc9a7b015759c2d6d52ed2679
- code/ops/build_skips_grant_autofill_pack.py | size 21827 | sha256 e1dc5e4584460a4c3a94f19246fd9afd3b94f96e1149ab3fe1eb5f969f6b8ad0
- code/dice_preliminary_benchmark.py | size 21430 | sha256 b9f54993b1a5483e38d28ed003bf47ec28f2778e03322434868c1e4333a8c2bf
- code/ops/BUILD_GOV_BLUEPRINT_VAULT.py | size 21063 | sha256 495914d22d2a63b80ba854608a8b4d285df75833763c094d81455f7a88447f40
- code/PATCH_SEED_VALIDATION_READER.py | size 21047 | sha256 13810d980420e61c5b95d4e4850e039b2f5b320b02ba4923331d510d61107eb2
- out/missionweave_validation/summary.json | size 20809 | sha256 a8d75fe3480733c29cdbd73cf5e39e8a25b84f8d38cf33f84dc7c2e54bc55c27
- code/SEED_VALIDATION_READOUT.py | size 20539 | sha256 fc6edfad219f279ed16f53af4488d5cf730c7014c8ae2906511b907cb8b17e0a
- code/ops/run_healthcare_grants_poc_forecast.py | size 19951 | sha256 6e7c5b43851604815a9a81061fd7a3328eab51a8db407749eac04a5f0918451b
- code/ops/RUN_INVESTOR_PACKET_REFRESH.ps1 | size 19748 | sha256 00a0a811b0b181c65cd56a4f3311d2147795e1d667cb0a1f1f08919a83a8b868
- code/MONTE_CARLO_REVALIDATION_ORCHESTRATOR.py | size 18963 | sha256 bd0a57fa997524bf0ded2cf34f6c7b7125871f2d173c2c0916951d9a54bb1ea1
- code/ops/GENERATE_CONTRACT_LOAN_AND_INVESTOR_PACK.py | size 18464 | sha256 674bfe65690f34b5348466b7213edc527d851ab7c90e0abd74840b35cb641f36
- code/CANONICAL_GOV_DATA_COLLECTOR.py | size 17106 | sha256 63bdce71f4b91ffcab1f301a0dba11a901e24c711e0b3a424c01712dc186b885
- code/ops/BUILD_MISSION_CONTROL_SUPPORT_ARTIFACTS.py | size 16984 | sha256 7463390c954f897e806c11b7da1a8c732016218a57b3142415941f74e0e88606
- code/real_data_fair_benchmark.py | size 16839 | sha256 bc6476ca23fd1dcc0170adb2130e47abf037ac8b43afe6958728363f94739613
- code/ops/run_sector_energy_evidence_pipeline.py | size 16774 | sha256 71f599e8251fb1cb4a9672558f4c8443436afcb6bac296ad4292d14916f63014
- code/harbor_sentinel_validation_suite.py | size 16432 | sha256 dc9c2586efa5659b8934f02fec37e6afea4afac3780fdff6c566743b10ee14ac
- code/build_kraken_positive_proof.py | size 16067 | sha256 b81b0ceb1b7bd246199c09779d1008e343408568bccd1534a0c2d89bfdb9397e
- code/ops/RUN_GRANT_FINAL_GATE.py | size 15085 | sha256 6e3e197382ced8dd73c84b98e1d2d42969aec9f6158b8c0ae1fc613376992abf
- code/execution/benchmark_beater.py | size 15033 | sha256 fc36e7c2eba24462c02058d4e6c09edccea28cfe0e3fcea4186f3c3c0d00ec35
- code/ops/GENERATE_PREMIUM_LUMA_LOGO.py | size 14678 | sha256 184b0aca883f2338b8645faf4a5041c6a493f3f21a1c0515c622ac8b08227f51
- code/ops/BUILD_GRANT_KRAKEN_ACTION_BRIEF.py | size 14508 | sha256 3af56a0c5ecc5822e4ebc9935d1743d668be50470eec0e53a8a7a398e039a95f

## Detailed Benchmark Results

### DARPA_DICE

#### code/dice_preliminary_benchmark.py
- Exists: True
- SHA-256: b9f54993b1a5483e38d28ed003bf47ec28f2778e03322434868c1e4333a8c2bf
- Ran: True
- Return code: 0
- Timeout: False

Output tail:
```text
{
  "mission_success_rate_points": 0.008333333333343518,
  "message_reduction_pct": 31.48226977800137,
  "recovery_message_reduction_pct": 40.98837209302325,
  "role_coherence_rate_points": 6.534143924048541
}

```

#### tests/test_dice_preliminary_benchmark.py
- Exists: True
- SHA-256: 2b387e642d5ec4cd18b4b621c10c05cf20ccc30da64d651a9e8e6618d0401f2b
- Ran: True
- Return code: 0
- Timeout: False

Error tail:
```text
.
----------------------------------------------------------------------
Ran 1 test in 0.151s

OK

```

### Navy_HarborSentinel

#### code/harbor_sentinel_benchmark.py
- Exists: True
- SHA-256: 8ec80504efd01d6be6a31f8b50c3d4757fabd233ed7a37640adc698d1b470c3d
- Ran: True
- Return code: 0
- Timeout: False

Output tail:
```text
{
  "run_dir": "C:\\LumenCore_GitHub\\lumen-core-public\\out\\harbor_sentinel\\20260616T013840Z",
  "precision_mean": 0.9399105316753726,
  "precision_min": 0.926829268292683,
  "recall_mean": 0.9176639421099668,
  "recall_min": 0.9131313131313131,
  "f1_mean": 0.9286436503916782,
  "f1_min": 0.9220138203356368,
  "baseline_f1_mean": 0.5974858007537273,
  "f1_lift_over_baseline_pct": 55.425225038016954,
  "event_recall_mean": 1.0,
  "median_detection_delay_steps": 1.0,
  "false_alerts_per_10000_mean": 78.8718394889132,
  "explanation_coverage_mean": 1.0,
  "maximum_algorithmic_state_bytes_per_track": 139
}

```

#### code/harbor_sentinel_validation_suite.py
- Exists: True
- SHA-256: dc9c2586efa5659b8934f02fec37e6afea4afac3780fdff6c566743b10ee14ac
- Ran: True
- Return code: None
- Timeout: True

#### tests/test_harbor_sentinel_benchmark.py
- Exists: True
- SHA-256: b50141710b3a36bc780f297395a710c15791464615eb6a4900a2f934102080fe
- Ran: True
- Return code: 0
- Timeout: False

Error tail:
```text
.........
----------------------------------------------------------------------
Ran 9 tests in 2.234s

OK

```

#### tests/test_harbor_sentinel_validation_suite.py
- Exists: True
- SHA-256: 5ba5ef9420d9ab603eb529c885a4c86f53c52bc1b19109c8eced2eab6c26dd24
- Ran: True
- Return code: 0
- Timeout: False

Error tail:
```text
.
----------------------------------------------------------------------
Ran 1 test in 15.283s

OK

```

### DLA_MissionWeave

#### code/missionweave_benchmark.py
- Exists: True
- SHA-256: ecff9ead66347b48aff093ffd7affe8958f355bf93273be8820dc5326331e39d
- Ran: True
- Return code: 0
- Timeout: False

Output tail:
```text
{
  "selected_weights": "critical",
  "conditions": {
    "nominal": {
      "mean_delta": 0.057771679432762096,
      "bootstrap_95pct_interval": [
        0.03777214601520276,
        0.0806324318037359
      ],
      "favorable_scenario_fraction": 0.8333333333333334,
      "zero_delta_scenario_fraction": 0.13333333333333333,
      "scenario_count": 30
    },
    "surge": {
      "mean_delta": 0.1155766853539992,
      "bootstrap_95pct_interval": [
        0.07408176607555333,
        0.16113158148214404
      ],
      "favorable_scenario_fraction": 0.8,
      "zero_delta_scenario_fraction": 0.03333333333333333,
      "scenario_count": 30
    },
    "targeted_absence": {
      "mean_delta": 0.11751993789161899,
      "bootstrap_95pct_interval": [
        0.0733448224001888,
        0.16384198104453804
      ],
      "favorable_scenario_fraction": 0.8333333333333334,
      "zero_delta_scenario_fraction": 0.1,
      "scenario_count": 30
    },
    "system_outage": {
      "mean_delta": 0.12659297855361853,
      "bootstrap_95pct_interval": [
        0.08517337633262627,
        0.17614313325317768
      ],
      "favorable_scenario_fraction": 0.9333333333333333,
      "zero_delta_scenario_fraction": 0.0,
      "scenario_count": 30
    },
    "combined_stress": {
      "mean_delta": 0.030165132726542716,
      "bootstrap_95pct_interval": [
        0.01677235021739905,
        0.04350157097340508
      ],
      "favorable_scenario_fraction": 0.7666666666666667,
      "zero_delta_scenario_fraction": 0.0,
      "scenario_count": 30
    }
  }
}

```

#### tests/test_missionweave_benchmark.py
- Exists: True
- SHA-256: c5e1ed552e100db9e13690b3c7ac561a59a89031208aea4ea0583836313ad178
- Ran: True
- Return code: 0
- Timeout: False

Error tail:
```text
....
----------------------------------------------------------------------
Ran 4 tests in 0.339s

OK

```

### NSF_Project_Pitch

#### code/real_data_fair_benchmark.py
- Exists: True
- SHA-256: bc6476ca23fd1dcc0170adb2130e47abf037ac8b43afe6958728363f94739613
- Ran: True
- Return code: 1
- Timeout: False

Output tail:
```text
=== real_data_fair_benchmark @ 20260616T014119Z ===
output dir: C:\LumenCore_GitHub\lumen-core-public\out\real_data_fair_benchmark\20260616T014119Z

[fetch] EIA_GEN_ALL_FUELS ...
  ! fetch failed: EIA_API_KEY missing
[fetch] EIA_GEN_SOLAR ...
  ! fetch failed: EIA_API_KEY missing
[fetch] EIA_GEN_WIND ...
  ! fetch failed: EIA_API_KEY missing
[fetch] EIA_GEN_NATGAS ...
  ! fetch failed: EIA_API_KEY missing
FATAL: no datasets succeeded

```

#### code/validation_proof_pack.py
- Exists: True
- SHA-256: 0617aa791c3ec7051214dd5b687255a2f9b842cb2f004f812d05cb2f14ae8dbf
- Ran: True
- Return code: 0
- Timeout: False

#### code/build_gov_grade_coherence_report.py
- Exists: True
- SHA-256: 9ba1927e86ee518873f2e3297bc5c8e61d303e4794b2d8b446a8568aafd06ea6
- Ran: True
- Return code: 0
- Timeout: False

Output tail:
```text
C:\LumenCore_GitHub\lumen-core-public\out\execution\gov_grade_coherence_report.json
C:\LumenCore_GitHub\lumen-core-public\out\execution\gov_grade_coherence_report.md
C:\LumenCore_GitHub\lumen-core-public\out\execution\gov_grade_coherence_report_sha256.json
C:\LumenCore_GitHub\lumen-core-public\out\execution\gov_grade_coherence_report_history.jsonl
C:\LumenCore_GitHub\lumen-core-public\dashboard\data\gov_grade_coherence_report.json

```

### Navy_TrackCast

#### code/regime_shift_scanner.py
- Exists: True
- SHA-256: 68b751fe566970b44877fc3aa450460295320af32d3c1cff2762bed08899dc8f
- Ran: True
- Return code: 1
- Timeout: False

Error tail:
```text
Traceback (most recent call last):
  File "C:\LumenCore_GitHub\lumen-core-public\code\regime_shift_scanner.py", line 259, in <module>
    raise SystemExit(main())
                     ~~~~^^
  File "C:\LumenCore_GitHub\lumen-core-public\code\regime_shift_scanner.py", line 157, in main
    utc = _resolve_run_utc()
  File "C:\LumenCore_GitHub\lumen-core-public\code\regime_shift_scanner.py", line 65, in _resolve_run_utc
    runs = sorted([p.name for p in V2_RUNS.iterdir() if p.is_dir()])
                                   ~~~~~~~~~~~~~~~^^
  File "C:\Python314\Lib\pathlib\__init__.py", line 836, in iterdir
    with os.scandir(root_dir) as scandir_it:
         ~~~~~~~~~~^^^^^^^^^^
FileNotFoundError: [WinError 3] The system cannot find the path specified: 'C:\\LumenCore_GitHub\\lumen-core-public\\out\\master_universe_v2'

```

#### code/anomaly_scanner.py
- Exists: True
- SHA-256: f8133229a107190aec1cd12158b0f3a07bea8e402b567246a88d80d193ba698d
- Ran: True
- Return code: 1
- Timeout: False

Output tail:
```text
FATAL: no ANOM_UTC and no latest.txt

```

#### code/forecast_api.py
- Exists: True
- SHA-256: 1ca15b15a651bb42782b065743cac105472c044a048d4e633f0d6b36239a786e
- Ran: True
- Return code: 1
- Timeout: False

Error tail:
```text
Traceback (most recent call last):
  File "C:\LumenCore_GitHub\lumen-core-public\code\forecast_api.py", line 39, in <module>
    from fastapi import APIRouter, HTTPException, Query
ModuleNotFoundError: No module named 'fastapi'

```

### Safety_Runtime_Truth

#### code/execution/live_data_no_orders_gate.py
- Exists: True
- SHA-256: 8e2f4f67e3c3656e550754dc8f1786d9fe3c5b5169d1a3e53958dba4fa9e4a5f
- Ran: True
- Return code: 0
- Timeout: False

Output tail:
```text
LIVE_DATA_NO_ORDERS_GATE=PASS_READ_ONLY
ORDER_PERMISSION=False
REASON=blocked_by_live_data_no_orders_stage
REPORT=C:\LumenCore_GitHub\lumen-core-public\out\safety_reports\LATEST_live_data_no_orders_gate.md

```

#### code/execution/order_safety_gate.py
- Exists: True
- SHA-256: 2c9bf922087fb002d3ef72c2b71351a1ae5e7eda4fcd7fcad89057d01ada5eaa
- Ran: True
- Return code: 0
- Timeout: False

Output tail:
```text
{
  "approved": false,
  "blockers": [],
  "generated_utc": "2026-06-16T01:41:24.044895+00:00",
  "intent": {
    "notional_usd": 1.0,
    "order_type": "market",
    "quantity": null,
    "side": "buy",
    "source": "order_safety_gate_smoke",
    "symbol": "TEST/USD"
  },
  "reason": "blocked_by_live_data_no_orders_stage",
  "stage": "live-data-no-orders",
  "warnings": [
    "kill_switch_clear_by_file_check",
    "live_order_config_detected_but_stage_blocks_orders",
    "risk_local_basic_pass",
    "signal_local_no_known_gate"
  ]
}

```

#### code/execution/safe_live_executor.py
- Exists: True
- SHA-256: 4c59e1dca7fb9676c25e7e50bd53aa5382a94a7945d5af461f0541f23f5e23e5
- Ran: True
- Return code: 0
- Timeout: False

Output tail:
```text
{
  "approved": false,
  "blocked": true,
  "decision": {
    "approved": false,
    "blockers": [],
    "generated_utc": "2026-06-16T01:41:25.267558+00:00",
    "intent": {
      "notional_usd": 1.0,
      "order_type": "market",
      "quantity": null,
      "side": "buy",
      "source": "safe_live_executor_smoke",
      "symbol": "TEST/USD"
    },
    "reason": "blocked_by_live_data_no_orders_stage",
    "stage": "live-data-no-orders",
    "warnings": [
      "kill_switch_clear_by_file_check",
      "live_order_config_detected_but_stage_blocks_orders",
      "risk_local_basic_pass",
      "signal_local_no_known_gate"
    ]
  },
  "executor_called": false,
  "executor_result": null,
  "generated_utc": "2026-06-16T01:41:25.268075+00:00",
  "intent": {
    "notional_usd": 1.0,
    "order_type": "market",
    "quantity": null,
    "side": "buy",
    "source": "safe_live_executor_smoke",
    "symbol": "TEST/USD"
  },
  "live_executor_surface": {
    "candidate_functions_found": [],
    "import_ok": true,
    "order_related_callables": [
      "MultiExchangeRouter",
      "OrderRouter",
      "RouteIntent"
    ]
  },
  "reason": "blocked_by_live_data_no_orders_stage",
  "stage": "live-data-no-orders"
}
REPORT=C:\LumenCore_GitHub\lumen-core-public\out\safety_reports\LATEST_safe_live_executor_smoke.md

```

#### code/execution/tiny_live_manual_arm_readiness.py
- Exists: True
- SHA-256: cde841a9654fec163e70847adfb02d3d53c2a48a6aba32c8bec12d97bd7c52d3
- Ran: True
- Return code: 0
- Timeout: False

Output tail:
```text
{
  "audit_counts": {
    "files_with_raw_live_references": 33,
    "files_with_safe_references": 18
  },
  "blockers": [],
  "live_trading_active": false,
  "mode": "design_only",
  "reason": "manual_arm_not_enabled_design_only",
  "tiny_live_ready": false
}
JSON_REPORT=C:\LumenCore_GitHub\lumen-core-public\out\safety_reports\LATEST_tiny_live_manual_arm_readiness.json
MD_REPORT=C:\LumenCore_GitHub\lumen-core-public\out\safety_reports\LATEST_tiny_live_manual_arm_readiness.md

```

## Reviewer-Safe Claim Language

Use: preliminary benchmark, bounded synthetic validation, reproducible evidence package, prototype safety-gated runtime, measured candidate lanes.

Avoid: guaranteed, undeniable, proves superiority, fully autonomous live trading, risk-free.

## Next Work

1. Turn passing lanes into agency-specific evidence cards.
2. Add missing benchmark scripts where lanes do not pass.
3. Map budget and milestones to each grant.
4. Add pilot letters or support validation.
5. Keep live trading separate from grant science claims.