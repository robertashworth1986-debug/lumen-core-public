# Session Package Bridge

This bridge pulls the repository-local premium package builders, grant tools, dashboards, evidence artifacts, and integration bridges into one session map. It does **not** access external paid accounts, browser sessions, or private cloud storage; it indexes what is present in this repository so the operator can launch the right local tool or portal workflow quickly.

## Inventory Summary

| Lane | Count indexed | Purpose |
|---|---:|---|
| `grant_submission_tools` | 32 | Grant discovery, package building, final-gate checks, receipt upserts, and submission tracking. |
| `premium_package_builders` | 63 | Investor, federal, dashboard, valuation, handout, and premium deck builders. |
| `bridges_and_integrations` | 40 | Unity, Node-RED, live registry, API, path resolver, and UI integration bridges. |
| `dashboards` | 113 | Operator, grants, mission-control, quant, execution, forecast, anomaly, and evidence surfaces. |
| `evidence_and_proof` | 74 | Manifests, hash chains, proof packs, audit artifacts, and truth reports. |
| `runtime_ops` | 120 | Launchers, sync jobs, watchdogs, bootstrap/deploy scripts, and recovery tools. |

## Fast Local Launch Commands

```powershell
# Open the public/operator dashboard surfaces that are already in this repo
Start-Process "dashboard\grants.html"
Start-Process "dashboard\mission_control.html"
Start-Process "dashboard\operator_home.html"
Start-Process "dashboard\investor_trust_snapshot.html"

# Open the submission portals; operator remains in control of sign-in and final certification
Start-Process "https://apply07.grants.gov/apply/landingPage.faces"
Start-Process "https://sam.gov/entity-registration"
Start-Process "https://pamspublic.science.energy.gov/webpamsepsexternal/login.aspx"
Start-Process "https://www.sbir.gov/"
```

## Operator Rules

1. Keep credentials, MFA codes, bank data, private keys, and account recovery codes out of chat and repo files.
2. Use generated packages and dashboards for preparation; the authorized operator performs final portal certifications and submissions.
3. After a grant submit, preserve tracking number, workspace/application ID, timestamp, confirmation PDF/screenshot, and final package manifest.
4. If an external premium package exists outside this repo, place it in a local folder and run a read-only inventory block before upload; do not paste secrets.


## Local Codex Plugin / MCP Rehydration

When the operator has Codex plugins, Playwright MCP, browser-control bridges, or paid connector caches on a Windows machine, this repo can carry a **non-secret session packet** that helps a future compatible session rehydrate those tools. Run this from the LumenCore repo root on Windows:

```powershell
./code/ops/IMPORT_CODEX_PLUGIN_SESSION_PACKET.ps1
```

The script writes `data/local_codex_plugin_session_manifest.json` and `docs/LOCAL_CODEX_PLUGIN_SESSION_PACKET.md`. It records plugin/MCP paths and capability hints only; it does not copy credentials, browser cookies, MFA codes, or plugin source into the repo, and it does not attach browser control to a hosted session by itself.

## Indexed Lanes

### grant_submission_tools

- `code/GRANT_IIS_DASHBOARD_PUBLISH_ACCESS.ps1`
- `code/grant_application_factory.py`
- `code/grant_hunter_v2.py`
- `code/grant_submission_kit.py`
- `code/grants_api.py`
- `code/grants_autofill.py`
- `code/grants_profile_lumencore.json`
- `code/ops/BUILD_GRANT_EVIDENCE_DELTA_PACK.py`
- `code/ops/BUILD_GRANT_FOLLOWUP_TRACKER.py`
- `code/ops/BUILD_GRANT_KRAKEN_ACTION_BRIEF.py`
- `code/ops/BUILD_GRANT_RESUBMISSION_CHECKLIST.py`
- `code/ops/BUILD_GRANT_SUBMIT_FIT_PACK.py`
- `code/ops/BUILD_GRANT_SUBMIT_NOW_PACK.py`
- `code/ops/BUILD_GRANT_WAITING_ACTIONS.py`
- `code/ops/LOCK_AUTONOMOUS_GRANT_WIN.py`
- `code/ops/MARK_GRANT_SUBMITTED.py`
- `code/ops/REGISTER_GRANT_DASHBOARD_REFRESH_TASK.ps1`
- `code/ops/RUN_BATCH_GRANT_SUBMISSION_READY.py`
- `code/ops/RUN_GRANT_DASHBOARD_AUTO_REFRESH.ps1`
- `code/ops/RUN_GRANT_FACTORY_FASTLANE.ps1`
- `code/ops/RUN_GRANT_FINAL_GATE.py`
- `code/ops/RUN_HEALTHCARE_GRANTS_ENGINE.ps1`
- `code/ops/UPSERT_GRANTS_EMAIL_RECEIPT.py`
- `code/ops/build_skips_grant_autofill_pack.py`
- `code/ops/run_healthcare_grants_engine.py`
- `code/ops/run_healthcare_grants_poc_forecast.py`
- `dashboard/embed/healthcare_grants_widget_example.html`
- `dashboard/grants.html`
- `dashboard/js/luma_healthcare_grants_embed.js`
- `data/grant_catalog.json`
- `docs/GRANT_SUBMISSION_CONTROL_ROOM.md`
- `investor_and_grant_evidence.json`

### premium_package_builders

- `AUDIT_GRADE_DERIVATION_PACK.json`
- `INVESTOR_BRIEF.md`
- `INVESTOR_DEMO_LAUNCH_BLOCKS.ps1`
- `OUTREACH_PACK.txt`
- `code/BUILD_ALL_PREMIUM_DASHBOARDS.py`
- `code/BUILD_ALPACA_PREMIUM_DASHBOARD.py`
- `code/BUILD_AUDIT_GRADE_DERIVATION_PACK.py`
- `code/BUILD_INVESTOR_BREADTH_PAGE.py`
- `code/BUILD_LAMASCOUT_PREMIUM_DASHBOARD.py`
- `code/RUN_FEDERAL_BRIEF_247.ps1`
- `code/RUN_INVESTOR_WALLBOARD.ps1`
- `code/audit_and_leverage_packages.py`
- `code/build_booth_explainer_brief.py`
- `code/build_investor_evidence_pack.py`
- `code/deploy/NED_QR_LANE_PACK.ps1`
- `code/deploy/build_lumaq_execution_pack.py`
- `code/execution/build_institutional_crypto_executive_brief.py`
- `code/execution/build_investor_wallboard.py`
- `code/execution/federal_brief_builder.py`
- `code/execution/harmonic_backprop_proofpack.py`
- `code/execution/investor_performance_report.py`
- `code/execution/premium_mesh_supervisor.py`
- `code/execution/premium_package_mesh.py`
- `code/execution/run_federal_brief.py`
- `code/ops/BUILD_GRANT_EVIDENCE_DELTA_PACK.py`
- `code/ops/BUILD_GRANT_KRAKEN_ACTION_BRIEF.py`
- `code/ops/BUILD_GRANT_SUBMIT_FIT_PACK.py`
- `code/ops/BUILD_GRANT_SUBMIT_NOW_PACK.py`
- `code/ops/BUILD_INSTITUTIONAL_HANDOUT_PACK.py`
- `code/ops/BUILD_INVESTOR_MISSION_CONTROL_PACK.py`
- `code/ops/BUILD_INVESTOR_ONE_PAGER.py`
- `code/ops/BUILD_LINKEDIN_APP_LAUNCHPACK.py`
- `code/ops/BUILD_MEET_DRAPERS_CAPITAL_PROJECTION_PACK.py`
- `code/ops/BUILD_MULTI_ASSET_FROZEN_DELTA_PACK.py`
- `code/ops/BUILD_PREMIUM_3MIN_DROPMIC_DECK.py`
- `code/ops/BUILD_UNIVERSE_INDEX_PACK.ps1`
- `code/ops/BUILD_VALUATION_LICENSING_BRIEF.py`
- `code/ops/EXPORT_RUNTIME_PORTABILITY_PACK.ps1`
- `code/ops/GENERATE_CONTRACT_LOAN_AND_INVESTOR_PACK.py`
- `code/ops/GENERATE_PREMIUM_LUMA_LOGO.py`
- ... 23 more in `data/session_package_inventory.json`

### bridges_and_integrations

- `LamaScout/config/api_registry.yaml`
- `LamaScout/src/api_clients.py`
- `LamaScout/src/dashboard_api.py`
- `code/WAIT_AND_INSTALL_UNITY_BRIDGE.ps1`
- `code/archive/execution/rolling_capital_engine_backup_20260409_213302.py`
- `code/archive/execution/rolling_capital_engine_multi_backup_20260409_213302.py`
- `code/email_opportunity_finder.py`
- `code/execution/README_PAYOUT_BRIDGE.md`
- `code/execution/capital_engine_core.py`
- `code/execution/payout_bridge.py`
- `code/execution/rolling_capital_engine.py`
- `code/execution/rolling_capital_engine_multi.py`
- `code/forecast_api.py`
- `code/grants_api.py`
- `code/node_red/flows_live_truth_bridge.json`
- `code/node_red/flows_luma_bidirectional.json`
- `code/node_red/flows_luma_bootstrap.json`
- `code/opportunities_api.py`
- `code/opportunity_filler.py`
- `code/opportunity_harvester.py`
- `code/ops/BUILD_MEET_DRAPERS_CAPITAL_PROJECTION_PACK.py`
- `code/ops/RUN_EMAIL_OPPORTUNITY_WATCHER.ps1`
- `code/ops/RUN_OPPORTUNITY_AUTOFILL_AND_TRACK.py`
- `code/ops/RUN_OPPORTUNITY_AUTONOMY_LOOP.ps1`
- `code/ops/RUN_OPPORTUNITY_ENGINE_V2.ps1`
- `code/ops/build_api_source_agent_monitor.py`
- `code/probe_apis.py`
- `code/unity_bridge/Editor/LumaExperienceAutoRigEditor.cs`
- `code/unity_bridge/INSTALL_UNITY_BRIDGE.ps1`
- `code/unity_bridge/LumaHarmonicFieldRenderer.cs`
- `code/unity_bridge/LumaLiveTruthBridge.cs`
- `code/unity_bridge/LumaRealtimeBridge.cs`
- `code/unity_bridge/LumaSceneCueDriver.cs`
- `code/unity_bridge/LumaSceneCueReceiver.cs`
- `code/unity_bridge/LumaVoiceGuideController.cs`
- `code/unity_bridge/LumaWsClientBridge.cs`
- `dashboard/js/live_registry_bridge.js`
- `dashboard/js/luma_path_resolver.js`
- `dashboard/test_kraken_futures_api.ps1`
- `live_registry_summary.json`

### dashboards

- `LamaScout/src/dashboard_api.py`
- `LamaScout/src/lamascout_dashboard.py`
- `build_credibility_dashboard.py`
- `build_dashboard.py`
- `build_fundable_dashboard_patch.py`
- `build_kraken_execution_dashboard.py`
- `build_live_sources_dashboard.py`
- `code/BUILD_ALL_PREMIUM_DASHBOARDS.py`
- `code/BUILD_ALPACA_PREMIUM_DASHBOARD.py`
- `code/BUILD_DASHBOARD_PORTAL.py`
- `code/BUILD_LAMASCOUT_PREMIUM_DASHBOARD.py`
- `code/GRANT_IIS_DASHBOARD_PUBLISH_ACCESS.ps1`
- `code/OPEN_PUBLIC_DASHBOARD.ps1`
- `code/RUN_INSTITUTIONAL_CRYPTO_DASHBOARD.ps1`
- `code/RUN_INSTITUTIONAL_DASHBOARD_HEALTHCHECK.ps1`
- `code/RUN_INVESTOR_WALLBOARD.ps1`
- `code/RUN_PUBLIC_DASHBOARD_TUNNEL.ps1`
- `code/RUN_SECTOR_OPP_GAIN_DASHBOARD.ps1`
- `code/RUN_UNIFIED_DASHBOARD.cmd`
- `code/RUN_UNIFIED_DASHBOARD.ps1`
- `code/SHOW_PUBLIC_DASHBOARD_TUNNEL.ps1`
- `code/UNIFIED_MASTER_DASHBOARD_BUILDER.py`
- `code/_inspect_dashboard_loop.ps1`
- `code/archive/dashboard_unified_refresh.py.bak_20260403_122458`
- `code/build_cold_case_dashboard.py`
- `code/build_dashboard_manifest.ps1`
- `code/build_xinfit_dashboard.py`
- `code/dashboard/grid_value_live.json`
- `code/dashboard/infra_live_dashboard.json`
- `code/dashboard_unified_refresh.py`
- `code/deploy/verify_dashboard_endpoints.sh`
- `code/execution/build_alpaca_paper_dashboard.py`
- `code/execution/build_combined_dashboard.py`
- `code/execution/build_infra_audit_dashboard.py`
- `code/execution/build_institutional_crypto_paper_dashboard.py`
- `code/execution/build_investor_wallboard.py`
- `code/execution/build_stage_wallboard.py`
- `code/execution/dashboard_builder.py`
- `code/execution/sector_opp_gain_dashboard.html`
- `code/forecast_api.py`
- ... 73 more in `data/session_package_inventory.json`

### evidence_and_proof

- `AUDIT_GRADE_DERIVATION_PACK.json`
- `CHAIN_OF_CUSTODY_SHA256.json`
- `LamaScout/src/audit.py`
- `LamaScout/src/truth.py`
- `PERSISTED_RUNTIME_LOCK_PROOF.json`
- `adaptive_universe_audit.json`
- `code/BUILD_AUDIT_GRADE_DERIVATION_PACK.py`
- `code/DEPLOY_LIVE_TRUTH_VPS.ps1`
- `code/FIX_MEASURED_SOURCE_AUDIT.py`
- `code/FULL_TRUTH_ORCHESTRATOR.py`
- `code/HARD_TRUTH_LIVE_MEASUREMENT_AUDIT.py`
- `code/REBUILD_LIVE_AUDIT_AND_PAPER_ENGINE.py`
- `code/REBUILD_REGISTRY_FROM_SINGLE_TRUTH.py`
- `code/REBUILD_SINGLE_TRUTH_AND_REVALIDATE.py`
- `code/RUN_FULL_TRUTH_ORCHESTRATOR.ps1`
- `code/RUN_REBUILD_SINGLE_TRUTH_AND_REVALIDATE.ps1`
- `code/RUN_UNIVERSE_AUDIT.ps1`
- `code/STACK_TRUTH_SYNC_AND_FAILFAST.py`
- `code/audit_and_leverage_packages.py`
- `code/autonomous_agent_manifest.py`
- `code/build_dashboard_manifest.ps1`
- `code/build_investor_evidence_pack.py`
- `code/build_kraken_positive_proof.py`
- `code/build_vps_growth_proof.py`
- `code/edge_truth_guard.py`
- `code/execution/audit_chain.py`
- `code/execution/build_infra_audit_dashboard.py`
- `code/execution/harmonic_backprop_proofpack.py`
- `code/execution/rebuild_truth.py`
- `code/execution/universe_audit_runner.py`
- `code/institutional_wiring_audit.py`
- `code/linkedin_publish_evidence.py`
- `code/live_truth_fabric_daemon.py`
- `code/node_red/flows_live_truth_bridge.json`
- `code/ops/AUDIT_DASHBOARD_MIRROR_PARITY.ps1`
- `code/ops/AUDIT_DASHBOARD_VPS_MIRROR.ps1`
- `code/ops/BUILD_FROZEN_DELTA_TRUTH_CHAIN.py`
- `code/ops/BUILD_GRANT_EVIDENCE_DELTA_PACK.py`
- `code/ops/ENFORCE_PRODUCTION_TRUTH_RULE.py`
- `code/ops/RUN_INVESTOR_PROOF_SWEEP.ps1`
- ... 34 more in `data/session_package_inventory.json`

### runtime_ops

- `.github/workflows/deploy.yml`
- `.github/workflows/live-metrics-sync.yml`
- `code/DEPLOY_LIVE_TRUTH_VPS.ps1`
- `code/DEPLOY_TO_VPS_LEAN.ps1`
- `code/FULL_TRUTH_ORCHESTRATOR.py`
- `code/HYDRATE_RUNTIME_ENV_AND_RERUN_KRAKEN.py`
- `code/MASTER_CONTEXT_RECOVERY.md`
- `code/MASTER_DATA_INGESTION_ORCHESTRATOR.py`
- `code/MONTE_CARLO_REVALIDATION_ORCHESTRATOR.py`
- `code/RUN_ALL_LANES.ps1`
- `code/RUN_ALL_SYMBOLS_READONLY.ps1`
- `code/RUN_ALPACA_PAPER_247.ps1`
- `code/RUN_ALPACA_PAPER_247_FIXED.ps1`
- `code/RUN_ALPACA_PAPER_COMPOUNDING.ps1`
- `code/RUN_ALPACA_PAPER_LIVE.ps1`
- `code/RUN_ALPACA_PAPER_ORCHESTRATOR.ps1`
- `code/RUN_BUILD_MASTER_CONTEXT_SNAPSHOT.ps1`
- `code/RUN_CROSS_SECTOR_INTEL_STACK.ps1`
- `code/RUN_ECOSYSTEM_FABRIC_ENGINE.ps1`
- `code/RUN_ELITE_STACK_OPTIMIZER.ps1`
- `code/RUN_FEDERAL_BRIEF_247.ps1`
- `code/RUN_FULL_TRUTH_ORCHESTRATOR.ps1`
- `code/RUN_INFRA_LIVE_LOOP.ps1`
- `code/RUN_INSTITUTIONAL_CRYPTO_DASHBOARD.ps1`
- `code/RUN_INSTITUTIONAL_DASHBOARD_HEALTHCHECK.ps1`
- `code/RUN_INVESTOR_WALLBOARD.ps1`
- `code/RUN_KRAKEN_STAGE2_WITH_ENV.ps1`
- `code/RUN_LUMA_AWARENESS_STACK.ps1`
- `code/RUN_MOONSHOT_TWIN_ENGINE.ps1`
- `code/RUN_MULTI_EXCHANGE_PAPER_TICKER.ps1`
- `code/RUN_ONE_BUTTON_RECONNECT.ps1`
- `code/RUN_PUBLIC_DASHBOARD_TUNNEL.ps1`
- `code/RUN_REBUILD_SINGLE_TRUTH_AND_REVALIDATE.ps1`
- `code/RUN_SECTOR_OPP_GAIN_DASHBOARD.ps1`
- `code/RUN_SPORTS_ODDS_ENGINE.ps1`
- `code/RUN_SYMBOL_WATCHER_FLEET.ps1`
- `code/RUN_TRIPLET_COMPLETE.ps1`
- `code/RUN_UNIFIED_DASHBOARD.cmd`
- `code/RUN_UNIFIED_DASHBOARD.ps1`
- `code/RUN_UNIVERSE_AUDIT.ps1`
- ... 80 more in `data/session_package_inventory.json`

