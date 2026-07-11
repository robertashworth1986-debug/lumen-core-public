# LumenCore Estate Master Index - 2026-07-10

Purpose: make the LumenCore universe estate-grade by inventorying the managed workspace, classifying every managed file, connecting concept families to evidence lanes, and keeping sensitive material private.

This is an audit and custody artifact. It does not claim a valuation, patent grant, agency approval, realized savings, field validation, live trading authority, or final submission authority.

## Status

- Status: `LUMENCORE_ESTATE_MASTER_INDEX_READY`
- Managed file count: `100030`
- Managed total bytes: `58103565618`
- Asset classes: `11`
- Custody tiers: `7`
- Concept tags: `14`
- Named concepts: `6`
- Content SHA-256 file count: `99871`
- Large-file deferred content hashes: `57`
- Sensitive metadata-only files: `102`
- Full inventory CSV: `out/ops/lumencore_estate_file_inventory_latest.csv`
- Full inventory CSV bytes: `35604645`
- Scan errors recorded: `1`
- Secret content indexed: `false`
- Final submission without human: `false`
- Legal/IP action without human: `false`
- Live trading allowed: `false`
- Estate index SHA-256: `05642d0c0336abdc4edf8c0dea3bc6a26db529fc2fe7214d981b9daf950eb4a5`

## Asset Classes

- `archive_asset`: `52`
- `dashboard_or_frontend`: `1947`
- `data_asset`: `8978`
- `document_or_review_packet`: `22261`
- `funding_submission_artifact`: `191`
- `machine_output_or_ledger`: `64484`
- `restricted_sensitive_metadata`: `102`
- `source_code_or_automation`: `1467`
- `structured_state_or_config`: `464`
- `visual_media_asset`: `41`
- `working_material`: `43`

## Custody Tiers

- `data_asset_hash_backed`: `8928`
- `estate_inventory_hash_backed`: `2600`
- `large_asset_metadata_hash_content_hash_deferred`: `57`
- `machine_receipt_hash_backed`: `64478`
- `restricted_private_metadata_only`: `102`
- `reviewer_packet_public_safe_after_human_review`: `22398`
- `source_code_audit_ready`: `1467`

## Concept Registry

### live_source

- File count: `29508`
- Concept SHA-256: `e518c2001aa5d53dd69751daa02eada51be67a6d3280ff62409056519b380d1b`
- Example paths:
  - `.deploy_stage/code/BUILD_ADAPTIVE_UNIVERSE_FROM_LIVE_KEYS.py`
  - `.deploy_stage/code/BUILD_APPROVED_SOURCE_BREADTH.py`
  - `.deploy_stage/code/BUILD_INVESTOR_BREADTH_PAGE.py`
  - `.deploy_stage/code/DISCOVER_AND_ROUTE_ALL_LIVE_KEYS.py`
  - `.deploy_stage/code/execution/config/luma_live_keys.env`

### quant_trading

- File count: `22498`
- Concept SHA-256: `ea8cb052c82beec06168530a6668ceab66f271037d20b0eef0595c5ea566c115`
- Example paths:
  - `.deploy_stage/code/.multi_exchange_paper_ticker.lock`
  - `.deploy_stage/code/alpaca_paper_loop_builder.py`
  - `.deploy_stage/code/binanceus_paper_state.json`
  - `.deploy_stage/code/execution/__init__.py`
  - `.deploy_stage/code/execution/alpaca_paper_executor.py`

### agency_protocol

- File count: `12712`
- Concept SHA-256: `a9b6ac33e14c4e54d12e43d399a0730a55489472ef4084a725efc402372c2f6e`
- Example paths:
  - `.deploy_stage/code/execution/federal_brief_builder.py`
  - `.deploy_stage/code/execution/run_federal_brief.py`
  - `.deploy_stage/code/grants_autofill.py`
  - `.deploy_stage/code/grants_profile_lumencore.json`
  - `.deploy_stage/code/RUN_FEDERAL_BRIEF_247.ps1`

### proof_stack

- File count: `12149`
- Concept SHA-256: `6bb0ac90b99b9117cfcf96931cb89f50d1a66822f5a370bf7eaeb7687b9d1c96`
- Example paths:
  - `.deploy_stage/code/ADVANCED_FLEET_VALIDATION.py`
  - `.deploy_stage/code/BUILD_AUDIT_GRADE_DERIVATION_PACK.py`
  - `.deploy_stage/code/build_investor_evidence_pack.py`
  - `.deploy_stage/code/execution/audit_chain.py`
  - `.deploy_stage/code/execution/build_infra_audit_dashboard.py`

### dashboard_ops

- File count: `8158`
- Concept SHA-256: `85fc9ef102cdef6fa5f555d071133b77e81f3f9f65aa76a1873075383d5e9291`
- Example paths:
  - `.deploy_stage/code/build_cold_case_dashboard.py`
  - `.deploy_stage/code/build_xinfit_dashboard.py`
  - `.deploy_stage/code/convert_html_to_pdf.ps1`
  - `.deploy_stage/code/dashboard_unified_refresh.py`
  - `.deploy_stage/code/execution/build_alpaca_paper_dashboard.py`

### infrastructure_energy

- File count: `6731`
- Concept SHA-256: `f0791a29cf9fe3470c391d2a7b38a2a4ca8bd389035ee1a7bda2e857c82a2709`
- Example paths:
  - `.deploy_stage/code/institutional_harmonic_infrastructure.py`
  - `AUDIT_PACK/AUDIT_20260213T233823Z/03_DATACENTER_PILOT_PROPOSAL.txt`
  - `AUDIT_PACK/AUDIT_20260213T235105Z/03_DATACENTER_PILOT_PROPOSAL.txt`
  - `clean_data/coarse_grid.csv`
  - `clean_data/Data_sets__Daily_U.S._nuclear_capacity_outage.csv__bd6ac5306d.csv`

### ip_patent

- File count: `4333`
- Concept SHA-256: `369eb0c6592d48261f72f19be8d8356925847e8d34b9c2bf6a91d8fe94c6a9c5`
- Example paths:
  - `.deploy_stage/code/execution/cross_sector_intel_pipeline.py`
  - `.deploy_stage/code/execution/trade_log_duckdb_pipeline.py`
  - `.deploy_stage/code/RUN_TRIPLET_COMPLETE.ps1`
  - `.deploy_stage/code/run_triplet_complete.py`
  - `.deploy_stage/LamaScout/src/pipeline.py`

### geometry_engine

- File count: `1600`
- Concept SHA-256: `162406900550e9d41e7d5b10d506b9b1faddb0b3e640d1a986d83af21b87095d`
- Example paths:
  - `.deploy_stage/code/execution/harmonic_signal_connector.py`
  - `.deploy_stage/code/execution/institutional_harmonic_suite.py`
  - `.deploy_stage/code/harmonic_hybrid_core.py`
  - `.deploy_stage/code/hybrid_harmonic_algorithms.py`
  - `.deploy_stage/code/hybrid_harmonic_strategies.py`

### revenue_pilot

- File count: `1398`
- Concept SHA-256: `0820fc2c5f2f54c13c43c2eae8e01cb481ed9adbf3a5405a2b2f7d518297e349`
- Example paths:
  - `.deploy_stage/code/RUN_ZERO_TOUCH_AUTOPILOT.ps1`
  - `.deploy_stage/live_domain_proof_feeds_20260627T211904Z/dashboard/data/proof_to_revenue_engine.json`
  - `.deploy_stage/live_domain_proof_feeds_20260627T211904Z/data/proof_to_revenue_engine.json`
  - `.deploy_stage/live_domain_proof_feeds_20260627T215110Z/dashboard/data/proof_to_revenue_engine.json`
  - `.deploy_stage/live_domain_proof_feeds_20260627T215110Z/data/proof_to_revenue_engine.json`

### luma_scout

- File count: `641`
- Concept SHA-256: `de21b96f211a4458e59d1bf909808cb90274dd4f906e5cf1765c612fb326fef4`
- Example paths:
  - `.deploy_stage/code/lamascout_deploy.tgz`
  - `.deploy_stage/code/LAMASCOUT_INTEGRATION.py`
  - `.deploy_stage/LamaScout/.cache`
  - `.deploy_stage/LamaScout/.gitignore`
  - `.deploy_stage/LamaScout/ARCHITECTURE.md`

### harbor_sentinel

- File count: `205`
- Concept SHA-256: `05a36255b7b9ad4f2ec879abff235c6699134c89379aa7bfafdd8c17fbc4df2f`
- Example paths:
  - `code/harbor_sentinel_benchmark.py`
  - `code/harbor_sentinel_validation_suite.py`
  - `code/ops/ACQUIRE_HARBOR_AIS_PILOT_DATA.py`
  - `code/ops/BUILD_HARBOR_AIS_HELDOUT_SPLITS.py`
  - `code/ops/BUILD_HARBOR_AIS_INJECTION_BENCHMARK.py`

### dice

- File count: `138`
- Concept SHA-256: `77183de1ee5fe909b1198b5dede717a412ca5c825628eb308a6d1db04b35a166`
- Example paths:
  - `code/dice_constraint_contract_benchmark.py`
  - `code/dice_preliminary_benchmark.py`
  - `code/ops/BUILD_DICE_EVIDENCE_SYNTHESIS.py`
  - `code/ops/BUILD_DICE_LIVE_BREADTH_REPLAY.py`
  - `code/ops/BUILD_DICE_SUBMISSION_LOCK_PACKET.py`

### luma_jet_skin_suity

- File count: `27`
- Concept SHA-256: `5fa41d69114a5d0c6687a3fdd5ac6e835d007ab50e44747c0d3a00b8e9ea1ea6`
- Example paths:
  - `code/nv065_sensor_tasking_benchmark.py`
  - `docs/NV065_ADAPTIVE_SENSOR_TASKING_VALIDATION_2026-06-19.md`
  - `out/execution/alpaca_symbol_agents/SKIN.json`
  - `out/nv065_sensor_tasking/20260619T_NV065_SENSOR_TASKING_V1/manifest.sha256.json`
  - `out/nv065_sensor_tasking/20260619T_NV065_SENSOR_TASKING_V1/scenario_summary.csv`

### missionweave

- File count: `21`
- Concept SHA-256: `a547d57dadb599dfc6be4c09e467fc21684b93a8e53f652f90902b11e3526247`
- Example paths:
  - `code/missionweave_benchmark.py`
  - `docs/MISSIONWEAVE_GENERATED_WORKFLOW_VALIDATION_2026-06-13.md`
  - `grant_submissions/DLA26BZ03_NV011_MissionWeave/MISSIONWEAVE_BOUNDED_PROCESS_PLAN_2026-06-19.md`
  - `grant_submissions/DLA26BZ03_NV011_MissionWeave/MISSIONWEAVE_CONCEPT_DRAFT.md`
  - `grant_submissions/DLA26BZ03_NV011_MissionWeave/MISSIONWEAVE_COST_BASIS_WORKING.md`

## Named Concepts

### Proof-to-pilot evidence operating system

- Concept ID: `proof_to_pilot_os`
- Estate role: `core_invention_and_funding_spine`
- Safe description: Turns source, baseline, candidate, metric, hash, reviewer, and claim-boundary records into reviewable proof packets.
- Public boundary: No agency validation, field validation, realized savings, or patent grant claim without the relevant human gate.

### Agency and government protocol readiness stack

- Concept ID: `agency_protocol_stack`
- Estate role: `funding_and_contract_access_layer`
- Safe description: Maps SAM, SBIR, RFI, BAA, and CSO opportunities into human-gated response packets.
- Public boundary: No final submit, reps/certs, price, or signature without human approval.

### Autonomous quant replay lab

- Concept ID: `autonomous_quant_replay_lab`
- Estate role: `noisy_market_stress_test_layer`
- Safe description: Uses market and live-source noise for replay, paper evaluation, and proof hardening.
- Public boundary: No live trading, public performance claim, or capital movement without explicit human runtime approval.

### Geometry champion and live-source validation engine

- Concept ID: `geometry_champion_engine`
- Estate role: `technical_alpha_and_cross_sector_evidence_layer`
- Safe description: Ranks geometry/control families against baselines under frozen replay and holdout constraints.
- Public boundary: Internal evidence supports field-replay requests; it is not external field validation by itself.

### IP claim-boundary estate

- Concept ID: `ip_claim_boundary_estate`
- Estate role: `invention_preservation_and_counsel_route`
- Safe description: Preserves invention families, public disclosure rules, hold-back areas, and counsel questions.
- Public boundary: Licensed counsel controls claim charts, filings, deadlines, and legal conclusions.

### Luma Jet / Skin / Suity concept lane

- Concept ID: `luma_jet_skin_suity_lane`
- Estate role: `emerging_product_family`
- Safe description: Held as named concept territory for future structured evidence, source, and IP mapping.
- Public boundary: Concept naming alone is not proof of technical readiness, market validation, or patent support.

## Largest Files

- `data/Data sets/EBA.txt` bytes=`4078041087` class=`data_asset` hash_mode=`metadata_hash_only_large_file` metadata_sha256=`b5bf52947c647fd9f8b6802d3101e6e71fdf658fb85e8343e721f3ceea6318aa`
- `data/promoted_raw/Data_sets__EBA.txt__b8fea129f9.txt` bytes=`4078041087` class=`data_asset` hash_mode=`metadata_hash_only_large_file` metadata_sha256=`0384be37c7702e470255944da0058e117cbfcbc44eb3371352ba40a5f1284025`
- `data/promoted_raw/LumenCore__data_Data_sets_EBA.txt__d0b81c3ac8.txt` bytes=`4078041087` class=`data_asset` hash_mode=`metadata_hash_only_large_file` metadata_sha256=`6c7aa6543cbf1679c824143a66ddc36184dc48f047bcb0420b3c2aa65842ef01`
- `data/promoted_raw/LumenLab__data_Data_sets_EBA.txt__84d68bfa6e.txt` bytes=`4078041087` class=`data_asset` hash_mode=`metadata_hash_only_large_file` metadata_sha256=`004f3dd7787820b48290a1f271c51a4b19fbb1712b6f56714da1271ea7ac5f98`
- `data/promoted_raw/LumenLab__data_EBA.txt__deec3fb453.txt` bytes=`4078041087` class=`data_asset` hash_mode=`metadata_hash_only_large_file` metadata_sha256=`2979cd33c48f7aac0024662a82c9daa9806545f11b287d4113245af5073aff8a`
- `data/promoted_raw/LumenLab__staging_unpacked_EBA.txt__9793275e73.txt` bytes=`4078041087` class=`data_asset` hash_mode=`metadata_hash_only_large_file` metadata_sha256=`6d6e189fcb396c5fcb4c3f914a38ac0e692314dd23f3dcbaa1c69622ab27f9f2`
- `data/Archive 5.zip` bytes=`3222752569` class=`data_asset` hash_mode=`metadata_hash_only_large_file` metadata_sha256=`f609ff32199baa1dc0177770a0187c9343655a79cf03dc52325566fbba9abc78`
- `data/Big bad pitch deck_/Archive 5.zip` bytes=`3222752569` class=`data_asset` hash_mode=`metadata_hash_only_large_file` metadata_sha256=`4e0015b23a08c3e53459057d758196e5e78a586e6e42deaf2a4ce0dd92a39c9d`
- `out/execution/multi_exchange_paper_ticker_ledger.jsonl` bytes=`1679877245` class=`machine_output_or_ledger` hash_mode=`metadata_hash_only_large_file` metadata_sha256=`07eb91a78363ead829e5d17c5bd60862a99d7c0d29b4001abb71dbfef7d5e325`
- `data/promoted_raw/LumenLab__data_ELEC.txt__16c551d1d0.txt` bytes=`1402143450` class=`data_asset` hash_mode=`metadata_hash_only_large_file` metadata_sha256=`ba03483c16dfa1e56b2cf8574a0d421d6e432250b69621c4379ca22e1c1ee2e6`
- `data/promoted_raw/LumenLab__staging_unpacked_ELEC.txt__10eb60d99a.txt` bytes=`1402143450` class=`data_asset` hash_mode=`metadata_hash_only_large_file` metadata_sha256=`f7a7ba901d213e43f2e527a66b55e9d2df9664a2b2580682b8be3fd0ba85e434`
- `data/Archive.zip` bytes=`1361385035` class=`data_asset` hash_mode=`metadata_hash_only_large_file` metadata_sha256=`64f6aa11eb33951c6272c89b7af6a8b35c68e3929f045d632b7838b1e8f05334`
- `data/Big bad pitch deck_/Archive.zip` bytes=`1361385035` class=`data_asset` hash_mode=`metadata_hash_only_large_file` metadata_sha256=`fc3644ebf69240744280fdfeb569fab08cfcdc422c3b5b5a395e6472ade4dc0d`
- `data/Archive 4.zip` bytes=`780043115` class=`data_asset` hash_mode=`metadata_hash_only_large_file` metadata_sha256=`20f82ada7adacee0fed2aeb7523dbcfc462ff48cb6405b9add4bba74ec749cbc`
- `data/Big bad pitch deck_/Archive 4.zip` bytes=`780043115` class=`data_asset` hash_mode=`metadata_hash_only_large_file` metadata_sha256=`5c384f81900a226de33915ce632bc587ece0a07e541a75b308d272a871aea1bf`

## Scan Exceptions

- `data/Grants outreach_/Important documents_/Neutron Strategic Technology Advanced Research (Neutron-STAR) Advanced Research Announcement (ARA)/Attachment 2 - Standard Form 424 (Research and Related SeniorKey Person Profile).pdf` error_type=`FileNotFoundError`

## Audit Rules

- scope: `Managed workspace files under C:/LumaTrader/INSTITUTIONAL_STACK_V2 excluding git, dependency, cache, and bytecode internals.`
- every_managed_file_inventory: `True`
- secret_contents_not_published: `True`
- sensitive_paths_metadata_only: `True`
- large_files_metadata_hash_until_dedicated_custody_pass: `True`
- reviewer_markdown_is_summary_only: `True`
- full_inventory_csv_is_local_custody_artifact: `True`
