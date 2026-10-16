import importlib.util
from pathlib import Path
import tempfile
import unittest

PATH=Path(__file__).resolve().parents[1]/'collectors/network/network_shipper.py'
spec=importlib.util.spec_from_file_location('p34',PATH)
p34=importlib.util.module_from_spec(spec); spec.loader.exec_module(p34)

class NetworkTests(unittest.TestCase):
    def test_suricata(self):
        e=p34.normalize('suricata',{'timestamp':'2026-10-15T08:00:00Z','event_type':'alert','src_ip':'192.168.37.155','alert':{'severity':1,'signature':'Test signature','signature_id':12}})
        self.assertEqual(e['severity'],'high');self.assertEqual(e['event_type'],'suricata.alert')
        self.assertEqual(e['payload']['signature_id'],12)
    def test_zeek(self):
        e=p34.normalize('zeek',{'ts':1792051200.0,'uid':'abc','id.orig_h':'192.168.37.155','_path':'conn'})
        self.assertEqual(e['event_type'],'zeek.conn');self.assertEqual(e['payload']['uid'],'abc')
    def test_first_run_skips_old(self):
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/'eve.json';file.write_text('{"event_type":"flow"}\n')
            s=p34.load_state(Path(d)/'state.json',file.stat());self.assertEqual(s['offset'],file.stat().st_size)
    def test_partial_line_waits(self):
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/'eve.json';file.write_bytes(b'{"event_type":"flow"}')
            self.assertEqual(p34.read_batch(file,{'offset':0}),[])

if __name__=='__main__':unittest.main()
