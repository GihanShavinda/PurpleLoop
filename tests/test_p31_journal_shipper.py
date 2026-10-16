"""Run locally with python -m unittest discover -s tests -p 'test_p31_*.py'."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timezone

path = Path(__file__).resolve().parents[1] / 'collectors/linux/journal_shipper.py'
spec = importlib.util.spec_from_file_location('journal_shipper', path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class JournalTests(unittest.TestCase):
    def test_mapping(self):
        now = int(datetime.now(timezone.utc).timestamp() * 1_000_000)
        value = mod.to_event({'__REALTIME_TIMESTAMP': str(now), 'MESSAGE': 'ssh login', 'PRIORITY': '4', '_HOSTNAME': 'ubuntu2404'})
        self.assertEqual(value['event_type'], 'linux.journal')
        self.assertEqual(value['severity'], 'medium')
        self.assertEqual(value['payload']['hostname'], 'ubuntu2404')
    def test_cursor_atomic(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory)/'cursor'
            mod.write_cursor(file, 'abc')
            self.assertEqual(file.read_text(), 'abc')
            mod.write_cursor(file, 'def')
            self.assertEqual(file.read_text(), 'def')
    def test_reject_plain_http(self):
        with self.assertRaises(ValueError):
            mod.send('http://192.168.37.1:8000', 'key', [], None)


if __name__ == '__main__':
    unittest.main()
