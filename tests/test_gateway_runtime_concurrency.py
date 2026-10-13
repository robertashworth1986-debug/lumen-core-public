from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest


CODE = Path(__file__).resolve().parents[1] / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))


@pytest.fixture
def legacy(monkeypatch, tmp_path):
    import luma_experience_gateway_legacy as gateway

    # Only fictional local state; a forgotten external call fails the fixture.
    def forbidden(*args, **kwargs):
        raise AssertionError("external transport is forbidden in gateway fixture")

    monkeypatch.setattr(gateway._requests_appr, "get", forbidden)
    monkeypatch.setattr(gateway._requests_appr, "post", forbidden)
    monkeypatch.setattr(gateway, "PROFIT_LOCK_PEAKS_FILE", tmp_path / "peaks.json")
    monkeypatch.setattr(gateway, "_PROFIT_LOCK_STATE", {})
    monkeypatch.setattr(gateway, "_AUTOBUY_STATE", {})
    monkeypatch.setattr(gateway, "_SMART_SCANNER_STATE", {})
    monkeypatch.setattr(gateway, "_load_profit_lock_cfg", lambda: {"enabled": True, "scan_interval_s": 30})
    monkeypatch.setattr(gateway, "api_positions_live", lambda: {"lots_open": [
        {"pair": "FIXTUREUSD", "remaining": 1.0, "price": 100.0, "txid": "synthetic-lot"}
    ]})
    monkeypatch.setattr(gateway, "_resolve_fill_prices", lambda ids: {})
    monkeypatch.setattr(gateway, "_evaluate_lot_exit", lambda lot, cfg, peak: {"action": "hold"})
    return gateway


async def _thread_started(event):
    assert await asyncio.to_thread(event.wait, 2), "fixture callback did not start"


def test_real_profit_watcher_keeps_event_loop_responsive_during_delayed_transport(legacy, monkeypatch):
    started, release = threading.Event(), threading.Event()
    transport_threads = []

    class Response:
        def json(self):
            return {"result": {"FIXTUREUSD": {"c": ["100.0"]}}}

    def delayed_get(url, *, timeout):
        assert "Ticker" in url and timeout == 8
        transport_threads.append(threading.current_thread())
        started.set()
        assert release.wait(2), "test did not release delayed transport"
        return Response()

    monkeypatch.setattr(legacy._requests_appr, "get", delayed_get)

    async def exercise():
        queue = legacy.GatewayBlockingQueue()
        monkeypatch.setattr(legacy, "_GATEWAY_BLOCKING_QUEUE", queue)
        watcher = asyncio.create_task(legacy._profit_lock_watcher())
        try:
            await _thread_started(started)
            # The real watcher -> candidates -> unrealized -> ticker path runs.
            # A blocked event loop would prevent this deadline from completing.
            await asyncio.wait_for(asyncio.sleep(0.02), timeout=0.2)
            assert transport_threads[0] is not threading.current_thread()
            assert not watcher.done()
        finally:
            release.set()
            watcher.cancel()
            await asyncio.gather(watcher, return_exceptions=True)
            await queue.close()
        assert legacy._PROFIT_LOCK_STATE["last_scan_actionable"] == 0

    asyncio.run(exercise())


def test_manual_scanner_route_preserves_flags_and_shares_one_serialized_thread(legacy, monkeypatch, tmp_path):
    started, release = threading.Event(), threading.Event()
    state = tmp_path / "fictional-state.json"
    state.write_text('{"count": 0}', encoding="utf-8")
    calls = []

    def delayed_tick(**flags):
        calls.append(flags)
        current = json.loads(state.read_text())["count"]
        if len(calls) == 1:
            started.set()
            assert release.wait(2)
        current += 1
        state.write_text(json.dumps({"count": current}))
        return {"count": current, "effective_interval_s": 30}

    class Request:
        async def json(self):
            return {"force": False, "run_spike": False, "run_alpha": False}

    monkeypatch.setattr(legacy, "_smart_scanner_tick", delayed_tick)

    async def exercise():
        queue = legacy.GatewayBlockingQueue()
        monkeypatch.setattr(legacy, "_GATEWAY_BLOCKING_QUEUE", queue)
        first = asyncio.create_task(legacy.api_smart_scanner_run(Request()))
        second = None
        try:
            await _thread_started(started)
            second = asyncio.create_task(legacy.api_smart_scanner_run(Request()))
            await asyncio.wait_for(asyncio.sleep(0.02), timeout=0.2)
            assert len(calls) == 1  # No concurrent read/modify/write transaction.
            release.set()
            results = await asyncio.gather(first, second)
            assert [result["result"]["count"] for result in results] == [1, 2]
            assert all(flags == {"force": False, "run_spike": False, "run_alpha": False} for flags in calls)
            assert json.loads(state.read_text()) == {"count": 2}
        finally:
            release.set()
            await asyncio.gather(*[task for task in (first, second) if task is not None], return_exceptions=True)
            await queue.close()

    asyncio.run(exercise())


def test_queue_bounds_pending_work_and_discards_cancelled_actions(legacy):
    started, release = threading.Event(), threading.Event()
    executed = []

    def delayed():
        started.set()
        assert release.wait(2)
        executed.append("running")

    async def exercise():
        queue = legacy.GatewayBlockingQueue(max_pending=1)
        first = asyncio.create_task(queue.run(delayed))
        queued = None
        try:
            await _thread_started(started)
            queued = asyncio.create_task(queue.run(executed.append, "cancelled"))
            await asyncio.sleep(0)
            with pytest.raises(legacy.HTTPException) as error:
                await queue.run(executed.append, "overflow")
            assert error.value.status_code == 503
            queued.cancel()
            await asyncio.gather(queued, return_exceptions=True)
            release.set()
            await first
        finally:
            release.set()
            await queue.close()
        assert executed == ["running"]
        with pytest.raises(legacy.HTTPException) as error:
            await queue.run(executed.append, "after_shutdown")
        assert error.value.status_code == 503

    asyncio.run(exercise())


def test_shutdown_waits_for_running_state_transaction_and_refuses_queued_work(legacy):
    started, release = threading.Event(), threading.Event()
    executed = []

    def delayed():
        started.set()
        assert release.wait(2)
        executed.append("completed")

    async def exercise():
        queue = legacy.GatewayBlockingQueue()
        running = asyncio.create_task(queue.run(delayed))
        queued = None
        shutdown = None
        try:
            await _thread_started(started)
            queued = asyncio.create_task(queue.run(executed.append, "should_not_run"))
            await asyncio.sleep(0)
            shutdown = asyncio.create_task(queue.close())
            await asyncio.sleep(0.02)
            assert not shutdown.done()
            with pytest.raises(legacy.HTTPException) as error:
                await queued
            assert error.value.status_code == 503
            release.set()
            await asyncio.gather(running, shutdown)
        finally:
            release.set()
            if shutdown is None:
                await queue.close()
            else:
                await shutdown
        assert executed == ["completed"]

    asyncio.run(exercise())


def test_disabled_watchers_do_not_enable_or_invoke_scans(legacy, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("disabled worker must not scan")

    profit = {"enabled": False, "scan_interval_s": 30}
    autobuy = {"enabled": False, "scan_interval_s": 60}
    monkeypatch.setattr(legacy, "_load_profit_lock_cfg", lambda: profit)
    monkeypatch.setattr(legacy, "_load_autobuy_cfg", lambda: autobuy)
    monkeypatch.setattr(legacy, "api_sells_candidates", forbidden)
    monkeypatch.setattr(legacy, "_autobuy_scan_once", forbidden)
    assert legacy._profit_lock_tick() == 30
    assert legacy._autobuy_tick() == 60
    assert profit["enabled"] is False and autobuy["enabled"] is False


def test_sync_route_state_transactions_cannot_overlap_queue_transactions(legacy):
    started, release = threading.Event(), threading.Event()
    order = []

    def first():
        started.set()
        assert release.wait(2)
        order.append("queue")

    @legacy._serialized_gateway_state
    def sync_route():
        order.append("sync_route")

    async def exercise():
        queue = legacy.GatewayBlockingQueue()
        running = asyncio.create_task(queue.run(first))
        other = None
        try:
            await _thread_started(started)
            other = asyncio.create_task(asyncio.to_thread(sync_route))
            await asyncio.sleep(0.02)
            assert order == []
            release.set()
            await asyncio.gather(running, other)
            assert order == ["queue", "sync_route"]
        finally:
            release.set()
            await queue.close()

    asyncio.run(exercise())


def test_import_and_module_reload_do_not_create_runtime_lock(tmp_path):
    script = '''
import importlib
from pathlib import Path
import luma_experience_gateway_legacy as gateway
assert not gateway._GATEWAY_LOCK.exists()
assert not gateway._GATEWAY_LOCK.parent.exists()
importlib.reload(gateway)
assert not gateway._GATEWAY_LOCK.parent.exists()
print("IMPORT_ONLY_NO_RUNTIME_LOCK")
'''
    env = {**os.environ, "PYTHONPATH": str(CODE), "LUMA_STACK_ROOT": str(tmp_path),
           "LUMA_DASHBOARD_DIR": str(tmp_path / "dashboard")}
    result = subprocess.run([sys.executable, "-c", script], env=env, cwd=tmp_path,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "IMPORT_ONLY_NO_RUNTIME_LOCK"


def test_explicit_minimal_profile_imports_no_legacy_graph_and_keeps_features_hold(tmp_path):
    script = '''
import asyncio, sys
import httpx
import luma_experience_gateway as gateway
assert "luma_experience_gateway_legacy" not in sys.modules
async def check():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=gateway.app), base_url="http://synthetic-test") as client:
        public = await client.get("/health")
        assert public.status_code == 200 and public.json()["public_surface"] == "minimal"
        headers = {"Authorization": "Bearer " + "synthetic-minimal-profile-token-0000"}
        operator = await client.get("/api/operator/health", headers=headers)
        assert operator.status_code == 200
        assert operator.json()["operational_readiness"] == "HOLD"
        assert operator.json()["background_workers"] == "not_started"
        for path in ("/api/scanner/smart/run", "/api/buys/autobuy/run", "/api/grants/draft"):
            response = await client.post(path, headers=headers, json={})
            assert response.status_code == 503
asyncio.run(check())
print("MINIMAL_PROFILE_HOLD")
'''
    env = {**os.environ, "PYTHONPATH": str(CODE), "LUMA_GATEWAY_SERVING_PROFILE": "minimal",
           "LUMA_STACK_ROOT": str(tmp_path), "LUMA_OPERATOR_API_TOKEN": "synthetic-minimal-profile-token-0000",
           "LUMA_OPERATOR_API_TOKENS": ""}
    result = subprocess.run([sys.executable, "-c", script], env=env, cwd=tmp_path,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "MINIMAL_PROFILE_HOLD"
    assert not (tmp_path / "run").exists()


@pytest.mark.parametrize("route,loader,saver", [
    ("api_sells_config_set", "_load_profit_lock_cfg", "_save_profit_lock_cfg"),
    ("api_smart_scanner_set_config", "_load_smart_scanner_cfg", "_save_smart_scanner_cfg"),
    ("api_autobuy_set_config", "_load_autobuy_cfg", "_save_autobuy_cfg"),
])
def test_async_config_writes_share_transaction_queue_and_preserve_disabled_flags(legacy, monkeypatch, tmp_path,
                                                                               route, loader, saver):
    started, release = threading.Event(), threading.Event()
    state = tmp_path / "fictional-config.json"
    original = {"enabled": True, "existing_unknown_field": "retained"}
    state.write_text(json.dumps(original))
    monkeypatch.setattr(legacy, loader, lambda: json.loads(state.read_text()))
    monkeypatch.setattr(legacy, saver, lambda payload: state.write_text(json.dumps(payload)))

    def occupied():
        started.set()
        assert release.wait(2)

    class Request:
        async def json(self):
            return {"enabled": False, "unexpected_request_field": True}

    async def exercise():
        queue = legacy.GatewayBlockingQueue()
        monkeypatch.setattr(legacy, "_GATEWAY_BLOCKING_QUEUE", queue)
        first = asyncio.create_task(queue.run(occupied))
        update = None
        try:
            await _thread_started(started)
            update = asyncio.create_task(getattr(legacy, route)(Request()))
            await asyncio.sleep(0.02)
            assert json.loads(state.read_text()) == original
            release.set()
            await first
            result = await update
            assert result["config"] == {"enabled": False, "existing_unknown_field": "retained"}
            assert json.loads(state.read_text()) == result["config"]
        finally:
            release.set()
            await queue.close()

    asyncio.run(exercise())


def test_facade_reload_keeps_validate_only_gate_without_recursive_wrapping(tmp_path):
    script = '''
import importlib
import luma_experience_gateway_legacy as legacy
calls = []
def synthetic_adapter(payload):
    calls.append(payload)
    return {"result": {"synthetic_fixture": True}}
legacy._kraken_add_order = synthetic_adapter
import luma_experience_gateway as gateway
importlib.reload(gateway)
payload = {"pair": "XBTUSD", "type": "buy", "ordertype": "market", "volume": "0.001", "validate": "true"}
assert gateway._kraken_add_order(payload) == {"result": {"synthetic_fixture": True}}
assert len(calls) == 1
assert gateway._kraken_add_order({**payload, "validate": "false"})["error"]
assert len(calls) == 1
print("RELOAD_GATE_PRESERVED")
'''
    env = {**os.environ, "PYTHONPATH": str(CODE), "LUMA_STACK_ROOT": str(tmp_path),
           "LUMA_DASHBOARD_DIR": str(tmp_path / "dashboard"), "LUMA_GATEWAY_SERVING_PROFILE": "operator"}
    result = subprocess.run([sys.executable, "-c", script], env=env, cwd=tmp_path,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "RELOAD_GATE_PRESERVED"
