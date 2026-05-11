# Meta-Engine Integration Checklist

This checklist will help you verify that all modular engines, data sources, and dashboards are working together in tandem for your institutional stack. Mark each item as you confirm it.

## 1. Orchestrator Health
- [ ] Orchestrator process is running (see orchestrator logs)
- [ ] Watchdog is monitoring all critical logs and restarting modules if needed

## 2. Modular Engine Launch
- [ ] All modular engines (signal, execution, risk, analytics, infra, sports, etc.) are launched by the orchestrator
- [ ] Engines are discoverable and can be hot-reloaded/restarted

## 3. Data Ingestion & Flow
- [ ] Sports data is being ingested and updated in sports_data/
- [ ] Infra/engineering data is being ingested and updated in clean_data/ or relevant folders
- [ ] All engines are reading from the correct live data folders

## 4. Signal & Strategy Processing
- [ ] Signal engines are generating signals from all available data sources
- [ ] Infra modules are running advanced metrics and Monte Carlo backtests
- [ ] Results are being written to unified output locations (e.g., out/ or dashboard/)

## 5. Execution & Audit
- [ ] Execution orchestrator is firing on high-edge opportunities in real time
- [ ] All executions are logged with full audit chain and hashed/frozen delta outputs

## 6. Dashboard & Visualization
- [ ] Dashboard is live and updating with real execution stats and infra facts
- [ ] Only trusted, hashed/frozen, or live stats are displayed (no unverified data)

## 7. Continuous Loop & Evolution
- [ ] All modules are running in continuous loops (no manual intervention required)
- [ ] Orchestrator can restart/recover any failed module automatically
- [ ] New data and strategies are incorporated without downtime

---

If any item is not checked, investigate the corresponding logs, configs, or code modules. For wiring up a specific module, focus on its section above and ensure its inputs/outputs are connected to the orchestrator and dashboard.
