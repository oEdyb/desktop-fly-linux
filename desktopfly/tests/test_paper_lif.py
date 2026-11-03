import importlib.util
import unittest

import numpy as np


@unittest.skipUnless(importlib.util.find_spec("numba") and importlib.util.find_spec("brian2"),
                     "install sensory extras and Brian2 to check solver parity")
class PaperLIFTest(unittest.TestCase):
    def test_delays_reset_refractory_and_inhibition_match_brian2(self):
        import brian2 as b

        from desktopfly.simcore.paper_lif import PaperLIF

        b.start_scope()
        b.prefs.codegen.target = "numpy"
        b.defaultclock.dt = 0.1 * b.ms
        ptr = np.array([0, 2, 3, 4, 4], np.int32)
        post = np.array([1, 2, 3, 3], np.int32)
        weights = np.array([20., -10., 25., -5.])
        model = PaperLIF(ptr, post, weights, [0], seed=4)
        draws = np.random.default_rng(4).random((300, 1)) < 0.04
        stimulus = b.TimedArray(np.pad(draws, ((0, 0), (0, 3))).astype(float), dt=0.1 * b.ms)
        neurons = b.NeuronGroup(
            4, "dv/dt=(-v+g)/(20*ms):volt (unless refractory)\n"
            "dg/dt=-g/(5*ms):volt (unless refractory)\nrfc:second",
            method="linear", threshold="v>7*mV", reset="v=0*mV;g=0*mV", refractory="rfc",
            namespace={"stimulus": stimulus},
        )
        neurons.rfc = 2.2 * b.ms
        neurons.rfc[0] = 0 * b.ms
        synapses = b.Synapses(neurons, neurons, "w:volt", on_pre="g+=w", delay=1.8 * b.ms)
        synapses.connect(i=[0, 0, 1, 2], j=post)
        synapses.w = weights * b.mV
        neurons.run_regularly("v+=stimulus(t,i)*68.75*mV", when="synapses", order=1)
        spikes = b.SpikeMonitor(neurons)
        state = b.StateMonitor(neurons, ["v", "g"], record=True, when="end")
        b.Network(neurons, synapses, spikes, state).run(30 * b.ms)
        voltage, conductance = [], []
        for tick in range(300):
            model.step(0.1, [0], draws[tick:tick + 1])
            voltage.append(model.v.copy())
            conductance.append(model.g.copy())
        np.testing.assert_allclose(np.array(voltage).T, state.v / b.mV, atol=1e-10)
        np.testing.assert_allclose(np.array(conductance).T, state.g / b.mV, atol=1e-10)
        np.testing.assert_array_equal(model.counts, spikes.count[:])
