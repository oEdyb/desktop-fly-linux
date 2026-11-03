"""Shiu LIF equations, with sparse delayed spike delivery at 0.1 ms."""

from __future__ import annotations

import numpy as np
from numba import njit


@njit(cache=True, nogil=True)
def advance(start, steps, ptr, post, weights, v, g, last, queue, lengths,
            active, marked, nactive, inputs, draws, counts, sensory, fired):
    av = np.exp(-0.1 / 20)
    ag = np.exp(-0.1 / 5)
    coupling = (av - ag) / 3
    for t in range(start, start + steps):
        slot = t % 19
        nfired = 0
        for k in range(nactive):
            j = active[k]
            if t - last[j] >= 22 or sensory[j]:
                v[j] = v[j] * av + g[j] * coupling
                g[j] *= ag
                if v[j] > 7:
                    counts[j] += 1
                    fired[nfired] = j
                    nfired += 1
                    last[j] = t
        for k in range(lengths[slot]):
            j = queue[slot, k]
            for e in range(ptr[j], ptr[j + 1]):
                target = post[e]
                g[target] += weights[e]
                if not marked[target]:
                    marked[target] = True
                    active[nactive] = target
                    nactive += 1
        lengths[slot] = 0
        for k in range(len(inputs)):
            if draws[t - start, k]:
                v[inputs[k]] += 68.75
        dest = (t + 18) % 19
        for k in range(nfired):
            j = fired[k]
            v[j] = 0
            g[j] = 0
            queue[dest, lengths[dest]] = j
            lengths[dest] += 1
    return nactive


class PaperLIF:
    def __init__(self, ptr, post, weights, inputs, seed=None):
        self.ptr, self.post, self.weights = ptr, post, weights
        self.n = len(ptr) - 1
        self.inputs = np.asarray(inputs, dtype=np.int32)
        self.rng = np.random.default_rng(seed)
        self.v = np.zeros(self.n)
        self.g = np.zeros(self.n)
        self.last = np.full(self.n, -22, dtype=np.int64)
        self.queue = np.zeros((19, self.n), dtype=np.int32)
        self.lengths = np.zeros(19, dtype=np.int32)
        self.active = np.empty(self.n, dtype=np.int32)
        self.marked = np.zeros(self.n, dtype=bool)
        self.sensory = np.zeros(self.n, dtype=bool)
        self.sensory[self.inputs] = True
        self.marked[self.inputs] = True
        self.active[:len(self.inputs)] = self.inputs
        self.nactive = len(self.inputs)
        self.fired = np.empty(self.n, dtype=np.int32)
        self.counts = np.zeros(self.n, dtype=np.int64)
        self.tick = 0

    def step(self, ms, rates, draws=None):
        steps = int(ms * 10)
        if steps <= 0:
            return
        if draws is None:
            draws = self.rng.random((steps, len(self.inputs))) < np.asarray(rates) * 0.0001
        self.nactive = advance(
            self.tick, steps, self.ptr, self.post, self.weights, self.v, self.g,
            self.last, self.queue, self.lengths, self.active, self.marked,
            self.nactive, self.inputs, draws, self.counts, self.sensory, self.fired,
        )
        self.tick += steps
