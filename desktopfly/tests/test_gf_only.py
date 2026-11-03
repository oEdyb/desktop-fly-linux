import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from desktopfly.app import DesktopFly
from desktopfly.body.fly import Fly, State
from desktopfly.simcore.data import load_brain_data
from desktopfly.simcore.lif import LIFSim
from desktopfly.simcore.signals import BrainSignals, SignalBuilder


class GFOnlyTest(unittest.TestCase):
    def test_arousal_and_cursor_cannot_take_off_without_gf(self):
        fly = Fly(0, 0)
        fly.state = State.WALKING
        fly.start_flight = Mock()
        signals = BrainSignals(arousal=1, nervous=1, walk_drive=1)
        for _ in range(600):
            fly.update(.016, (1920, 1080), (0, 0), signals)
        fly.start_flight.assert_not_called()
        signals.escape = True
        fly.update(.016, (1920, 1080), (0, 0), signals)
        fly.start_flight.assert_called_once()

    def test_no_brain_does_not_enable_proximity_fallback(self):
        fly = Fly(0, 0)
        fly.start_flight = Mock()
        for _ in range(600):
            fly.update(.016, (1920, 1080), (0, 0))
        fly.start_flight.assert_not_called()

    def test_fast_cursor_uses_only_visual_path_and_cut_blocks_it(self):
        _, circuit = load_brain_data()
        app = DesktopFly.__new__(DesktopFly)
        app._prev_mouse = (500, 0)
        app._mouse_vel = [0., 0.]
        app._loom_override = 0
        body = SimpleNamespace(pos_x=0, pos_y=0, heading=0)
        left, right, puff = app._compute_loom(body, (10, 0), .016)
        self.assertEqual(puff, 0)
        self.assertGreater(left + right, .9)
        for cut in (False, True):
            sim = LIFSim(circuit, seed=20260821)
            sim.set_escape_inputs_cut(cut)
            sim.step(4000)
            sim.consume_gf()
            sim.loom_l, sim.loom_r, sim.air_puff = left, right, puff
            sim.step(1000)
            self.assertEqual(sim.consume_gf(), not cut)
            self.assertGreater(sim.rate_loom, 50)
            sim.stimulate(sim.gf, .25, 400)
            sim.step(100)
            self.assertTrue(SignalBuilder().make(sim, .016).escape)


if __name__ == '__main__':
    unittest.main()
