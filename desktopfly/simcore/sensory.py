"""Whole-brain taste and odor adapter; motor readout is MN9 only."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import numpy as np

DEFAULT_DATA = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "desktopfly" / "v783"


class SensoryBrain:
    def __init__(self, directory=DEFAULT_DATA, seed=None):
        from .paper_lif import PaperLIF

        directory = Path(directory)
        self.seed = seed
        self.info = json.loads((directory / "manifest.json").read_text())
        data = np.load(directory / "brain.npz", allow_pickle=False)
        self.ids = data["ids"]
        self.positions = data["positions"]
        self.groups = {name: data[name] for name in self.info["groups"]}
        self.inputs = np.concatenate([self.groups[k] for k in ("sugar", "bitter", "orn")])
        self.engine = PaperLIF(data["ptr"], data["post"], data["weights"], self.inputs, seed)
        self.neuron_rates = np.zeros(self.engine.n)
        self.rates = {name: 0.0 for name in self.groups}
        self.sugar = self.bitter = self.odor = 0.0
        self.wall_seconds = 0.0
        self.fly_seconds = 0.0
        self.last_mn9_tick = -10000
        self.step(0.1)

    @property
    def feeding(self):
        return self.engine.tick - self.last_mn9_tick < 1500

    def reset(self):
        from .paper_lif import PaperLIF

        old = self.engine
        self.engine = PaperLIF(old.ptr, old.post, old.weights, self.inputs, self.seed)
        self.neuron_rates.fill(0)
        self.rates = {name: 0.0 for name in self.groups}
        self.last_mn9_tick = -10000
        self.wall_seconds = self.fly_seconds = 0.0

    def step(self, ms):
        if ms <= 0:
            return
        rates = np.concatenate([
            np.full(len(self.groups["sugar"]), 100 * self.sugar),
            np.full(len(self.groups["bitter"]), 200 * self.bitter),
            np.full(len(self.groups["orn"]), 100 * self.odor),
        ])
        before = self.engine.counts.copy()
        started = time.perf_counter()
        self.engine.step(ms, rates)
        self.wall_seconds += time.perf_counter() - started
        self.fly_seconds += ms / 1000
        delta = self.engine.counts - before
        alpha = 1 - np.exp(-ms / 120)
        self.neuron_rates += (delta * (1000 / ms) - self.neuron_rates) * alpha
        for name, indices in self.groups.items():
            self.rates[name] = float(self.neuron_rates[indices].mean())
        if delta[self.groups["mn9"]].any():
            self.last_mn9_tick = int(self.engine.last[self.groups["mn9"]].max())

    def snapshot(self):
        return {
            "neurons": self.engine.n, "connections": len(self.engine.post),
            "fly_seconds": self.engine.tick / 10000,
            "compute_seconds": self.wall_seconds,
            "input": {"sugar": self.sugar, "bitter": self.bitter, "odor": self.odor},
            "rates_hz": self.rates.copy(), "feeding": self.feeding,
            "mn9_spikes": int(self.engine.counts[self.groups["mn9"]].sum()),
        }
