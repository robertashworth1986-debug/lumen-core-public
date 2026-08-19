import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATEWAY = ROOT / "code" / "luma_experience_gateway.py"


def gateway_tree() -> ast.Module:
    return ast.parse(GATEWAY.read_text(encoding="utf-8"))


def function_named(tree: ast.Module, name: str) -> ast.FunctionDef:
    return next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )


def test_real_order_path_rechecks_action_time_authority_before_kraken_submit():
    method = function_named(gateway_tree(), "master_approval_decide")
    calls = [node for node in ast.walk(method) if isinstance(node, ast.Call)]
    authority_calls = [
        node
        for node in calls
        if isinstance(node.func, ast.Name)
        and node.func.id == "_live_action_time_authority"
    ]
    order_calls = [
        node
        for node in calls
        if isinstance(node.func, ast.Name) and node.func.id == "_kraken_add_order"
    ]

    assert len(authority_calls) >= 2
    assert len(order_calls) == 1
    assert max(node.lineno for node in authority_calls) < order_calls[0].lineno
    assert "human_action_time_authority_required" in ast.unparse(method)


def test_gateway_authority_is_bound_to_canonical_runtime_receipt_and_controller():
    helper = function_named(gateway_tree(), "_live_action_time_authority")
    source = ast.unparse(helper)

    assert "RUNTIME_CONTROL_FILE" in source
    assert "LIVE_ACTION_RECEIPT_FILE" in source
    assert "controller=controller" in source
    assert "ttl_seconds=300" in source


def test_gateway_keeps_human_unlock_and_exact_ticket_phrase_layers():
    source = GATEWAY.read_text(encoding="utf-8")

    assert "LUMA_HUMAN_UNLOCK_TOKEN" in source
    assert 'expected_phrase = f"FIRE {ticket.get(\'ticket_id\')}"' in source
    assert "validate_live_action_authority" in source
