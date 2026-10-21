#!/usr/bin/env python3
"""Read active Nginx MIME evidence; never change configuration or service state."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path('/opt/lumencore/dashboard')
EXPECTED = {
    'bounded-light/observatory/geometry.mjs': '645f826e9e31ba3c3f49edd63bb7b63eee8ab5f5af1593bad3b23ff426d70d1b',
    'portfolio/math-models.mjs': 'a08c96232c0fe6c246fae33c68835149d5febcb3d00d35ca4add45119b336d9b',
    'portfolio/portfolio-model.mjs': '1952beb45c5526fe56a226ae256baccbaadf7f7781b864e7e73fec2396db11c8',
}


def inspect_dump(dump: str, metadata: bool = True) -> dict:
    """Expose only MIME and public routing declarations, never raw Nginx config."""
    sections = re.split(r'^# configuration file (.+):\s*$', dump, flags=re.M)
    evidence = []
    for index in range(1, len(sections), 2):
        filename, content = sections[index], sections[index + 1]
        path = PurePosixPath(filename)
        if not re.fullmatch(r'/etc/nginx/[A-Za-z0-9_./-]+', filename) or '..' in path.parts:
            continue
        facts = []
        has_js_mapping = False
        for number, raw in enumerate(content.splitlines(), 1):
            line = raw.split('#', 1)[0].strip()
            if re.fullmatch(r'(?:application|text)/javascript\s+[A-Za-z0-9_.+\-\s]+;', line):
                mime, extensions = line[:-1].split(None, 1)
                facts.append({'line': number, 'kind': 'javascript_mapping', 'mime': mime, 'extensions': extensions.split()})
                has_js_mapping = True
            elif re.fullmatch(r'[A-Za-z0-9.+\-/]+\s+(?:[A-Za-z0-9_.+\-]+\s+)*mjs(?:\s+[A-Za-z0-9_.+\-]+)*\s*;', line):
                mime, extensions = line[:-1].split(None, 1)
                facts.append({'line': number, 'kind': 'other_mjs_mapping', 'mime': mime, 'extensions': extensions.split()})
            elif line.startswith('server_name ') and line.endswith(';'):
                names = [name for name in line[len('server_name '):-1].split() if name == 'lumen-core.ai' or name.endswith('.lumen-core.ai')]
                if names:
                    facts.append({'line': number, 'kind': 'public_server_names', 'names': names})
            elif re.fullmatch(r'include\s+/etc/nginx/[A-Za-z0-9_./*\-]+\s*;', line):
                facts.append({'line': number, 'kind': 'include', 'path': line[len('include '):].strip().rstrip(';').strip()})
            elif re.fullmatch(r'default_type\s+[A-Za-z0-9.+\-/]+\s*;', line):
                facts.append({'line': number, 'kind': 'default_type', 'mime': line.split()[1].rstrip(';')})
            elif re.fullmatch(r'types\s*\{\s*\}?\s*', line):
                facts.append({'line': number, 'kind': 'types_block', 'empty': '}' in line})
            elif re.fullmatch(r'root\s+/opt/lumencore/dashboard/?\s*;', line):
                facts.append({'line': number, 'kind': 'known_dashboard_root', 'path': '/opt/lumencore/dashboard'})
            elif line.startswith('location ') and line.endswith('{'):
                pattern = line[len('location '):-1].strip()
                if pattern in ('/', '= /', '/bounded-light/', '/portfolio/', '^~ /bounded-light/', '^~ /portfolio/', r'~* \.(js|mjs|css)$', r'~* \.(js|css)$', r'~* \.mjs$'):
                    if len(pattern) <= 180 and not any(char in pattern for char in ('@', '"', "'", '$')):
                        facts.append({'line': number, 'kind': 'relevant_location_declaration', 'pattern': pattern})
        if facts:
            row = {'active_file': filename, 'facts': facts, 'contains_javascript_mapping': has_js_mapping}
            if metadata:
                resolved = Path(filename).resolve(strict=True)
                if not resolved.is_relative_to(Path('/etc/nginx')) or not resolved.is_file():
                    raise ValueError('active file resolved outside expected configuration boundary')
                info = resolved.stat()
                if info.st_size > 2_000_000:
                    raise ValueError('active file exceeds bounded inspection size')
                row.update(resolved_path=str(resolved), sha256=hashlib.sha256(resolved.read_bytes()).hexdigest(),
                           uid=info.st_uid, gid=info.st_gid, mode=oct(info.st_mode & 0o7777))
            evidence.append(row)
    return {'active_configuration_evidence': evidence,
            'scope_review_required': True,
            'limitation': 'Filtered declarations locate active files; they do not automatically prove location inheritance or authorize any edit.'}


def main() -> int:
    result = {'schema': 'lumencore.public_mime_inspection.v1', 'generated_utc': datetime.now(timezone.utc).isoformat(),
              'release_source_commit': '975dc8968b7dbc1c3a410e20a6a50584a3a9d05f', 'configuration_modified': False,
              'service_reloaded': False, 'private_keys_read_by_inspector': False}
    try:
        completed = subprocess.run(['nginx', '-T'], capture_output=True, text=True, timeout=25, check=False)
        result['nginx_test_passed'] = completed.returncode == 0
        if completed.returncode != 0:
            raise ValueError('nginx inspection validation failed; raw configuration and diagnostics withheld')
        if len(completed.stdout) > 2_000_000:
            raise ValueError('active configuration exceeds bounded inspection size')
        result.update(inspect_dump(completed.stdout))
        result['module_files'] = []
        for relative, expected in EXPECTED.items():
            path = ROOT / relative
            resolved = path.resolve(strict=True)
            if not resolved.is_relative_to(ROOT) or path.is_symlink() or not resolved.is_file():
                raise ValueError('module path is outside the known static root')
            if resolved.stat().st_size > 2_000_000:
                raise ValueError('module exceeds bounded inspection size')
            actual = hashlib.sha256(resolved.read_bytes()).hexdigest()
            result['module_files'].append({'path': relative, 'sha256': actual, 'expected_sha256': expected, 'matches_release': actual == expected})
        result['status'] = 'INSPECTED_REVIEW_REQUIRED'
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        result.update(status='INSPECTION_FAILED', error_type=type(exc).__name__)
        print(json.dumps(result, sort_keys=True, indent=2))
        return 1


if __name__ == '__main__':
    sys.exit(main())
