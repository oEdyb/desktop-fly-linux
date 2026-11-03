import unittest

import numpy as np

from desktopfly.simcore.data import load_brain_data
from desktopfly.simcore.lif import LIFSim


class EscapeCutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, cls.circuit = load_brain_data()

    def test_cut_changes_only_visual_to_gf_and_restores_exactly(self):
        sim = LIFSim(self.circuit, seed=20260821)
        original = sim.w.copy()
        pre = np.repeat(np.arange(sim.n), np.diff(sim.row_start))
        mask = np.isin(pre, np.r_[sim.loom_left, sim.loom_right]) & np.isin(sim.col_idx, sim.gf)
        self.assertEqual(int(mask.sum()), 216)
        for _ in range(2):
            sim.set_escape_inputs_cut(True)
            self.assertTrue(sim.escape_inputs_cut)
            self.assertTrue((sim.w[mask] == 0).all())
            np.testing.assert_array_equal(sim.w[~mask], original[~mask])
        for _ in range(2):
            sim.set_escape_inputs_cut(False)
            self.assertFalse(sim.escape_inputs_cut)
            np.testing.assert_array_equal(sim.w, original)

    def test_cut_blocks_loom_but_direct_gf_bypasses_it(self):
        for cut in (False, True):
            sim = LIFSim(self.circuit, seed=20260821)
            sim.set_escape_inputs_cut(cut)
            sim.step(4000)
            sim.consume_gf()
            sim.loom_l, sim.loom_r = 1.0, 0.5
            sim.step(400)
            self.assertEqual(sim.consume_gf(), not cut)
            self.assertGreater(sim.rate_loom, 50)
            sim.loom_l = sim.loom_r = 0
            sim.stimulate(sim.gf, 0.25, 400)
            sim.step(400)
            self.assertTrue(sim.consume_gf())
            self.assertEqual(sim.escape_inputs_cut, cut)


if __name__ == '__main__':
    unittest.main()
