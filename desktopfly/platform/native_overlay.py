"""Native Wayland drawing and pointer events in a separate GTK4 layer-shell client."""

import atexit
import base64
import json
import os
import select
import subprocess
import sys
from types import SimpleNamespace

from .gtkcompat import GLib, Gtk

_bridge = None


def native_pointer():
    return _bridge.pointer if _bridge is not None else None


class NativeBridge:
    def __init__(self):
        self.overlays = {}
        self.pointer = None
        self.buffer = b""
        self.next_id = 0
        environment = dict(os.environ, GDK_BACKEND="wayland", GSK_RENDERER="gl")
        environment["LD_PRELOAD"] = "libgtk4-layer-shell.so.0 " + os.environ.get("LD_PRELOAD", "")
        self.process = subprocess.Popen(
            [sys.executable, "-m", "desktopfly.platform.native_layer"],
            env=environment, stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0,
        )
        if not select.select([self.process.stdout], [], [], 10)[0] or self.process.stdout.readline() != b'{"event":"ready"}\n':
            self.close()
            raise RuntimeError("Niri overlays require GTK4, Gtk4LayerShell and python-gobject-cairo")
        os.set_blocking(self.process.stdout.fileno(), False)
        GLib.io_add_watch(self.process.stdout.fileno(), GLib.IO_IN | GLib.IO_HUP, self.receive)
        atexit.register(self.close)

    def send(self, data):
        payload = (json.dumps(data, separators=(",", ":")) + "\n").encode()
        view = memoryview(payload)
        while view:
            try:
                written = self.process.stdin.write(view)
            except (BrokenPipeError, OSError):
                Gtk.main_quit()
                raise RuntimeError("The native Wayland overlay stopped; restart desktopfly") from None
            view = view[written:]

    def receive(self, descriptor, condition):
        chunk = os.read(descriptor, 65536)
        if not chunk:
            Gtk.main_quit()
            return False
        self.buffer += chunk
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            event = json.loads(line)
            if event["event"] == "pointer":
                self.pointer = (event["x"], event["y"])
                continue
            if event["event"] == "leave":
                self.pointer = None
                continue
            overlay = self.overlays.get(event.get("id"))
            if overlay is None:
                continue
            if event["event"] == "press":
                overlay._drag.active = True
                if overlay._on_pickup:
                    overlay._on_pickup()
            elif event["event"] == "drag":
                overlay._on_drag(event["dx"], event["dy"])
            elif event["event"] == "drop":
                overlay._drag.active = False
                if overlay._on_drop:
                    overlay._on_drop()
            elif event["event"] == "click" and overlay._on_click:
                overlay._on_click(SimpleNamespace(button=event["button"]))
        return True

    def close(self):
        if self.process.poll() is None:
            self.process.stdin.close()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.terminate()


class NativeOverlay:
    def __init__(self, width, height, name, on_click, on_drag, on_drop, on_pickup):
        global _bridge
        if _bridge is None:
            _bridge = NativeBridge()
        self.bridge = _bridge
        self.id = self.bridge.next_id
        self.bridge.next_id += 1
        self.bridge.overlays[self.id] = self
        self.width, self.height = width, height
        self._x = self._y = -10000
        self._drag = SimpleNamespace(active=False)
        self._on_click, self._on_drag = on_click, on_drag
        self._on_drop, self._on_pickup = on_drop, on_pickup
        self.bridge.send({"op": "create", "id": self.id, "width": width, "height": height,
                          "drag": on_drag is not None, "click": on_click is not None, "body": name == "desktopfly-body"})

    def move(self, x, y):
        x, y = int(x), int(y)
        if (x, y) != (self._x, self._y):
            self._x, self._y = x, y
            self.bridge.send({"op": "move", "id": self.id, "x": x, "y": y})

    def blit(self, surface):
        surface.flush()
        self.bridge.send({"op": "frame", "id": self.id, "stride": surface.get_stride(),
                          "pixels": base64.b64encode(surface.get_data()).decode("ascii")})

    def set_input_circle(self, radius):
        self.bridge.send({"op": "radius", "id": self.id, "radius": radius})

    def raise_(self):
        self.bridge.send({"op": "raise", "id": self.id})

    def set_visible(self, visible):
        self.bridge.send({"op": "visible", "id": self.id, "visible": visible})

    def destroy(self):
        self.bridge.send({"op": "destroy", "id": self.id})
        self.bridge.overlays.pop(self.id, None)
