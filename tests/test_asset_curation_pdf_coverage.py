"""Document discovery must report partial PDF inspection without hiding it."""
import hashlib
import importlib.util
import json
import logging
from pathlib import Path
import sys
from types import SimpleNamespace
import warnings

import pytest


SOURCE = Path(__file__).resolve().parents[1] / 'code/ops/CURATE_ICLOUD_TOP_ASSETS.py'


def load_subject():
    spec = importlib.util.spec_from_file_location('asset_curation_subject', SOURCE)
    subject = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(subject)
    return subject


@pytest.fixture
def subject():
    logger = logging.getLogger('pypdf')
    level, filters = logger.level, warnings.filters[:]
    try:
        yield load_subject()
    finally:
        logger.setLevel(level)
        warnings.filters[:] = filters


class Page:
    def __init__(self, text='fixture', *, images=(), text_error=False, image_error=False, warning=False):
        self.text, self._images = text, images
        self.text_error, self.image_error, self.warning = text_error, image_error, warning
        self.image_reads = self.text_reads = 0

    @property
    def images(self):
        self.image_reads += 1
        if self.image_error:
            raise ValueError('fixture image failure')
        return self._images

    def extract_text(self):
        self.text_reads += 1
        if self.text_error:
            raise ValueError('fixture text failure')
        if self.warning:
            logging.getLogger('pypdf._page').warning('further form content is skipped')
            warnings.warn('fixture extraction warning', UserWarning)
        return self.text


def pdf_fixture(tmp_path, subject, monkeypatch, pages):
    path = tmp_path / 'proof fixture.pdf'
    path.write_bytes(b'%PDF-1.7\nfixture')
    monkeypatch.setattr(subject, 'PdfReader', lambda *a, **k: SimpleNamespace(pages=pages))
    return path


def test_import_does_not_suppress_global_pdf_diagnostics():
    logger = logging.getLogger('pypdf')
    level, filters = logger.level, warnings.filters[:]
    logger.setLevel(logging.WARNING)
    expected_filters = warnings.filters[:]
    try:
        load_subject()
        assert logger.level == logging.WARNING
        assert warnings.filters == expected_filters
    finally:
        logger.setLevel(level)
        warnings.filters[:] = filters


def test_page_cap_applies_to_images_as_well_as_text(tmp_path, subject, monkeypatch):
    pages = [Page() for _ in range(4)]
    path = pdf_fixture(tmp_path, subject, monkeypatch, pages)
    result = subject.parse_pdf(path, max_pages=2, max_chars=100)
    assert [p.image_reads for p in pages] == [1, 1, 0, 0]
    assert result['pages_inspected'] == 2
    assert result['pages_total'] == 4
    assert result['inspection_status'] == 'PARTIAL'
    assert not result['text_layer_complete']
    assert not result['image_inventory_complete']
    assert 'page_limit' in result['limits_reached']


def test_character_budget_includes_join_separators(tmp_path, subject, monkeypatch):
    path = pdf_fixture(tmp_path, subject, monkeypatch, [Page('ab'), Page('cd')])
    result = subject.parse_pdf(path, max_pages=2, max_chars=4)
    assert result['text'] == 'ab\nc'
    assert len(result['text']) <= 4
    assert 'character_limit' in result['limits_reached']
    assert not result['text_layer_complete']


def test_pdf_warnings_make_partial_coverage_visible_and_restore_logger(tmp_path, subject, monkeypatch):
    path = pdf_fixture(tmp_path, subject, monkeypatch, [Page(warning=True)])
    logger = logging.getLogger('pypdf')
    logger.setLevel(logging.ERROR)
    handlers, propagate, filters = logger.handlers[:], logger.propagate, warnings.filters[:]
    result = subject.parse_pdf(path, max_pages=2, max_chars=100)
    assert result['inspection_status'] == 'PARTIAL'
    assert result['diagnostic_count'] == 2
    assert not result['text_layer_complete']
    assert logger.level == logging.ERROR
    assert logger.handlers == handlers and logger.propagate == propagate
    assert warnings.filters == filters


@pytest.mark.parametrize('failure', ['text_error', 'image_error'])
def test_page_errors_are_retained_as_partial_inspection(tmp_path, subject, monkeypatch, failure):
    path = pdf_fixture(tmp_path, subject, monkeypatch, [Page(**{failure: True})])
    result = subject.parse_pdf(path, max_pages=1, max_chars=100)
    assert result['inspection_status'] == 'PARTIAL'
    assert result['diagnostic_count'] >= 1
    field = 'text_layer_complete' if failure == 'text_error' else 'image_inventory_complete'
    assert not result[field]


def test_byte_cap_is_enforced_before_pdf_reader_construction(tmp_path, subject, monkeypatch):
    path = tmp_path / 'large.pdf'
    path.write_bytes(b'%PDF-' + b'X' * 40)
    calls = []
    monkeypatch.setattr(subject, 'PdfReader', lambda *a, **k: calls.append(a))
    result = subject.parse_document(path, max_bytes=10, max_pages=2, max_chars=100)
    assert not result['ok'] and result['inspection_status'] == 'FAILED'
    assert 'byte_limit' in result['limits_reached']
    assert calls == []


def test_success_binds_exact_bytes_and_only_claims_text_layer_coverage(tmp_path, subject, monkeypatch):
    path = pdf_fixture(tmp_path, subject, monkeypatch, [Page('proof', images=[object()])])
    result = subject.parse_pdf(path, max_pages=1, max_chars=100)
    assert result['inspection_status'] == 'TEXT_LAYER_INSPECTED'
    assert result['source_sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert result['text_layer_complete'] and result['image_inventory_complete']
    assert result['image_objects'] == 1
    assert 'OCR' in result['scope_boundary']


def test_reader_failure_returns_a_failed_report(tmp_path, subject, monkeypatch):
    path = pdf_fixture(tmp_path, subject, monkeypatch, [])
    def fail(*a, **k):
        raise ValueError('fixture malformed PDF')
    monkeypatch.setattr(subject, 'PdfReader', fail)
    result = subject.parse_pdf(path, max_pages=1, max_chars=100)
    assert result['inspection_status'] == 'FAILED' and not result['ok']
    assert result['diagnostic_count'] == 1


def test_empty_text_layer_is_not_an_ocr_or_visual_read(tmp_path, subject, monkeypatch):
    path = pdf_fixture(tmp_path, subject, monkeypatch, [Page('', images=[object()])])
    result = subject.parse_pdf(path, max_pages=1, max_chars=100)
    assert result['text'] == ''
    assert result['text_layer_complete']
    assert result['pages_without_text'] == 1
    assert result['ocr_performed'] is False


def test_curation_exports_pdf_coverage_in_inventory_top_list_and_summary(tmp_path, subject, monkeypatch):
    source = tmp_path / 'input'
    source.mkdir()
    path = pdf_fixture(source, subject, monkeypatch, [Page('proof'), Page('proof')])
    output = tmp_path / 'output'
    monkeypatch.setattr(subject, 'extract_pdf_previews', lambda **k: [])
    # The production scanner deliberately skips Windows Temp. Exercise the
    # report path with one explicitly supplied disposable test file.
    monkeypatch.setattr(subject, 'iter_user_files', lambda *a, **k: iter([(1, path)]))
    monkeypatch.setattr(sys, 'argv', [
        str(SOURCE), '--scan-root', str(source), '--output-root', str(output),
        '--max-doc-pages', '1', '--preview-max-docs', '0'])
    assert subject.main() == 0
    report = json.loads(next(output.glob('local_top_assets_*/top_assets.json')).read_text())
    assert report['counts']['pdf_partial_inspections'] == 1
    assert report['top_assets'][0]['inspection_status'] == 'PARTIAL'
    inventory = next(output.glob('local_top_assets_*/document_inventory.csv')).read_text()
    top = next(output.glob('local_top_assets_*/top_assets.csv')).read_text()
    assert 'inspection_status' in inventory and 'PARTIAL' in inventory
    assert 'inspection_status' in top and 'PARTIAL' in top


@pytest.mark.parametrize('name,value', [('max_pages', 0), ('max_chars', -1), ('max_bytes', 0), ('max_pages', True)])
def test_invalid_pdf_limits_fail_before_file_or_reader_access(tmp_path, subject, monkeypatch, name, value):
    calls = []
    monkeypatch.setattr(subject, 'PdfReader', lambda *a, **k: calls.append(a))
    limits = dict(max_pages=1, max_chars=100, max_bytes=100)
    limits[name] = value
    result = subject.parse_pdf(tmp_path / 'absent.pdf', **limits)
    assert result['error'] == f'invalid_{name}'
    assert result['inspection_status'] == 'FAILED'
    assert calls == []


def test_many_warnings_keep_bounded_diagnostics_and_exact_count(tmp_path, subject, monkeypatch):
    page = Page()
    def noisy():
        for index in range(70):
            logging.getLogger('pypdf._page').warning('fixture warning %s', index)
        return 'proof'
    page.extract_text = noisy
    path = pdf_fixture(tmp_path, subject, monkeypatch, [page])
    result = subject.parse_pdf(path, max_pages=1, max_chars=100)
    assert result['diagnostic_count'] == 70
    assert len(result['diagnostics']) == 50
    assert result['inspection_status'] == 'PARTIAL'


def test_preview_refuses_changed_or_unbound_source_bytes(tmp_path, subject, monkeypatch):
    path = pdf_fixture(tmp_path, subject, monkeypatch, [Page()])
    original = subject.parse_pdf(path, max_pages=1, max_chars=100)
    path.write_bytes(path.read_bytes() + b'changed')
    calls, reports = [], []
    monkeypatch.setattr(subject, 'PdfReader', lambda *a, **k: calls.append(a))
    rows = subject.extract_pdf_previews([{'path': str(path), **original}], tmp_path/'previews', 1, 1, reports=reports)
    assert rows == [] and calls == []
    assert reports[0]['status'] == 'SOURCE_IDENTITY_HOLD'


def test_preview_obeys_page_prefix_and_binds_extracted_bytes(tmp_path, subject, monkeypatch):
    image = SimpleNamespace(name='figure.png', data=b'raw fixture preview bytes')
    pages = [Page(images=[image]), Page(images=[image])]
    path = pdf_fixture(tmp_path, subject, monkeypatch, pages)
    doc = {'path': str(path), **subject.parse_pdf(path, max_pages=1, max_chars=100)}
    for page in pages:
        page.image_reads = 0
    reports = []
    rows = subject.extract_pdf_previews([doc], tmp_path/'previews', 1, 4, reports=reports)
    assert len(rows) == 1
    assert [p.image_reads for p in pages] == [1, 0]
    assert rows[0]['source_sha256'] == doc['source_sha256']
    assert rows[0]['preview_sha256'] == hashlib.sha256(image.data).hexdigest()
    assert Path(rows[0]['preview_path']).read_bytes() == image.data
    assert reports[0]['status'] == 'EXTRACTED'


def test_preview_failure_consumes_document_budget_and_is_reported(tmp_path, subject, monkeypatch):
    reports, calls = [], []
    monkeypatch.setattr(subject, 'PdfReader', lambda *a, **k: calls.append(a))
    docs = [{'path': str(tmp_path / f'absent-{index}.pdf')} for index in range(3)]
    rows = subject.extract_pdf_previews(docs, tmp_path/'previews', 1, 1, reports=reports)
    assert rows == [] and calls == []
    assert len(reports) == 1 and reports[0]['status'] == 'PARTIAL_OR_FAILED'
    assert reports[0]['diagnostic_count'] == 1


def test_real_pdf_page_count_and_selected_coverage(tmp_path, subject):
    from pypdf import PdfWriter
    writer = PdfWriter()
    for _ in range(3):
        writer.add_blank_page(width=100, height=100)
    path = tmp_path/'real-generated.pdf'
    with path.open('wb') as handle:
        writer.write(handle)
    result = subject.parse_pdf(path, max_pages=2, max_chars=100)
    assert result['pages_total'] == 3 and result['pages_inspected'] == 2
    assert result['pages_without_text'] == 2 and not result['text_layer_complete']
    assert result['source_sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_invalid_cli_bounds_do_not_create_output_state(tmp_path, subject, monkeypatch):
    output = tmp_path / 'output'
    monkeypatch.setattr(sys, 'argv', [str(SOURCE), '--scan-root', str(tmp_path),
                                    '--output-root', str(output), '--max-doc-bytes', '-1'])
    with pytest.raises(SystemExit) as error:
        subject.main()
    assert error.value.code == 2 and not output.exists()


def test_missing_scan_root_does_not_create_output_state(tmp_path, subject, monkeypatch):
    output = tmp_path / 'output'
    monkeypatch.setattr(sys, 'argv', [str(SOURCE), '--scan-root', str(tmp_path/'absent'),
                                    '--output-root', str(output)])
    with pytest.raises(SystemExit):
        subject.main()
    assert not output.exists()
