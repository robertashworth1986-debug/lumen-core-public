import importlib.util
import pathlib
import tempfile
import unittest
import numpy as np
import pandas as pd

ROOT=pathlib.Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'experiments'/'energy_multisource'/'run_next_stage_experiments.py'
spec=importlib.util.spec_from_file_location('energy_next_stage',SCRIPT)
mod=importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

class EnergyNextStageTests(unittest.TestCase):
    def test_wave_proxy_constant_positive(self):
        self.assertGreater(mod.WAVE_KW_M,0.0)

    def test_ndbc_parser_and_proxy(self):
        text='''#YY MM DD hh mm WDIR WSPD GST WVHT DPD APD MWD PRES ATMP WTMP DEWP VIS PTDY TIDE\n#yr mo dy hr mn degT m/s m/s m sec sec degT hPa degC degC degC nmi hPa ft\n2026 09 04 17 20 350 5.0 6.0 1.8 11 8.5 294 1014.7 15.7 16.1 14.3 MM MM MM\n2026 09 04 17 00 350 5.0 6.0 1.7 10 8.2 290 1014.5 15.6 16.0 14.1 MM MM MM\n'''
        with tempfile.TemporaryDirectory() as td:
            p=pathlib.Path(td)/'test.txt'; p.write_text(text)
            d=mod.read_ndbc(p)
            self.assertEqual(len(d),2)
            self.assertTrue((d['proxy']>0).all())

    def test_walkforward_retains_all_horizons(self):
        n=5000
        t=pd.date_range('2026-01-01',periods=n,freq='30s')
        flow=300+5*np.sin(np.arange(n)/100.0)
        d=pd.DataFrame({'time':t,'sep_total':flow,'pump_rate':10.0,'p16a':2800.0,'p16b':250.0,'temp16b':350.0})
        d['recovery_proxy']=d['sep_total']/(d['pump_rate']*42.0)
        out=mod.forge_walkforward(d)
        self.assertEqual(set(out),{'20','60','120'})
        for v in out.values():
            self.assertEqual(len(v['folds']),4)
            self.assertIn('negative_rolling_folds',v)

if __name__=='__main__':
    unittest.main()
