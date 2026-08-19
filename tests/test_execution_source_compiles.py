from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXECUTION_DIR = ROOT / "code" / "execution"


def test_every_execution_python_source_compiles():
    failures = []
    for path in sorted(EXECUTION_DIR.glob("*.py")):
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except SyntaxError as exc:
            failures.append(f"{path.name}:{exc.lineno}:{exc.msg}")

    assert not failures, "execution source compile failures: " + "; ".join(failures)
