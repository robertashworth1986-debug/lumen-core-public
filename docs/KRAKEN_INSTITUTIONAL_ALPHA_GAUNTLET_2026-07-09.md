# Kraken Institutional Alpha Gauntlet - 2026-07-09

Purpose: harden Kraken alpha discovery toward institutional review by scoring signal quality, execution quality, liquidity/capacity, stress survivability, and replay readiness.

This gauntlet is paper research only. It is not investment advice and does not authorize live trading.

## Status

- Status: `INSTITUTIONAL_ALPHA_GAUNTLET_READY_LIVE_BLOCKED`
- Gauntlet rows: `8`
- Priority paper replay candidates: `0`
- Institutional research candidates: `0`
- Large-fund ready now: `0`
- Pairs discovered: `686`
- Pairs analyzed: `11`
- Paper control status: `KRAKEN_PAPER_INNOVATION_READY_LIVE_BLOCKED`
- Global runtime paper: `true`
- Kraken runtime paper: `true`
- Global live orders disabled: `true`
- Kraken live orders disabled: `true`
- Trading audit posture: `BLOCK_LIVE`
- Trading audit blockers: `3`
- Trusted with large fund now: `false`
- Order placement allowed: `false`
- Capital movement allowed: `false`
- Private credential use without human: `false`
- Gauntlet SHA-256: `b931dd179f32b103b2b39bab1cdd67074d705b1aeef20ea4cae291ab6fa5984f`

## Top Research Candidates

### 1. SYN/USD

- Pair: `SYNUSD`
- Strategy mode: `trend_follow_swing`
- Institutional tier: `watchlist_paper_research`
- Institutional alpha score: `67.171164`
- Signal / execution / capacity / stress / replay: `63.418721` / `84.816118` / `29.379268` / `83.962418` / `80.0`
- Capacity tier: `micro_paper_capacity_only`
- Conservative paper notional cap USD: `74.84`
- Large-fund capacity proven: `false`
- Promotion fail reasons: `capacity_not_institutional_yet`
- Allowed next step: `paper_replay_and_slippage_stress_only`
- Live order allowed: `false`
- Row SHA-256: `d4f19a342b3962588859494ef781ec2871934f5abc62f7f35b82e272db129636`

### 2. EVAA/USD

- Pair: `EVAAUSD`
- Strategy mode: `mean_reversion_snapback`
- Institutional tier: `watchlist_paper_research`
- Institutional alpha score: `59.967497`
- Signal / execution / capacity / stress / replay: `91.928909` / `53.975933` / `29.776726` / `18.970377` / `80.0`
- Capacity tier: `micro_paper_capacity_only`
- Conservative paper notional cap USD: `77.63`
- Large-fund capacity proven: `false`
- Promotion fail reasons: `execution_spread_too_weak_for_promotion, volatility_or_move_stress_too_high, capacity_not_institutional_yet`
- Allowed next step: `paper_replay_and_slippage_stress_only`
- Live order allowed: `false`
- Row SHA-256: `c886b982d16216400383e745ac14acc45c7548a6fb3537f893a8941fa9111249`

### 3. TLM/USD

- Pair: `TLMUSD`
- Strategy mode: `trend_follow_swing`
- Institutional tier: `watchlist_paper_research`
- Institutional alpha score: `59.013798`
- Signal / execution / capacity / stress / replay: `44.65228` / `84.955753` / `22.125283` / `81.845369` / `80.0`
- Capacity tier: `micro_paper_capacity_only`
- Conservative paper notional cap USD: `38.37`
- Large-fund capacity proven: `false`
- Promotion fail reasons: `capacity_not_institutional_yet`
- Allowed next step: `paper_replay_and_slippage_stress_only`
- Live order allowed: `false`
- Row SHA-256: `6dc9c2d3facf03e47b84ddc741171f093a6137a3415ce3815257de81a93a5e92`

### 4. ZEC/USD

- Pair: `XZECZUSD`
- Strategy mode: `watch`
- Institutional tier: `watchlist_paper_research`
- Institutional alpha score: `58.74509`
- Signal / execution / capacity / stress / replay: `22.272474` / `99.7669` / `43.256486` / `89.100441` / `80.0`
- Capacity tier: `small_fund_capacity_research_candidate`
- Conservative paper notional cap USD: `250.0`
- Large-fund capacity proven: `false`
- Promotion fail reasons: `strategy_mode_watch_only`
- Allowed next step: `paper_replay_and_slippage_stress_only`
- Live order allowed: `false`
- Row SHA-256: `79bff6e0b88c2d996261768c36e4c2cb23e4441a4c09eee7a1157f51fd1f628e`

### 5. BASED/USD

- Pair: `BASEDUSD`
- Strategy mode: `momentum_snipe`
- Institutional tier: `watchlist_paper_research`
- Institutional alpha score: `58.530771`
- Signal / execution / capacity / stress / replay: `57.271637` / `86.129925` / `18.429007` / `56.940999` / `80.0`
- Capacity tier: `micro_paper_capacity_only`
- Conservative paper notional cap USD: `27.3`
- Large-fund capacity proven: `false`
- Promotion fail reasons: `capacity_not_institutional_yet`
- Allowed next step: `paper_replay_and_slippage_stress_only`
- Live order allowed: `false`
- Row SHA-256: `5fee53422f89d5b00d43611ead0ce2b614332bd2cd6579107b6bb16e04a55db6`

## Institutional Standard

- Current level: `public_market_scan_plus_paper_gauntlet`
- Target level: `institutional_multi_month_replay_capacity_audit_before_any_live_promotion`

Promotion requirements:
- multi-month walk-forward replay across regimes
- independent data replay receipt
- depth and slippage model using live order book snapshots
- capacity and participation-rate limits
- drawdown, VaR, tail, liquidity, and exchange-outage stress tests
- fresh paper-trading heartbeats
- zero live-promotion blockers
- separate human action-time approval
- legal, tax, compliance, and custody review before outside capital

## Source Artifacts

- `out/ops/kraken_multi_tf_alpha_map_latest.json` present=`true` bytes=`26673` sha256=`b8cfb5f37cc108bccf8f8db9feafead4dc5cfe8c51a35f15a4f18842c574a48a`
- `out/ops/kraken_paper_innovation_control_room_latest.json` present=`true` bytes=`13523` sha256=`1be81f7d232db19c7d07baea14fd73b6e22c156614b6d11918c8ceae6f87c512`
- `out/ops/trading_stack_safety_audit_latest.json` present=`true` bytes=`1727` sha256=`3c8c805a9fea5ff3b5938412f1015f4e0fd6148dc7658524cb020f7e2d19e224`
- `config/runtime_control.json` present=`true` bytes=`14975` sha256=`ad8cb516d3145d43e39300f35ae03304efc58070bd643a2bf8ee5b177909c448`
- `config/accounts/KRAKEN_PRIMARY/runtime_control.json` present=`true` bytes=`489` sha256=`341775322d161c6f7fe96dce4ecfe264c6694d60a1df1c19c1f54b32fedf0e39`

## Claim Boundary

- This gauntlet ranks paper research candidates only.
- No row is approved for live orders or capital movement.
- No row is represented as suitable for a hedge fund without external audit, capacity evidence, and compliance review.
- No performance or profit claim is made.
