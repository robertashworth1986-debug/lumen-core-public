# Kraken Paper Innovation Control Room - 2026-07-09

Purpose: connect Kraken market evidence to LumenCore's paper/replay innovation loop while keeping private credentials, live orders, and capital movement outside the automation boundary.

This packet is not investment advice and does not authorize trading.

## Status

- Status: `KRAKEN_PAPER_INNOVATION_READY_LIVE_BLOCKED`
- Public alpha map present: `true`
- Paper research cards: `8`
- Pairs discovered: `686`
- Pairs after liquidity filter: `12`
- Pairs analyzed: `11`
- Pair errors: `1`
- Global runtime paper: `true`
- Kraken runtime paper: `true`
- Global live orders disabled: `true`
- Kraken live orders disabled: `true`
- Live arm off: `true`
- Trading audit posture: `BLOCK_LIVE`
- Trading audit blockers: `3`
- Live promotion blocked: `true`
- Private API use without human: `false`
- Validate-only without action-time approval: `false`
- Order placement allowed: `false`
- Capital movement allowed: `false`
- Keys loaded by this packet: `false`
- Packet SHA-256: `4f4b881cf0df5ba9a840927ed73ab229231ab30006b0be395eccb9f31f4488bf`

## Paper Research Cards

### 1. EVAA/USD

- Pair: `EVAAUSD`
- Strategy mode: `mean_reversion_snapback`
- Paper research mode: `paper_reversion_decay_test`
- Alpha edge score: `21.483397`
- Momentum / trend / reversion: `11.3415` / `53.369038` / `15.623129`
- Spread bps: `30.313237`
- 24h turnover USD: `1552633.81`
- 24h range pct: `84.623549`
- 24h change pct: `-24.884343`
- Replay entry hour UTC: `6`
- Replay exit hour UTC: `10`
- Allowed next step: `paper_replay_ticket_only`
- Blocked next steps: `no_live_order, no_private_api_order, no_position_size_change, no_capital_movement`
- Risk notes: `wide_spread_replay_only, high_intraday_range_requires_slippage_stress, large_24h_move_requires_no_chase_rule`
- Card SHA-256: `a50907bd53567e6481a87beac0c95eeb79215ca019679c6f1cd2f574947ff41d`

### 2. BASED/USD

- Pair: `BASEDUSD`
- Strategy mode: `momentum_snipe`
- Paper research mode: `paper_momentum_confirmation`
- Alpha edge score: `14.536689`
- Momentum / trend / reversion: `20.740122` / `9.262284` / `0.0`
- Spread bps: `12.628541`
- 24h turnover USD: `545959.33`
- 24h range pct: `31.694817`
- 24h change pct: `26.9874`
- Replay entry hour UTC: `3`
- Replay exit hour UTC: `0`
- Allowed next step: `paper_replay_ticket_only`
- Blocked next steps: `no_live_order, no_private_api_order, no_position_size_change, no_capital_movement`
- Risk notes: `lower_turnover_size_cap_required, large_24h_move_requires_no_chase_rule`
- Card SHA-256: `6428a228c21037651c2e318077558c03c90afa71ce64f9a63872c62ed0150eac`

### 3. SYN/USD

- Pair: `SYNUSD`
- Strategy mode: `trend_follow_swing`
- Paper research mode: `paper_trend_persistence_test`
- Alpha edge score: `12.798554`
- Momentum / trend / reversion: `2.350505` / `35.862534` / `6.974393`
- Spread bps: `13.351135`
- 24h turnover USD: `1496823.88`
- 24h range pct: `13.657817`
- 24h change pct: `5.88069`
- Replay entry hour UTC: `10`
- Replay exit hour UTC: `17`
- Allowed next step: `paper_replay_ticket_only`
- Blocked next steps: `no_live_order, no_private_api_order, no_position_size_change, no_capital_movement`
- Risk notes: `standard_paper_gate`
- Card SHA-256: `2c4345a627ad9a5751e561ccabed22e4f66d197226cfa9feabfe1f24bd1bda94`

### 4. SENT/USD

- Pair: `SENTUSD`
- Strategy mode: `watch`
- Paper research mode: `paper_watch_only`
- Alpha edge score: `8.73659`
- Momentum / trend / reversion: `7.89045` / `7.577044` / `0.0`
- Spread bps: `24.469356`
- 24h turnover USD: `319044.32`
- 24h range pct: `40.078426`
- 24h change pct: `28.448213`
- Replay entry hour UTC: `0`
- Replay exit hour UTC: `18`
- Allowed next step: `paper_replay_ticket_only`
- Blocked next steps: `no_live_order, no_private_api_order, no_position_size_change, no_capital_movement`
- Risk notes: `lower_turnover_size_cap_required, high_intraday_range_requires_slippage_stress, large_24h_move_requires_no_chase_rule`
- Card SHA-256: `f5dadf8471eaf5d2268d4dbde18025d9ad9c49b63dbdb61ec731f7b80065b9db`

### 5. TLM/USD

- Pair: `TLMUSD`
- Strategy mode: `trend_follow_swing`
- Paper research mode: `paper_trend_persistence_test`
- Alpha edge score: `8.176728`
- Momentum / trend / reversion: `-1.34911` / `20.898152` / `5.057471`
- Spread bps: `13.274336`
- 24h turnover USD: `767381.47`
- 24h range pct: `16.175804`
- 24h change pct: `-6.495656`
- Replay entry hour UTC: `16`
- Replay exit hour UTC: `22`
- Allowed next step: `paper_replay_ticket_only`
- Blocked next steps: `no_live_order, no_private_api_order, no_position_size_change, no_capital_movement`
- Risk notes: `lower_turnover_size_cap_required`
- Card SHA-256: `7774d0d629d7254006ced58d842c54ee2c5234c660e03e378cdda5abe5e2b457`

### 6. ZEC/USD

- Pair: `XZECZUSD`
- Strategy mode: `watch`
- Paper research mode: `paper_watch_only`
- Alpha edge score: `7.466684`
- Momentum / trend / reversion: `4.981974` / `5.247167` / `0.0`
- Spread bps: `5.128205`
- 24h turnover USD: `5373526.97`
- 24h range pct: `8.905975`
- 24h change pct: `4.629451`
- Replay entry hour UTC: `19`
- Replay exit hour UTC: `1`
- Allowed next step: `paper_replay_ticket_only`
- Blocked next steps: `no_live_order, no_private_api_order, no_position_size_change, no_capital_movement`
- Risk notes: `standard_paper_gate`
- Card SHA-256: `9df2d8d0c992e768c4f95f9503ea980a70bbfa84d4f322bf64e2197deb8f614c`

### 7. ESPORTS/USD

- Pair: `ESPORTSUSD`
- Strategy mode: `watch`
- Paper research mode: `paper_watch_only`
- Alpha edge score: `5.679233`
- Momentum / trend / reversion: `12.148717` / `-13.534224` / `8.755733`
- Spread bps: `46.948357`
- 24h turnover USD: `1514401.75`
- 24h range pct: `46.496815`
- 24h change pct: `32.298137`
- Replay entry hour UTC: `19`
- Replay exit hour UTC: `15`
- Allowed next step: `paper_replay_ticket_only`
- Blocked next steps: `no_live_order, no_private_api_order, no_position_size_change, no_capital_movement`
- Risk notes: `wide_spread_replay_only, high_intraday_range_requires_slippage_stress, large_24h_move_requires_no_chase_rule`
- Card SHA-256: `343a44ce33a3ee28ef4f16a443786879134f5cd975efa4910b7270f51da30c5f`

### 8. ARB/USD

- Pair: `ARBUSD`
- Strategy mode: `watch`
- Paper research mode: `paper_watch_only`
- Alpha edge score: `5.400415`
- Momentum / trend / reversion: `2.66325` / `2.06974` / `0.0`
- Spread bps: `22.522523`
- 24h turnover USD: `677153.37`
- 24h range pct: `19.084967`
- 24h change pct: `15.625`
- Replay entry hour UTC: `12`
- Replay exit hour UTC: `17`
- Allowed next step: `paper_replay_ticket_only`
- Blocked next steps: `no_live_order, no_private_api_order, no_position_size_change, no_capital_movement`
- Risk notes: `lower_turnover_size_cap_required`
- Card SHA-256: `24313adf7a17c30f16e0c7f05b51c3f76a3119dbc88180d2e5658f6f0699309b`

## Innovation Protocol

Allowed now:
- public Kraken market scans
- paper replay tickets
- watchlist scoring
- spread and slippage stress tests
- validate-only smoke-test planning without secrets

Blocked now:
- private endpoint calls without action-time approval
- live orders
- auto-fire
- withdrawals
- collateral conversion
- position-size escalation
- profit or return promises

Promotion requirements:
- fresh executor heartbeat
- fresh autofire heartbeat
- growth controller health OK
- zero trading audit blockers
- paper replay receipt for selected pair
- validate-only smoke test explicitly approved by human
- separate human action-time approval for any live order

## Key Policy

- registry_note: Keys may exist in the local registry, but this packet does not read, print, hydrate, or use them.
- secret_handling: Private credentials stay outside the control-room artifact. Any key verification must report presence only and never display secret values.
- safe_next_private_step: Only a human-approved validate-only smoke test with validate=true may use private credentials before any live path is considered.

## Source Artifacts

- `config/runtime_control.json` present=`true` bytes=`14975` sha256=`ad8cb516d3145d43e39300f35ae03304efc58070bd643a2bf8ee5b177909c448`
- `config/accounts/KRAKEN_PRIMARY/runtime_control.json` present=`true` bytes=`489` sha256=`341775322d161c6f7fe96dce4ecfe264c6694d60a1df1c19c1f54b32fedf0e39`
- `out/execution_status.json` present=`true` bytes=`211` sha256=`4c206c4c8120a23c496b6f0aa1a46cd8df723b947e490ff1bfa88ed9c9c0a64a`
- `out/ops/kraken_multi_tf_alpha_map_latest.json` present=`true` bytes=`26673` sha256=`b8cfb5f37cc108bccf8f8db9feafead4dc5cfe8c51a35f15a4f18842c574a48a`
- `out/ops/trading_stack_safety_audit_latest.json` present=`true` bytes=`1727` sha256=`3c8c805a9fea5ff3b5938412f1015f4e0fd6148dc7658524cb020f7e2d19e224`
- `out/ops/autonomous_quant_governance_packet_latest.json` present=`true` bytes=`10038` sha256=`fb2fa17cfc4da39ec4c95659e679462fba202af881d2ebad4307419261a77c81`

## Claim Boundary

- Research cards are not investment advice.
- Scores are public-market research signals, not buy/sell instructions.
- No live trading, order placement, capital movement, account change, or private API use is authorized by this packet.
- No performance, profit, or guaranteed-safety claim is made.
