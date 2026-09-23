import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

p=Path(__file__).with_name('checkpoint.py')
spec=importlib.util.spec_from_file_location('checkpoint_tested',p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class CustodyTests(unittest.TestCase):
    def test_valid_zip(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.zip'
            with zipfile.ZipFile(p,'w') as z:z.writestr('safe.txt','data')
            self.assertEqual(m.checked_zip(p),['safe.txt'])
    def test_path_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.zip'
            with zipfile.ZipFile(p,'w') as z:z.writestr('../escape','data')
            with self.assertRaises(ValueError):m.checked_zip(p)
    def test_absolute_path(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.zip'
            with zipfile.ZipFile(p,'w') as z:z.writestr('/escape','data')
            with self.assertRaises(ValueError):m.checked_zip(p)
    def test_windows_path(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.zip'
            with zipfile.ZipFile(p,'w') as z:z.writestr('C:\\escape','data')
            with self.assertRaises(ValueError):m.checked_zip(p)
    def test_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.zip';info=zipfile.ZipInfo('link');info.create_system=3;info.external_attr=0o120777<<16
            with zipfile.ZipFile(p,'w') as z:z.writestr(info,'../target')
            with self.assertRaises(ValueError):m.checked_zip(p)
    def test_tampered_payload(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x';p.write_bytes(b'abc')
            with self.assertRaises(ValueError):m.verify_file(p,{'bytes':3,'sha256':'0'*64})
    def test_size_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x';p.write_bytes(b'abc')
            with self.assertRaises(ValueError):m.verify_file(p,{'bytes':4,'sha256':hashlib.sha256(b'abc').hexdigest()})
    def test_valid_payload(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x';p.write_bytes(b'abc')
            m.verify_file(p,{'bytes':3,'sha256':hashlib.sha256(b'abc').hexdigest()})

if __name__=='__main__':unittest.main()
