"""Taste requires contact; the generic odor plume stimulates DM1 ORNs only."""

import math
from dataclasses import dataclass

from .sugar import CONTACT_RADIUS, SugarField


@dataclass
class Source:
    x: float
    y: float
    kind: str
    age: float = 0.0
    amount: float = 1.0
    radius: float = 12.0

    @property
    def draw_radius(self):
        return self.radius


class Environment:
    def __init__(self, sugar: SugarField):
        self.sugar = sugar
        self.sources = []

    def add(self, kind, x, y):
        if kind == "food":
            return self.sugar.add(x, y)
        if kind not in ("bitter", "odor"):
            raise ValueError("kind must be food, bitter, or odor")
        source = Source(x, y, kind)
        self.sources.append(source)
        self.sources = self.sources[-12:]
        return source

    def sense(self, x, y):
        bitter = any(s.kind == "bitter" and math.hypot(x - s.x, y - s.y) <= CONTACT_RADIUS
                     for s in self.sources)
        odor = 0.0
        for source in self.sources:
            if source.kind == "odor":
                dx, dy = x - source.x, y - source.y
                sigma_x = 240 if dx >= 0 else 70
                odor += math.exp(-0.5 * ((dx / sigma_x) ** 2 + (dy / 90) ** 2))
        return float(bitter), min(1.0, odor)
