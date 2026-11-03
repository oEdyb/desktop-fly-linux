"""One-second whole-brain probes, separate from the tiny default tests."""

import json
import time

from ..simcore.sensory import DEFAULT_DATA, SensoryBrain


def run(directory=None, seed=42):
    results = []
    for name, sugar, bitter, odor in (("rest", 0, 0, 0), ("sugar", 1, 0, 0),
                                      ("sugar_bitter", 1, 1, 0),
                                      ("mn9_inputs_cut", 1, 0, 0), ("odor", 0, 0, 1)):
        brain = SensoryBrain(directory or DEFAULT_DATA, seed)
        if name == "mn9_inputs_cut":
            import numpy as np
            brain.engine.weights[np.isin(brain.engine.post, brain.groups["mn9"])] = 0
        brain.sugar, brain.bitter, brain.odor = sugar, bitter, odor
        started = time.perf_counter()
        brain.step(1000)
        snapshot = brain.snapshot()
        snapshot.update(condition=name, wall_seconds=time.perf_counter() - started)
        results.append(snapshot)
    rest, sugar, bitter, cut, odor = results
    ok = (rest["mn9_spikes"] == 0 and sugar["mn9_spikes"] > 0
          and bitter["mn9_spikes"] < sugar["mn9_spikes"]
          and cut["mn9_spikes"] == 0
          and odor["rates_hz"]["orn"] > 0 and odor["rates_hz"]["pn"] > 0)
    print(json.dumps({"ok": ok, "seed": seed, "results": results}, indent=2))
    return 0 if ok else 1
