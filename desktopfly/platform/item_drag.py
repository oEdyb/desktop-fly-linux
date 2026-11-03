"""Capture a stationary input window while a separate drag preview follows motion."""

from .gtkcompat import Gdk, GLib


class ItemDrag:
    def __init__(self, window, sample, move, drop):
        self.window = window
        self.sample = sample
        self.move = move
        self.drop = drop
        self.seat = None
        self.timer = None
        self.last = None

    @property
    def active(self):
        return self.last is not None

    def press(self, event, point=None):
        self.cancel()
        seat = self.window.get_display().get_default_seat()
        status = seat.grab(self.window, Gdk.SeatCapabilities.ALL_POINTING,
                           False, None, event, None, None)
        if status != Gdk.GrabStatus.SUCCESS:
            return False
        self.seat = seat
        self.last = point if point is not None else self.sample()[:2]
        self.window.raise_()
        self.timer = GLib.timeout_add(8, self.poll)
        return True

    def update(self, point=None):
        if not self.active:
            return
        x, y = point if point is not None else self.sample()[:2]
        previous_x, previous_y = self.last
        self.last = (x, y)
        if x != previous_x or y != previous_y:
            self.move(x - previous_x, y - previous_y)

    def poll(self):
        if not self.active:
            self.timer = None
            return False
        _x, _y, held = self.sample()
        if not held:
            self.timer = None
            self.release(self.last)
            return False
        return True

    def release(self, point=None):
        if not self.active:
            return False
        try:
            self.update(point)
        finally:
            self.cancel(notify=False)
        if self.drop:
            self.drop()
        return True

    def cancel(self, notify=True):
        was_active = self.active
        self.last = None
        if self.timer is not None:
            GLib.source_remove(self.timer)
            self.timer = None
        if self.seat is not None:
            self.seat.ungrab()
            self.seat = None
        if was_active and notify and self.drop:
            self.drop()
