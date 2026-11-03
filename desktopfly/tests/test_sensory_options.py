import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from desktopfly import cli
from desktopfly.app import DesktopFly
from desktopfly.world.environment import Source
from desktopfly.world.sugar import SugarDrop


class SensoryOptionsTest(unittest.TestCase):
    def test_missing_numba_only_blocks_explicit_model_requests(self):
        app = Mock(sensory=None, data_info='legacy', monitor_index=0,
                   monitor={'name': 'test'}, sugar_grab=SimpleNamespace(error=None))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'manifest.json').write_text('{}')
            with patch('desktopfly.simcore.sensory.DEFAULT_DATA', root), \
                 patch('importlib.util.find_spec', return_value=None), \
                 patch('desktopfly.app.DesktopFly', return_value=app) as create, \
                 contextlib.redirect_stdout(io.StringIO()), \
                 contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(cli.main([]), 0)
                self.assertIsNone(create.call_args.kwargs['sensory_data'])
                create.reset_mock()
                with self.assertRaises(SystemExit) as error:
                    cli.main(['--sensory-data', directory])
                self.assertEqual(error.exception.code, 2)
                create.assert_not_called()

    def test_removal_keeps_other_coincident_items(self):
        for factory, field in ((lambda: SugarDrop(0, 0), 'drops'),
                               (lambda: Source(0, 0, 'bitter'), 'sources')):
            with self.subTest(field=field):
                first, second = factory(), factory()
                self.assertEqual(first, second)
                app = DesktopFly.__new__(DesktopFly)
                app.sugar = SimpleNamespace(drops=[])
                app.environment = SimpleNamespace(sources=[])
                owner = app.sugar if field == 'drops' else app.environment
                setattr(owner, field, [first, second])
                app._sync_sugar_views = Mock()
                app.remove_drop(second)
                self.assertEqual(len(getattr(owner, field)), 1)
                self.assertIs(getattr(owner, field)[0], first)
