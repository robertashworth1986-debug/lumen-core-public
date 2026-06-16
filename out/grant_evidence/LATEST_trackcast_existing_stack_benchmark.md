# TrackCast Existing Stack Benchmark

Generated UTC: 2026-06-16T02:00:59.295044+00:00

## Result

- Pass: True
- Score: 12
- Meaning: Existing TrackCast stack is discoverable and benchmark-ready at the structural level.

## Reasons

- master_universe directory discovered
- latest data file discovered
- anomaly data/source discovered
- TrackCast data artifact discovered
- regime shift script discovered
- anomaly script discovered
- forecast script discovered

## Discovery Buckets

### master_universe_dirs

- Count shown: 2

- root_label=repo path=out/master_universe size=None sha256=None
- root_label=repo path=out/master_universe_v2 size=None sha256=None

### latest_files

- Count shown: 4

- root_label=repo path=out/harbor_sentinel/latest.txt size=18 sha256=aa1b41a8d69a870f724724978fa443078a79758828d1f9de5687d968037308ff
- root_label=C_LumaTrader path=dashboard/evidence/latest.txt size=16 sha256=a01c72c51846f127f71c7c7966d7adaa1075214e432b4e228f7fa4954058ca76
- root_label=C_LumaTrader path=INSTITUTIONAL_STACK_V2/dashboard/evidence/latest.txt size=16 sha256=a01c72c51846f127f71c7c7966d7adaa1075214e432b4e228f7fa4954058ca76
- root_label=C_LumaTrader_Institutional path=dashboard/evidence/latest.txt size=16 sha256=a01c72c51846f127f71c7c7966d7adaa1075214e432b4e228f7fa4954058ca76

### anom_files

- Count shown: 40

- root_label=C_LumaTrader path=dashboard/evidence/runs/20260505T121657Z/anomalies/anomalies.csv size=58011 sha256=2a37af85db7cb59b5f886210f6d51308cd0ff02601de2458aeeb173ecb1642b8
- root_label=C_LumaTrader path=dashboard/evidence/runs/20260505T121657Z/anomalies/anomaly_summary.md size=2034 sha256=7617d91e33452cd769c7030366f61ba2671e0523031b585548a02f5b47dd3877
- root_label=C_LumaTrader path=dashboard/evidence/runs/20260505T121657Z/anomalies/manifest.sha256.json size=417 sha256=4ac63a36be4cbd9fbeaad2f2cdf21443fe726de0f21fdb94e202d9402667bce9
- root_label=C_LumaTrader path=dashboard/evidence/runs/20260505T121657Z/anomalies/ranked.csv size=48178 sha256=e06977dea41ba969ebc167a552949b7ff2e3e6b588d28057ae67191fbf0856ba
- root_label=C_LumaTrader path=dashboard/evidence/runs/20260505T121657Z/anomalies/summary.json size=352 sha256=cb64887018d41c92971a0a90ba4e6a996d6c17f5e92aadc4e91deb5679fdfc64
- root_label=C_LumaTrader path=dashboard/evidence/runs/20260511T175644Z/anomalies/anomalies.csv size=58011 sha256=2a37af85db7cb59b5f886210f6d51308cd0ff02601de2458aeeb173ecb1642b8
- root_label=C_LumaTrader path=dashboard/evidence/runs/20260511T175644Z/anomalies/anomaly_summary.md size=2034 sha256=7617d91e33452cd769c7030366f61ba2671e0523031b585548a02f5b47dd3877
- root_label=C_LumaTrader path=dashboard/evidence/runs/20260511T175644Z/anomalies/manifest.sha256.json size=417 sha256=4ac63a36be4cbd9fbeaad2f2cdf21443fe726de0f21fdb94e202d9402667bce9
- root_label=C_LumaTrader path=dashboard/evidence/runs/20260511T175644Z/anomalies/ranked.csv size=48178 sha256=e06977dea41ba969ebc167a552949b7ff2e3e6b588d28057ae67191fbf0856ba
- root_label=C_LumaTrader path=dashboard/evidence/runs/20260511T175644Z/anomalies/summary.json size=352 sha256=cb64887018d41c92971a0a90ba4e6a996d6c17f5e92aadc4e91deb5679fdfc64
- root_label=C_LumaTrader path=dashboard/evidence/runs/20260526T050639Z/anomalies/anomalies.csv size=58011 sha256=2a37af85db7cb59b5f886210f6d51308cd0ff02601de2458aeeb173ecb1642b8
- root_label=C_LumaTrader path=dashboard/evidence/runs/20260526T050639Z/anomalies/anomaly_summary.md size=2034 sha256=7617d91e33452cd769c7030366f61ba2671e0523031b585548a02f5b47dd3877
- root_label=C_LumaTrader path=dashboard/evidence/runs/20260526T050639Z/anomalies/manifest.sha256.json size=417 sha256=4ac63a36be4cbd9fbeaad2f2cdf21443fe726de0f21fdb94e202d9402667bce9
- root_label=C_LumaTrader path=dashboard/evidence/runs/20260526T050639Z/anomalies/ranked.csv size=48178 sha256=e06977dea41ba969ebc167a552949b7ff2e3e6b588d28057ae67191fbf0856ba
- root_label=C_LumaTrader path=dashboard/evidence/runs/20260526T050639Z/anomalies/summary.json size=352 sha256=cb64887018d41c92971a0a90ba4e6a996d6c17f5e92aadc4e91deb5679fdfc64
- root_label=C_LumaTrader path=INSTITUTIONAL_STACK_V2/dashboard/evidence/runs/20260505T121657Z/anomalies/anomalies.csv size=58011 sha256=2a37af85db7cb59b5f886210f6d51308cd0ff02601de2458aeeb173ecb1642b8
- root_label=C_LumaTrader path=INSTITUTIONAL_STACK_V2/dashboard/evidence/runs/20260505T121657Z/anomalies/anomaly_summary.md size=2034 sha256=7617d91e33452cd769c7030366f61ba2671e0523031b585548a02f5b47dd3877
- root_label=C_LumaTrader path=INSTITUTIONAL_STACK_V2/dashboard/evidence/runs/20260505T121657Z/anomalies/manifest.sha256.json size=417 sha256=4ac63a36be4cbd9fbeaad2f2cdf21443fe726de0f21fdb94e202d9402667bce9
- root_label=C_LumaTrader path=INSTITUTIONAL_STACK_V2/dashboard/evidence/runs/20260505T121657Z/anomalies/ranked.csv size=48178 sha256=e06977dea41ba969ebc167a552949b7ff2e3e6b588d28057ae67191fbf0856ba
- root_label=C_LumaTrader path=INSTITUTIONAL_STACK_V2/dashboard/evidence/runs/20260505T121657Z/anomalies/summary.json size=352 sha256=cb64887018d41c92971a0a90ba4e6a996d6c17f5e92aadc4e91deb5679fdfc64

### trackcast_data_files

- Count shown: 5

- root_label=repo path=docs/grant_evidence_cards/Navy_TrackCast_EVIDENCE_CARD.md size=1427 sha256=5f8e97da53db063f1a045bf2dd2e28d3eef686a9c4b3c28c5f286544f69fb69a
- root_label=repo path=out/grant_evidence/LATEST_trackcast_existing_stack_benchmark.json size=25591 sha256=fc5f10ac4a762fe9c4c91e02d7d492a634034f842a73c9069f98c09be3d5751f
- root_label=repo path=out/grant_evidence/LATEST_trackcast_existing_stack_benchmark.md size=9269 sha256=f719a80aad79d29b4afc37eeff58ff6fa6919db573336b0129ed24a4e5348aed
- root_label=repo path=out/grant_evidence/TRACKCAST_EXISTING_STACK_REPAIR.md size=995 sha256=950c41257e169b105b3503a2b5e44be59a549f1dd4b9feee960109346af63eb0
- root_label=repo path=out/grant_evidence/TRACKCAST_FAILURE_TRIAGE.md size=1233 sha256=3077b73008c19890eba0b017f2d58616ee5faea60cf70a31f98024f432b2c6df

### trackcast_scripts

- Count shown: 1

- root_label=repo path=code/trackcast/trackcast_existing_stack_benchmark.py size=9797 sha256=3a092e0bec0872a2bb5d34b83961b4e552f5151a476479cfa78a0993d7169f1b

### regime_shift_scripts

- Count shown: 3

- root_label=repo path=code/regime_shift_scanner.py size=9203 sha256=68b751fe566970b44877fc3aa450460295320af32d3c1cff2762bed08899dc8f
- root_label=C_LumaTrader path=INSTITUTIONAL_STACK_V2/code/regime_shift_scanner.py size=9203 sha256=68b751fe566970b44877fc3aa450460295320af32d3c1cff2762bed08899dc8f
- root_label=C_LumaTrader_Institutional path=code/regime_shift_scanner.py size=9203 sha256=68b751fe566970b44877fc3aa450460295320af32d3c1cff2762bed08899dc8f

### anomaly_scripts

- Count shown: 5

- root_label=repo path=code/anomaly_scanner.py size=10181 sha256=f8133229a107190aec1cd12158b0f3a07bea8e402b567246a88d80d193ba698d
- root_label=C_LumaTrader path=INSTITUTIONAL_STACK_V2/code/anomaly_scanner.py size=10181 sha256=f8133229a107190aec1cd12158b0f3a07bea8e402b567246a88d80d193ba698d
- root_label=C_LumaTrader path=INSTITUTIONAL_STACK_V2/env311/Lib/site-packages/torch/autograd/anomaly_mode.py size=5072 sha256=168c1fd281017b0e237aca182356e068a5ec27cfaefaaa14fbd4deb9c18cb090
- root_label=C_LumaTrader_Institutional path=code/anomaly_scanner.py size=10181 sha256=f8133229a107190aec1cd12158b0f3a07bea8e402b567246a88d80d193ba698d
- root_label=C_LumaTrader_Institutional path=env311/Lib/site-packages/torch/autograd/anomaly_mode.py size=5072 sha256=168c1fd281017b0e237aca182356e068a5ec27cfaefaaa14fbd4deb9c18cb090

### forecast_scripts

- Count shown: 8

- root_label=repo path=code/forecast_api.py size=20326 sha256=1ca15b15a651bb42782b065743cac105472c044a048d4e633f0d6b36239a786e
- root_label=repo path=code/ops/run_healthcare_grants_poc_forecast.py size=19951 sha256=6e7c5b43851604815a9a81061fd7a3328eab51a8db407749eac04a5f0918451b
- root_label=C_LumaTrader path=INSTITUTIONAL_STACK_V2/code/forecast_api.py size=20326 sha256=1ca15b15a651bb42782b065743cac105472c044a048d4e633f0d6b36239a786e
- root_label=C_LumaTrader path=INSTITUTIONAL_STACK_V2/code/ops/run_healthcare_grants_poc_forecast.py size=19951 sha256=6e7c5b43851604815a9a81061fd7a3328eab51a8db407749eac04a5f0918451b
- root_label=C_LumaTrader path=INSTITUTIONAL_STACK_V2/env311/Lib/site-packages/statsmodels/tsa/statespace/tests/test_forecasting.py size=1626 sha256=305d82bf48e53123484c62856efa95d8d05890f4b804d1c924b1c3ec4371028a
- root_label=C_LumaTrader_Institutional path=code/forecast_api.py size=20326 sha256=1ca15b15a651bb42782b065743cac105472c044a048d4e633f0d6b36239a786e
- root_label=C_LumaTrader_Institutional path=code/ops/run_healthcare_grants_poc_forecast.py size=19951 sha256=6e7c5b43851604815a9a81061fd7a3328eab51a8db407749eac04a5f0918451b
- root_label=C_LumaTrader_Institutional path=env311/Lib/site-packages/statsmodels/tsa/statespace/tests/test_forecasting.py size=1626 sha256=305d82bf48e53123484c62856efa95d8d05890f4b804d1c924b1c3ec4371028a

## Reviewer-Safe Claim

TrackCast existing-stack discovery verifies that local stack artifacts and/or scripts are present without printing secrets or raw data. This supports integration readiness, while the benchmark lane still needs direct algorithmic performance evidence for production claims.