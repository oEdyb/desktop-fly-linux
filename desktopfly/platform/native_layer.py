"""GTK4 layer-shell renderer; each monitor is a stationary pointer coordinate space."""

import base64
import json
import os
import sys

import cairo
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_foreign("cairo")
from gi.repository import Gdk, GLib, Gtk


def emit(event, **values):
    print(json.dumps({"event": event, **values}, separators=(",", ":")), flush=True)


class MonitorLayer:
    def __init__(self, scene, monitor):
        gi.require_version("Gtk4LayerShell", "1.0")
        from gi.repository import Gtk4LayerShell as Layer

        self.scene = scene
        self.geometry = monitor.get_geometry()
        self.window = Gtk.Window()
        Layer.init_for_window(self.window)
        Layer.set_namespace(self.window, "desktopfly")
        Layer.set_monitor(self.window, monitor)
        Layer.set_layer(self.window, Layer.Layer.OVERLAY)
        Layer.set_keyboard_mode(self.window, Layer.KeyboardMode.NONE)
        Layer.set_exclusive_zone(self.window, -1)
        for edge in (Layer.Edge.TOP, Layer.Edge.BOTTOM, Layer.Edge.LEFT, Layer.Edge.RIGHT):
            Layer.set_anchor(self.window, edge, True)
        self.fixed = Gtk.Fixed()
        self.window.set_child(self.fixed)
        self.pictures = {}
        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self.motion)
        motion.connect("leave", self.leave)
        self.window.add_controller(motion)
        drag = Gtk.GestureDrag()
        drag.set_button(1)
        drag.connect("drag-begin", self.begin)
        drag.connect("drag-update", self.update)
        drag.connect("drag-end", self.end)
        drag.connect("cancel", self.cancel)
        self.window.add_controller(drag)
        click = Gtk.GestureClick()
        click.set_button(3)
        click.connect("pressed", self.right_click)
        self.window.add_controller(click)
        self.window.connect("map", lambda *_: self.region())
        self.window.present()

    def point(self, x, y):
        return x + self.geometry.x, y + self.geometry.y

    def motion(self, _controller, x, y):
        x, y = self.point(x, y)
        emit("pointer", x=x, y=y)

    def leave(self, _controller):
        if self.scene.active is None:
            emit("leave")

    def begin(self, gesture, x, y):
        x, y = self.point(x, y)
        key = self.scene.hit(x, y)
        if key is None or not self.scene.entries[key]["drag"]:
            gesture.set_state(Gtk.EventSequenceState.DENIED)
            if key is not None and self.scene.entries[key]["click"]:
                emit("click", id=key, button=1)
            return
        self.scene.active = key
        self.scene.start = self.scene.last = (x, y)
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)
        self.scene.regions()
        emit("pointer", x=x, y=y)
        emit("press", id=key)

    def update(self, _gesture, dx, dy):
        if self.scene.active is not None:
            self.scene.move_pointer(self.scene.start[0] + dx, self.scene.start[1] + dy)

    def end(self, gesture, dx, dy):
        self.update(gesture, dx, dy)
        self.scene.drop()

    def cancel(self, *_):
        self.scene.drop()

    def right_click(self, _gesture, _count, x, y):
        x, y = self.point(x, y)
        key = self.scene.hit(x, y)
        if key is not None:
            emit("click", id=key, button=3)

    def region(self):
        surface = self.window.get_surface()
        if surface is None:
            return
        region = cairo.Region()
        if self.scene.active is not None:
            region.union(cairo.RectangleInt(0, 0, self.geometry.width, self.geometry.height))
        else:
            for entry in self.scene.entries.values():
                radius = entry["radius"]
                if radius and entry["visible"]:
                    x = int(entry["x"] + entry["width"] / 2 - self.geometry.x)
                    y = int(entry["y"] + entry["height"] / 2 - self.geometry.y)
                    r = int(radius)
                    region.union(cairo.RectangleInt(x - r, y - r, r * 2 + 1, r * 2 + 1))
        surface.set_input_region(region)

    def render(self, key, entry, raised=False):
        picture = self.pictures.get(key)
        if picture is None:
            picture = Gtk.Picture()
            picture.set_can_target(False)
            picture.set_size_request(entry["width"], entry["height"])
            self.fixed.put(picture, 0, 0)
            self.pictures[key] = picture
        elif raised:
            self.fixed.remove(picture)
            self.fixed.put(picture, 0, 0)
        x, y = entry["x"] - self.geometry.x, entry["y"] - self.geometry.y
        visible = (entry["visible"] and x < self.geometry.width and y < self.geometry.height
                   and x + entry["width"] > 0 and y + entry["height"] > 0)
        picture.set_visible(visible)
        self.fixed.move(picture, x, y)
        if entry.get("texture") is not None:
            picture.set_paintable(entry["texture"])


class Scene:
    def __init__(self):
        self.entries = {}
        self.active = None
        self.start = self.last = (0, 0)
        self.buffer = b""
        monitors = Gdk.Display.get_default().get_monitors()
        while monitors.get_n_items() == 0:
            GLib.MainContext.default().iteration(True)
        self.layers = [MonitorLayer(self, monitors.get_item(i)) for i in range(monitors.get_n_items())]

    def hit(self, x, y):
        for key, entry in reversed(self.entries.items()):
            radius = entry["radius"]
            if entry["visible"] and radius and (entry["drag"] or entry["click"]):
                dx = x - entry["x"] - entry["width"] / 2
                dy = y - entry["y"] - entry["height"] / 2
                if abs(dx) <= radius and abs(dy) <= radius:
                    return key
        return None

    def move_pointer(self, x, y):
        previous = self.last
        self.last = (x, y)
        emit("pointer", x=x, y=y)
        if (x, y) != previous:
            emit("drag", id=self.active, dx=x - previous[0], dy=y - previous[1])

    def drop(self):
        if self.active is not None:
            key, self.active = self.active, None
            emit("drop", id=key)
            self.regions()

    def regions(self):
        for layer in self.layers:
            layer.region()

    def command(self, data):
        op, key = data["op"], data["id"]
        if op == "create":
            self.entries[key] = {**data, "x": -10000, "y": -10000, "visible": True,
                                 "radius": 24 if data["body"] else 0}
        elif op == "destroy":
            if self.active == key:
                self.drop()
            self.entries.pop(key, None)
            for layer in self.layers:
                picture = layer.pictures.pop(key, None)
                if picture:
                    layer.fixed.remove(picture)
            self.regions()
            return
        elif key not in self.entries:
            return
        elif op == "frame":
            entry = self.entries[key]
            pixels = GLib.Bytes.new(base64.b64decode(data["pixels"]))
            entry["texture"] = Gdk.MemoryTexture.new(
                entry["width"], entry["height"], Gdk.MemoryFormat.B8G8R8A8_PREMULTIPLIED,
                pixels, data["stride"],
            )
        elif op == "raise":
            self.entries[key] = self.entries.pop(key)
        else:
            self.entries[key].update(data)
        for layer in self.layers:
            layer.render(key, self.entries[key], op == "raise")
        if op != "frame":
            self.regions()

    def receive(self, descriptor, _condition):
        chunk = os.read(descriptor, 262144)
        if not chunk:
            loop.quit()
            return False
        self.buffer += chunk
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            self.command(json.loads(line))
        return True


if __name__ == "__main__":
    Gtk.init()
    provider = Gtk.CssProvider()
    provider.load_from_data(b"window { background-color: transparent; }")
    Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, 800)
    scene = Scene()
    emit("ready")
    loop = GLib.MainLoop()
    GLib.io_add_watch(sys.stdin.fileno(), GLib.IO_IN | GLib.IO_HUP, scene.receive)
    loop.run()
