import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('publication_tested',Path(__file__).with_name('publication.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.row={'id':10,'tag_name':'research-test','target_commitish':'a'*40,'draft':True,
                  'prerelease':True,'body':'RESEARCH ONLY','assets':[{'name':'a','state':'uploaded','size':3,'digest':'sha256:'+'b'*64}]}
        self.expected={'a':{'bytes':3,'sha256':'b'*64}}
    def test_draft_discovered_without_tag_endpoint(self):
        with patch.object(m.custody,'gh_json',side_effect=[[self.row],self.row]) as f:
            self.assertEqual(m.lookup_release('research-test')['id'],10)
            self.assertTrue(all('/tags/' not in c.args[0] for c in f.call_args_list))
    def test_numeric_id_resume(self):
        with patch.object(m.custody,'gh_json',return_value=self.row) as f:
            self.assertEqual(m.lookup_release('research-test',10)['id'],10)
            self.assertTrue(f.call_args.args[0].endswith('/releases/10'))
    def test_wrong_id_rejected(self):
        with patch.object(m.custody,'gh_json',return_value=self.row):
            with self.assertRaises(ValueError):m.lookup_release('research-test',11)
    def test_wrong_tag_rejected(self):
        with patch.object(m.custody,'gh_json',return_value=self.row):
            with self.assertRaises(ValueError):m.lookup_release('wrong-tag',10)
    def test_duplicate_drafts_rejected(self):
        with self.assertRaises(ValueError):m.choose_release([self.row,self.row],'research-test')
    def test_valid_draft_hashes(self):
        m.validate_release(self.row,'research-test','a'*40,self.expected,'RESEARCH ONLY')
    def test_wrong_hash_rejected(self):
        r=copy.deepcopy(self.row);r['assets'][0]['digest']='sha256:'+'c'*64
        with self.assertRaises(ValueError):m.validate_release(r,'research-test','a'*40,self.expected,'RESEARCH ONLY')
    def test_extra_asset_rejected(self):
        r=copy.deepcopy(self.row);r['assets'].append({'name':'extra'})
        with self.assertRaises(ValueError):m.validate_release(r,'research-test','a'*40,self.expected,'RESEARCH ONLY')
    def test_production_release_rejected(self):
        r=copy.deepcopy(self.row);r['prerelease']=False
        with self.assertRaises(ValueError):m.validate_release(r,'research-test','a'*40,self.expected,'RESEARCH ONLY')
    def test_changed_claim_notes_rejected(self):
        with self.assertRaises(ValueError):m.validate_release(self.row,'research-test','a'*40,self.expected,'unsupported superiority')

if __name__=='__main__':unittest.main()
