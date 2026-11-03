"""Draggable taste droplets and a click-through odor plume."""

import math

import cairo

from ..render.sugar_renderer import SugarRenderer
from .overlay import Overlay


class EnvironmentItem:
    TILE = 72

    def __init__(self, source, kind, monitor, remove, on_drop=None):
        self.drop = source
        self.kind = kind
        self.monitor = monitor
        self.remove = remove
        self.on_drop = on_drop
        self.preview = None
        self.overlay = Overlay(self.TILE, self.TILE, on_click=lambda e: remove(source) if e.button == 3 else None,
                               on_drag=self.drag, on_pickup=self.pickup, on_drop=self.finish_drag)
        self.renderer = SugarRenderer(self.TILE)
        self.plume = Overlay(600, 300) if kind == "odor" else None
        self._last_radius = -1
        self.draw()

    def drag(self, dx, dy):
        self.drop.x += dx
        self.drop.y -= dy
        self.draw()

    def pickup(self):
        self.preview = Overlay(self.TILE, self.TILE)
        self.overlay.blit(cairo.ImageSurface(cairo.FORMAT_ARGB32, self.TILE, self.TILE))
        self.draw(force=True)

    def finish_drag(self):
        m = self.monitor
        self.drop.x = min(m["width"] / 2 - 15, max(-m["width"] / 2 + 15, self.drop.x))
        self.drop.y = min(m["height"] / 2 - 15, max(-m["height"] / 2 + 15, self.drop.y))
        if self.on_drop:
            self.on_drop(self.drop)
        if self.preview:
            self.preview.destroy()
            self.preview = None
        self.draw(force=True)

    def contains(self, x, y):
        cx, cy = self.center()
        return math.hypot(x - cx, y - cy) <= max(12, self.drop.draw_radius + 2)

    def center(self):
        m = self.monitor
        return m["x"] + m["width"] / 2 + self.drop.x, m["y"] + m["height"] / 2 - self.drop.y

    def draw(self, force=False):
        cx, cy = self.center()
        visual = self.preview or self.overlay
        visual.move(cx - self.TILE / 2, cy - self.TILE / 2)
        if self.plume:
            self.plume.move(cx - 100, cy - 150)
        radius = self.drop.draw_radius
        if not force and abs(radius - self._last_radius) < 0.35:
            return
        self._last_radius = radius
        if self.kind == "food":
            surface = self.renderer.render(self.drop)
        else:
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.TILE, self.TILE)
            cr = cairo.Context(surface)
            color = (0.75, 0.28, 0.92) if self.kind == "bitter" else (0.15, 0.82, 0.75)
            cr.set_source_rgba(*color, 0.95)
            cr.arc(36, 36, 12, 0, 2 * math.pi)
            cr.fill()
            cr.set_source_rgb(1, 1, 1)
            cr.set_font_size(15)
            cr.move_to(31, 41)
            cr.show_text("B" if self.kind == "bitter" else "O")
        visual.blit(surface)
        self.overlay.set_input_circle(max(12, radius + 2))
        if self.plume:
            self._draw_plume()
            self.overlay.raise_()

    def _draw_plume(self):
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 600, 300)
        cr = cairo.Context(surface)
        cr.translate(100, 150)
        cr.scale(2.5, 1)
        gradient = cairo.RadialGradient(0, 0, 2, 0, 0, 130)
        gradient.add_color_stop_rgba(0, 0.2, 0.8, 0.7, 0.16)
        gradient.add_color_stop_rgba(1, 0.2, 0.8, 0.7, 0)
        cr.set_source(gradient)
        cr.arc(0, 0, 130, 0, 2 * math.pi)
        cr.fill()
        self.plume.blit(surface)

    def destroy(self):
        self.overlay.destroy()
        if self.preview:
            self.preview.destroy()
            self.preview = None
        if self.plume:
            self.plume.destroy()
