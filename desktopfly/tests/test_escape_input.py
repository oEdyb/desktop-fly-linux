import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np

from desktopfly.app import DesktopFly
from desktopfly.platform.brain_window import BrainWindow
from desktopfly.simcore.data import load_brain_data
from desktopfly.simcore.lif import LIFSim


class EscapeInputTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, cls.circuit = load_brain_data()

    def drive(self, distance):
        app = DesktopFly.__new__(DesktopFly)
        app._prev_mouse = (distance, 0)
        app._mouse_vel = [0.0, 0.0]
        app._loom_override = 0.0
        fly = SimpleNamespace(pos_x=0, pos_y=0, heading=0)
        return app._compute_loom(fly, (distance, 0), .016)

    def test_proximity_increases_real_visual_spiking_before_escape(self):
        rates, escaped = [], []
        for distance in (700, 180, 30):
            sim = LIFSim(self.circuit, seed=42)
            sim.step(1000)
            sim.loom_l, sim.loom_r, sim.air_puff = self.drive(distance)
            did_escape = False
            for _ in range(1000):
                sim.step(1)
                did_escape |= sim.consume_gf()
            rates.append(sim.rate_loom)
            escaped.append(did_escape)
        self.assertLess(rates[0], rates[1])
        self.assertLess(rates[1], rates[2])
        self.assertEqual(escaped, [False, False, True])

    def test_named_controls_stimulate_only_the_real_group(self):
        sim = LIFSim(self.circuit, seed=42)
        brain = BrainWindow.__new__(BrainWindow)
        brain.sim = sim
        brain._show_label = lambda _text: None
        brain.on_stimulate = None
        for role, count in [('lc4', 104), ('lplc2', 210), ('dnp09', 2), ('mdn', 4), ('gf', 2)]:
            picked = np.flatnonzero(np.asarray(sim.roles) == role)
            self.assertEqual(len(picked), count)
            brain.groups = {role: (role, picked)}
            sim.stimulate = Mock()
            brain.stimulate_group(role)
            np.testing.assert_array_equal(sim.stimulate.call_args.args[0], picked)


if __name__ == '__main__':
    unittest.main()
