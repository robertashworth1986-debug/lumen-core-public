import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = ROOT / "code" / "execution" / "execution_orchestrator.py"
UNIVERSE_ROUTER = ROOT / "code" / "execution" / "universe_router.py"


def orchestrator_tree() -> ast.Module:
    return ast.parse(ORCHESTRATOR.read_text(encoding="utf-8"))


def find_place_order(tree: ast.Module) -> ast.FunctionDef:
    router_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "UniversalExchangeRouter"
    )
    return next(
        node
        for node in router_class.body
        if isinstance(node, ast.FunctionDef) and node.name == "place_order"
    )


def test_router_requires_guard_context_before_any_exchange_order_call():
    method = find_place_order(orchestrator_tree())
    argument_names = [arg.arg for arg in method.args.args]
    calls = [node for node in ast.walk(method) if isinstance(node, ast.Call)]
    guard_calls = [
        node
        for node in calls
        if isinstance(node.func, ast.Attribute) and node.func.attr == "can_place_live_order"
    ]
    mutation_calls = [
        node
        for node in calls
        if isinstance(node.func, ast.Attribute)
        and node.func.attr in {"_place_alpaca_order", "_place_kraken_order", "_place_binance_order_fallback"}
    ]

    assert "guard_context" in argument_names
    assert guard_calls
    assert mutation_calls
    assert min(node.lineno for node in guard_calls) < min(node.lineno for node in mutation_calls)
    assert "human_action_time_authority_context_required" in ast.unparse(method)


def test_every_internal_router_order_call_supplies_guard_context():
    tree = orchestrator_tree()
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "router"
        and node.func.attr == "place_order"
    ]

    assert len(calls) == 2
    assert all(any(keyword.arg == "guard_context" for keyword in call.keywords) for call in calls)


def test_standalone_universe_router_has_no_direct_live_import_or_order_call():
    source = UNIVERSE_ROUTER.read_text(encoding="utf-8")

    assert "from execution_orchestrator import router" not in source
    assert "router.place_order" not in source
    assert "canonical_live_execution_stack_required" in source
