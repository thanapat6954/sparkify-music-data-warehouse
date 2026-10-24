import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.local_config import load_local_env, save_local_setting


class LocalConfigTests(unittest.TestCase):
    def test_shell_settings_take_precedence_and_save_preserves_other_keys(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'PGHOST': 'ci-host'}, clear=True):
            root = Path(temp)
            (root / '.env').write_text('PGHOST=local-host\nPGDATABASE=sparkify\n', encoding='utf-8')
            load_local_env(root)
            self.assertEqual(os.environ['PGHOST'], 'ci-host')
            self.assertEqual(os.environ['PGDATABASE'], 'sparkify')
            save_local_setting(root, 'LOCAL_TEST_SETTING', 'value')
            self.assertIn('PGDATABASE=sparkify', (root / '.env').read_text())


if __name__ == '__main__':
    unittest.main()
