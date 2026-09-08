import copy, importlib.util, math, tempfile, unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch
spec = importlib.util.spec_from_file_location('watch', Path(__file__).with_name('constraint_watch.py'))
w = importlib.util.module_from_spec(spec); spec.loader.exec_module(w)
NOW = datetime(2026, 9, 8, 1, 0, tzinfo=timezone.utc)
P = {'dataset_sha256':'a'*64, 'protocol_sha256':'b'*64, 'metric':'MAE', 'direction':'lower'}
ROW = {'target_id':'t1','truth':10,'baseline':8,'candidate':9}
def post(**kw):
    x = {'id':'abc123','title':'VPN backup failed','created_utc':NOW.timestamp(), 'subreddit':'sysadmin','is_self':True}; x.update(kw)
    return {'data':{'children':[{'data':x}]}}
class Tests(unittest.TestCase):
    def test_reddit_fresh(self): self.assertEqual(len(w.reddit_records(post(),NOW)),1)
    def test_reddit_old(self): self.assertEqual(w.reddit_records(post(created_utc=(NOW-timedelta(days=8)).timestamp()),NOW),[])
    def test_reddit_future(self): self.assertEqual(w.reddit_records(post(created_utc=(NOW+timedelta(hours=1)).timestamp()),NOW),[])
    def test_reddit_nsfw(self): self.assertEqual(w.reddit_records(post(over_18=True),NOW),[])
    def test_reddit_wrong_sub(self): self.assertEqual(w.reddit_records(post(subreddit='unlisted'),NOW),[])
    def test_reddit_bad_id(self): self.assertEqual(w.reddit_records(post(id='../secret'),NOW),[])
    def test_reddit_no_username(self): self.assertNotIn('author',w.reddit_records(post(author='private'),NOW)[0])
    def test_reddit_not_savings(self): self.assertIsNone(w.reddit_records(post(),NOW)[0]['verified_savings_usd'])
    def test_reddit_bad_schema(self):
        with self.assertRaises(ValueError): w.reddit_records({},NOW)
    def test_official_bad_schema(self):
        with self.assertRaises(ValueError): w.official_records({},NOW)
    def test_official_not_measurement(self): self.assertIn('NOT_OUR_MEASUREMENT',w.official_records({'incidents':[{'id':'abc'}]},NOW)[0]['verification'])
    def test_unapproved_url(self):
        with self.assertRaises(ValueError): w.request('http://127.0.0.1/private')
    def test_gain(self): self.assertEqual(w.paired_mae([ROW],P)['mae_gain_pct'],50)
    def test_loser_retained(self): self.assertEqual(w.paired_mae([{**ROW,'candidate':15}],P)['mae_gain_pct'],-150)
    def test_zero_baseline(self): self.assertIsNone(w.paired_mae([{**ROW,'baseline':10}],P)['mae_gain_pct'])
    def test_empty_pairs(self):
        with self.assertRaises(ValueError): w.paired_mae([],P)
    def test_duplicate(self):
        with self.assertRaises(ValueError): w.paired_mae([ROW,ROW],P)
    def test_missing_truth(self):
        with self.assertRaises(ValueError): w.paired_mae([{**ROW,'truth':None}],P)
    def test_nan(self):
        with self.assertRaises(ValueError): w.paired_mae([{**ROW,'candidate':math.nan}],P)
    def test_unfrozen(self):
        with self.assertRaises(ValueError): w.paired_mae([ROW],{})
    def test_no_savings_inference(self): self.assertFalse(w.paired_mae([ROW],P)['causal_savings_or_superiority_established'])
    def test_overwrite_refused(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(FileExistsError): w.collect(Path(t))
    def test_missing_secret_no_probe(self):
        with tempfile.TemporaryDirectory() as t, patch.dict(w.os.environ,{},clear=True),patch.object(w,'request',return_value=({'incidents':[]},b'{"incidents":[]}')) as req:
            r = w.collect(Path(t)/'fresh',True)
            self.assertEqual(r['sources']['reddit']['state'],'HOLD_MISSING_RUNTIME_CREDENTIALS')
            self.assertEqual(req.call_count,1)
    def test_error_payload_redacted(self): self.assertNotIn('secret_value',str(w.failure(ValueError('secret_value'))))
if __name__=='__main__': unittest.main()
