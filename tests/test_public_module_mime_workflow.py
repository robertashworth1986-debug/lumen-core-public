import os
from pathlib import Path
import shutil
import subprocess
import textwrap
import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/repair-public-module-mime.yml'


def authorization_script():
    text = WORKFLOW.read_text(encoding='utf-8')
    block = text.split('name: Require exact main source, observed target and explicit scope', 1)[1]
    return textwrap.dedent(block.split('run: |', 1)[1].split('\n  repair:', 1)[0]).strip()


@pytest.mark.parametrize('field,value', [
    ('APPROVAL', 'HOLD'), ('WORKFLOW_REF', 'refs/heads/unreviewed'),
    ('SOURCE_COMMIT', 'b' * 40), ('SOURCE_COMMIT', 'main'),
    ('EXPECTED_MIME_SHA256', 'bad; echo should-not-run'),
])
def test_executed_authorization_script_rejects_unapproved_or_ambiguous_inputs(field, value):
    bash = str(Path('C:/Program Files/Git/bin/bash.exe')) if os.name == 'nt' else shutil.which('bash')
    if not bash or not Path(bash).exists():
        pytest.skip('Bash runtime unavailable')
    env = {**os.environ, 'APPROVAL': 'APPLY_PUBLIC_MJS_MIME',
        'SOURCE_COMMIT': 'a' * 40, 'WORKFLOW_SHA': 'a' * 40,
        'WORKFLOW_REF': 'refs/heads/main', 'EXPECTED_MIME_SHA256': 'c' * 64}
    assert subprocess.run([bash, '-c', authorization_script()], env=env, capture_output=True, timeout=10).returncode == 0
    env[field] = value
    assert subprocess.run([bash, '-c', authorization_script()], env=env, capture_output=True, timeout=10).returncode != 0


def test_production_is_manual_main_only_and_all_independent_failures_recover():
    text = WORKFLOW.read_text(encoding='utf-8')
    repair = text.split('\n  repair:', 1)[1]
    assert "if: github.event_name == 'workflow_dispatch'" in repair
    assert 'needs: [validate, authorize]' in repair
    assert 'name: production' in repair
    assert '$(git rev-parse origin/main)' in repair
    assert 'StrictHostKeyChecking=yes' in repair
    assert 'StrictHostKeyChecking=no' not in repair
    assert "always() && steps.apply.outcome == 'success'" in repair
    assert "steps.full_gate.outcome != 'success' || steps.service_gate.outcome != 'success'" in repair
    assert "--expected-candidate-sha256 '$CANDIDATE_SHA256'" in repair
    assert 'timeout 420s python3 code/ops/VERIFY_PUBLIC_SITE_LIVE_RELEASE.py' in repair
    assert 'concurrency:' not in text.split('jobs:', 1)[0]
    assert 'group: lumencore-production-site' in repair
    assert 'cancel-in-progress: false' in repair
    assert 'path: out/public-module-mime/*.json' in text
