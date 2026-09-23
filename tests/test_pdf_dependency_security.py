"""Small local regressions for the PDF dependency's published resource guards.

The cycle/outline/XForm attack surfaces are described by upstream advisories
GHSA-jp53-mhqp-8xcg, GHSA-23w6-3w8w-8484 and GHSA-763m-79hh-57f2.
Alphabetic page-label bounds cover GHSA-w23x-9jrw-r45c.
Fixtures here are generated in memory; no uploaded PDF or exploit file runs.
"""
from io import BytesIO
from pathlib import Path
import os
import subprocess
import sys

import pypdf
import pytest
from pypdf import PdfReader, PdfWriter
from pypdf._page_labels import number2lowercase_letter, number2uppercase_letter
from pypdf.errors import LimitReachedError
from pypdf.generic import (
    ArrayObject, DecodedStreamObject, DictionaryObject, NameObject,
    NumberObject, TextStringObject,
)


def test_cyclic_tree_insertion_stops_in_a_bounded_child_process():
    # Use the base executable on Windows: a timeout can then reap the actual
    # worker, without leaving a child behind a venv redirector.
    executable = sys._base_executable if os.name == "nt" else sys.executable
    site_path = str(Path(pypdf.__file__).resolve().parent.parent)
    script = f"import sys;sys.path.insert(0,{site_path!r})\n" + """
from pypdf import PdfWriter
from pypdf.generic import TreeObject, DictionaryObject, NameObject
from pypdf.errors import LimitReachedError
w = PdfWriter()
ring = TreeObject()
ring_ref = w._add_object(ring)
ring[NameObject('/Next')] = ring_ref
root = TreeObject()
w._add_object(root)
root[NameObject('/First')] = w._add_object(DictionaryObject())
root[NameObject('/Last')] = ring_ref
try:
    root.insert_child(w._add_object(DictionaryObject()), None, w)
except LimitReachedError:
    print('CYCLE_REJECTED')
else:
    raise SystemExit('cyclic tree was accepted')
"""
    result = subprocess.run([executable, "-I", "-c", script], capture_output=True,
                            text=True, timeout=5)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "CYCLE_REJECTED"


def test_outline_alias_expansion_obeys_a_shared_entry_budget():
    writer = PdfWriter()
    nodes = [DictionaryObject({NameObject('/Title'): TextStringObject(f'node-{i}')})
             for i in range(5)]
    references = [writer._add_object(node) for node in nodes]
    for index, node in enumerate(nodes[:-1]):
        for edge in ('/First', '/Next'):
            node[NameObject(edge)] = references[index + 1]
    writer.root_object[NameObject('/Outlines')] = DictionaryObject({
        NameObject('/First'): references[0]
    })
    # A tiny test budget exercises the upstream limit without allocating a
    # large tree. It does not measure the default limit's memory consumption.
    with pypdf.apply_configuration(outline_maximum_entries=8):
        with pytest.raises(LimitReachedError, match='outline entry limit'):
            _ = writer.outline


def page_with_repeated_form(repeats):
    writer = PdfWriter()
    page = writer.add_blank_page(width=120, height=120)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                             NameObject('/Subtype'): NameObject('/Type1'),
                             NameObject('/BaseFont'): NameObject('/Helvetica')})
    resources = DictionaryObject({NameObject('/Font'): DictionaryObject({
        NameObject('/F1'): writer._add_object(font)
    })})
    form = DecodedStreamObject()
    form.set_data(b'BT /F1 10 Tf 1 0 0 1 10 10 Tm (fixture) Tj ET')
    form.update({NameObject('/Type'): NameObject('/XObject'),
                 NameObject('/Subtype'): NameObject('/Form'),
                 NameObject('/BBox'): ArrayObject([NumberObject(v) for v in (0, 0, 120, 120)]),
                 NameObject('/Resources'): resources})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/XObject'): DictionaryObject({
        NameObject('/Fm'): writer._add_object(form)
    })})
    content = DecodedStreamObject()
    content.set_data(b'/Fm Do\n' * repeats)
    page[NameObject('/Contents')] = writer._add_object(content)
    return writer, page


def test_repeated_form_extraction_stops_at_budget_and_reports_truncation(caplog):
    _, page = page_with_repeated_form(7)
    with pypdf.apply_configuration(xform_maximum_invocations_per_extraction=3):
        with caplog.at_level('WARNING', logger='pypdf'):
            text = page.extract_text()
    assert text.count('fixture') == 3
    assert 'further form content is skipped' in caplog.text


@pytest.mark.parametrize('label,letter', [
    (number2uppercase_letter, 'Z'), (number2lowercase_letter, 'z'),
])
def test_alphabetic_page_label_accepts_boundary_and_rejects_next_length(label, letter):
    # These small integer inputs exercise the upstream 512-character bound.
    # The old release also returns a short string, so the negative control
    # establishes a missing rejection, not a measured exhaustion incident.
    with pytest.raises(ValueError, match='too large'):
        label(26 * 512 + 1)
    assert label(26 * 512) == letter * 512


def test_normal_pdf_round_trip_preserves_text_outline_metadata_and_attachments():
    writer, _ = page_with_repeated_form(2)
    writer.add_outline_item('Evidence fixture', 0)
    writer.add_metadata({'/Title': 'LumenCore dependency compatibility'})
    writer.add_attachment('receipt.txt', b'bounded fixture')
    writer.add_attachment('context.txt', b'compatibility only')
    stream = BytesIO()
    writer.write(stream)
    stream.seek(0)
    reader = PdfReader(stream, strict=True)
    assert len(reader.pages) == 1
    assert reader.pages[0].extract_text().count('fixture') == 2
    assert reader.outline[0].title == 'Evidence fixture'
    assert reader.metadata.title == 'LumenCore dependency compatibility'
    assert dict(reader.attachments) == {
        'receipt.txt': [b'bounded fixture'],
        'context.txt': [b'compatibility only'],
    }
