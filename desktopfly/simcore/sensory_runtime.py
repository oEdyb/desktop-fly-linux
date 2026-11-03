"""Keep the desktop responsive when whole-brain olfactory activity is expensive."""

import logging
import threading
import time

from .sensory import SensoryBrain

logger = logging.getLogger(__name__)


class SensoryRuntime:
    def __init__(self, directory, seed=None):
        self.brain = SensoryBrain(directory, seed)
        self.groups = self.brain.groups
        self.positions = self.brain.positions
        self.info = self.brain.info
        self.neuron_rates = self.brain.neuron_rates.copy()
        self.rates = self.brain.rates.copy()
        self.feeding = False
        self.sugar = self.bitter = self.odor = 0.0
        self.error = None
        self.speed = 1.0
        self._snapshot = self.brain.snapshot()
        self._request = None
        self._lock = threading.Lock()
        self._reset = False
        self._last_finished = time.perf_counter()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="sensory-brain", daemon=True)
        self._thread.start()

    def step(self, ms):
        with self._lock:
            self._request = (min(16, ms), self.sugar, self.bitter, self.odor)
        self._wake.set()

    def reset(self):
        with self._lock:
            self._reset = True
            self._request = None
        self._wake.set()

    def _run(self):
        while not self._stop.is_set():
            self._wake.wait()
            self._wake.clear()
            if self._stop.is_set():
                return
            with self._lock:
                request = self._request
                self._request = None
                reset = self._reset
                self._reset = False
            if self.error and not reset:
                continue
            if reset:
                self.brain.reset()
                self.error = None
                self._last_finished = time.perf_counter()
                self.neuron_rates = self.brain.neuron_rates.copy()
                self.rates = self.brain.rates.copy()
                self.feeding = False
                self._snapshot = self.brain.snapshot()
            if request is None:
                continue
            ms, sugar, bitter, odor = request
            try:
                self.brain.sugar, self.brain.bitter, self.brain.odor = sugar, bitter, odor
                self.brain.step(ms)
                finished = time.perf_counter()
                elapsed = finished - self._last_finished
                self._last_finished = finished
                self.speed += (min(1.0, ms / 1000 / max(elapsed, 0.00001)) - self.speed) * 0.1
                self.neuron_rates = self.brain.neuron_rates.copy()
                self.rates = self.brain.rates.copy()
                self.feeding = self.brain.feeding
                self._snapshot = {**self.brain.snapshot(), "speed": self.speed}
            except Exception as error:
                logger.exception("Whole-brain simulation failed")
                self.error = str(error)
                self.feeding = False

    def snapshot(self):
        return {**self._snapshot, "error": self.error}

    def pause(self):
        with self._lock:
            self._request = None

    def close(self):
        self._stop.set()
        self._wake.set()
        self._thread.join(timeout=2)
