"""An empty or incomplete HTTP observation cannot prove a public release."""
from email.message import Message
from http.client import IncompleteRead
from io import BytesIO
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'code/ops/VERIFY_PUBLIC_SITE_LIVE_RELEASE.py'
COMMIT = 'a' * 40


@pytest.fixture
def subject():
    spec = importlib.util.spec_from_file_location('live_verification_bounds', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Response:
    status = 200
    def __init__(self, body=b'abc', error=None):
        self.stream, self.read_sizes, self.error = BytesIO(body), [], error
        self.headers = Message()
        self.headers['Content-Type'] = 'text/css'
        self.closed = False
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.closed = True
    def read(self, size=-1):
        self.read_sizes.append(size)
        if self.error:
            raise self.error
        return self.stream.read(size)


def manifest_file(tmp_path, *, names=('assets/a.css',), body=b'abc', byte_count=None):
    rows = [{'archive_name': name, 'repo_path': f'dashboard/{name}', 'install_mode': '0644',
             'git_blob_oid': 'b' * 40, 'sha256': hashlib.sha256(body).hexdigest(),
             'bytes': len(body) if byte_count is None else byte_count} for name in names]
    data = {'schema': 'lumencore.public_site_release_manifest.v1', 'source_commit': COMMIT,
            'target_directory': '/opt/lumencore/dashboard', 'archive_sha256': 'c' * 64,
            'file_count': len(rows), 'files': rows}
    path = tmp_path / 'manifest.json'
    path.write_text(json.dumps(data))
    return path, data


def verify(subject, path, **kwargs):
    return subject.verify(manifest_path=path, source_commit=COMMIT,
                          base_url='https://example.invalid', timeout=kwargs.get('timeout', 1))


def test_empty_manifest_is_rejected_without_http(tmp_path, subject, monkeypatch):
    path, _ = manifest_file(tmp_path, names=())
    calls = []
    monkeypatch.setattr(subject, 'urlopen', lambda *a, **k: calls.append(a))
    with pytest.raises(ValueError, match='manifest file rows'):
        verify(subject, path)
    assert calls == []


def test_all_manifest_rows_are_validated_before_http(tmp_path, subject, monkeypatch):
    path, data = manifest_file(tmp_path, names=('assets/a.css', 'assets/b.css'))
    data['files'][1]['unexpected'] = True
    path.write_text(json.dumps(data))
    calls = []
    def opener(*a, **k):
        calls.append(a)
        return Response()
    monkeypatch.setattr(subject, 'urlopen', opener)
    with pytest.raises(ValueError, match='manifest file row'):
        verify(subject, path)
    assert calls == []


@pytest.mark.parametrize('timeout', [0, -1, float('inf'), float('nan'), True])
def test_invalid_timeout_is_rejected_before_http(tmp_path, subject, monkeypatch, timeout):
    path, _ = manifest_file(tmp_path)
    calls = []
    def opener(*a, **k):
        calls.append(a)
        return Response()
    monkeypatch.setattr(subject, 'urlopen', opener)
    with pytest.raises(ValueError, match='timeout'):
        verify(subject, path, timeout=timeout)
    assert calls == []


def test_http_read_is_bounded_and_exact_bytes_pass(tmp_path, subject, monkeypatch):
    path, _ = manifest_file(tmp_path)
    response = Response()
    monkeypatch.setattr(subject, 'urlopen', lambda *a, **k: response)
    result = verify(subject, path)
    assert result['release_verified'] is True
    assert response.read_sizes == [4] and response.closed


def test_oversized_http_body_reports_error_without_a_prefix_hash(tmp_path, subject, monkeypatch):
    path, _ = manifest_file(tmp_path)
    response = Response(b'abc' * 100)
    monkeypatch.setattr(subject, 'urlopen', lambda *a, **k: response)
    result = verify(subject, path)
    assert result['release_verified'] is False
    row = result['results'][0]
    assert row['status'] == 'ERROR' and 'exceeds declared byte count' in row['detail']
    assert 'actual_sha256' not in row
    assert response.read_sizes == [4] and response.closed


def test_matching_hash_does_not_override_wrong_manifest_byte_count(tmp_path, subject, monkeypatch):
    path, _ = manifest_file(tmp_path, byte_count=9)
    monkeypatch.setattr(subject, 'urlopen', lambda *a, **k: Response())
    result = verify(subject, path)
    assert result['results'][0]['status'] == 'MISMATCH'
    assert result['release_verified'] is False


@pytest.mark.parametrize('error', [IncompleteRead(b'partial', 5), ConnectionResetError('fixture reset')])
def test_incomplete_response_is_recorded_and_other_files_are_checked(tmp_path, subject, monkeypatch, error):
    path, _ = manifest_file(tmp_path, names=('assets/a.css', 'assets/b.css'))
    responses = iter([Response(error=error), Response()])
    monkeypatch.setattr(subject, 'urlopen', lambda *a, **k: next(responses))
    result = verify(subject, path)
    assert [r['status'] for r in result['results']] == ['ERROR', 'MATCH']
    assert result['matched_file_count'] == 1 and not result['release_verified']


def test_huge_declared_response_is_rejected_before_http(tmp_path, subject, monkeypatch):
    path, _ = manifest_file(tmp_path, byte_count=129 * 1024 * 1024)
    calls = []
    monkeypatch.setattr(subject, 'urlopen', lambda *a, **k: calls.append(a))
    with pytest.raises(ValueError, match='byte budget'):
        verify(subject, path)
    assert calls == []


@pytest.mark.parametrize('field,value', [('archive_name', 5), ('sha256', 10**63), ('git_blob_oid', 10**39)])
def test_nonstring_identifiers_are_not_coerced_into_a_valid_manifest(tmp_path, subject, monkeypatch, field, value):
    path, data = manifest_file(tmp_path)
    data['files'][0][field] = value
    if field == 'archive_name':
        data['files'][0]['repo_path'] = 'dashboard/5'
    path.write_text(json.dumps(data))
    calls = []
    monkeypatch.setattr(subject, 'urlopen', lambda *a, **k: calls.append(a))
    with pytest.raises(ValueError, match='identifiers must be strings'):
        verify(subject, path)
    assert calls == []


def test_total_declared_byte_budget_is_enforced(tmp_path, subject, monkeypatch):
    path, _ = manifest_file(tmp_path, names=('a.css', 'b.css'), byte_count=70*1024*1024)
    calls = []
    monkeypatch.setattr(subject, 'urlopen', lambda *a, **k: calls.append(a))
    with pytest.raises(ValueError, match='byte budget'):
        verify(subject, path)
    assert calls == []


def test_manifest_input_has_a_byte_limit(tmp_path, subject):
    path = tmp_path/'oversized.json'
    path.write_bytes(b' ' * (1024*1024+1))
    with pytest.raises(ValueError, match='manifest exceeds byte budget'):
        subject.load_manifest(path)
