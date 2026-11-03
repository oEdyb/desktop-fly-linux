"""The interactive brain window.

Port of ``BrainWindowController`` from upstream's ``BrainView.swift``: an
always-on-top utility window showing the live point cloud, where hovering holds
the rotation still and clicking "optogenetically" stimulates the ~60 circuit
neurons nearest the click ray.

Upstream uses a non-activating ``NSPanel`` so the window never steals focus.
The closest GTK equivalent is a utility-hint, keep-above window that does not
accept focus.
"""

from __future__ import annotations

import numpy as np

from .gtkcompat import Gdk, GdkPixbuf, GLib, Gtk


class BrainWindow:
    WIDTH = 340
    HEIGHT = 546

    def __init__(self, renderer, sim, on_stimulate=None, on_close=None,
                 sensory=None, on_add_item=None, on_reset_environment=None):
        self.renderer = renderer
        self.sim = sim
        self.sensory = sensory
        self.on_stimulate = on_stimulate
        # The brain window is the app's only real window, so its close button is
        # the obvious way to quit -- "Show/Hide Brain" in the tray is the way to
        # dismiss it without quitting.
        self.on_close = on_close

        self.win = Gtk.Window(title="Fly Brain — FlyWire v783 (click = stimulate)")
        self.win.set_default_size(self.WIDTH, self.HEIGHT)
        self.win.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.win.set_keep_above(True)
        self.win.set_skip_taskbar_hint(True)
        self.win.set_resizable(False)
        self.win.set_decorated(True)
        self.win.connect("delete-event", self._on_delete)

        overlay = Gtk.Overlay()
        self.image = Gtk.Image()
        events = Gtk.EventBox()
        events.add(self.image)
        events.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.ENTER_NOTIFY_MASK
            | Gdk.EventMask.LEAVE_NOTIFY_MASK
        )
        events.connect("button-press-event", self._on_press)
        events.connect("button-release-event", self._on_release)
        events.connect("motion-notify-event", self._on_motion)
        self._press = None
        self._dragged = False
        events.connect("enter-notify-event", self._on_enter)
        events.connect("leave-notify-event", self._on_leave)
        overlay.add(events)

        self.label = Gtk.Label()
        self.label.set_halign(Gtk.Align.CENTER)
        self.label.set_valign(Gtk.Align.END)
        self.label.set_margin_bottom(10)
        self.label.set_no_show_all(True)
        ctx = self.label.get_style_context()
        provider = Gtk.CssProvider()
        provider.load_from_data(
            b"label { background-color: rgba(0,0,0,0.62); color: #f2f2f2;"
            b" padding: 3px 8px; border-radius: 6px; font-size: 11px; }"
        )
        ctx.add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        overlay.add_overlay(self.label)
        overlay.set_overlay_pass_through(self.label, True)
        self.cut_label = Gtk.Label(label="LC4/LPLC2 ✕ GF")
        self.cut_label.set_halign(Gtk.Align.CENTER)
        self.cut_label.set_valign(Gtk.Align.START)
        self.cut_label.set_margin_top(8)
        self.cut_label.set_no_show_all(True)
        self.cut_label.set_markup('<span foreground="#ff6655"><b>LC4/LPLC2 ✕ GF</b></span>')
        overlay.add_overlay(self.cut_label)
        overlay.set_overlay_pass_through(self.cut_label, True)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        header = Gtk.EventBox()
        move_label = Gtk.Label()
        move_label.set_markup('<span foreground="#f2f2f2">Move brain</span>')
        header.add(move_label)
        header.set_size_request(-1, 28)
        header.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        header.connect("button-press-event", self._on_move_press)
        content.pack_start(header, False, False, 0)
        self.move_handle = header
        content.pack_start(overlay, False, False, 0)
        self.group_buttons = {}
        self.groups = {}
        for role, name in [("lc4", "LC4"), ("lplc2", "LPLC2"),
                           ("dnp09", "DNp09 · Walk"), ("mdn", "MDN · Moonwalk"),
                           ("gf", "GF · Bypass")]:
            picked = np.flatnonzero(np.asarray(sim.roles) == role)
            self.groups[role] = (name, picked)
            if role == "gf":
                self.cut_button = Gtk.ToggleButton(label="Cut LC4/LPLC2 → GF")
                self.cut_button.connect("toggled", self._on_cut_toggled)
                content.pack_start(self.cut_button, False, False, 0)
            button = Gtk.Button(label=name)
            button.set_sensitive(len(picked) > 0)
            button.connect("clicked", lambda _button, role=role: self.stimulate_group(role))
            content.pack_start(button, False, False, 0)
            self.group_buttons[role] = button
        self.item_buttons = {}
        if sensory:
            self.HEIGHT = 760
            palette = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            for kind, name in (("food", "Food"), ("bitter", "Bitter"), ("odor", "Smell")):
                button = Gtk.Button(label=name)
                button.connect("clicked", lambda _b, kind=kind: on_add_item(kind))
                palette.pack_start(button, True, True, 0)
                self.item_buttons[kind] = button
            content.pack_start(palette, False, False, 2)
            self.reset_environment = Gtk.Button(label="Reset environment")
            self.reset_environment.connect("clicked", lambda _b: on_reset_environment())
            content.pack_start(self.reset_environment, False, False, 0)
            self.sensory_label = Gtk.Label()
            self.sensory_label.set_line_wrap(True)
            content.pack_start(self.sensory_label, False, False, 2)
            self.odor_label = Gtk.Label()
            self.odor_label.set_markup('<span foreground="#e8eded">Odor: neural response only · no steering</span>')
            content.pack_start(self.odor_label, False, False, 2)
            self.win.set_default_size(self.WIDTH, self.HEIGHT)
        self.win.add(content)
        self._label_timer = None
        self._visible = False

    # ------------------------------------------------------------ events

    def _on_move_press(self, _widget, event):
        if event.button != 1:
            return False
        self.win.begin_move_drag(event.button, int(event.x_root), int(event.y_root), event.time)
        return True

    def contains_screen_point(self, x, y):
        if not self.visible:
            return False
        _ok, ox, oy = self.win.get_window().get_origin()
        return (ox <= x < ox + self.win.get_allocated_width()
                and oy <= y < oy + self.win.get_allocated_height())

    def _on_delete(self, *_):
        if self.on_close is not None:
            self.on_close()
            return True
        self.hide()
        return True  # stop the default destroy

    def _on_enter(self, *_):
        self.renderer.paused = True  # hold the rotation while aiming
        return False

    def _on_leave(self, *_):
        self.renderer.paused = False
        return False

    def _on_press(self, _widget, event):
        if event.button != 1:
            return False
        self._press = (event.x, event.y, self.renderer.angle, self.renderer.tilt)
        self._dragged = False
        return True

    def _on_motion(self, _widget, event):
        if self._press is None:
            return False
        x, y, angle, tilt = self._press
        dx, dy = event.x - x, event.y - y
        if dx * dx + dy * dy > 25:
            self._dragged = True
        if self._dragged:
            self.renderer.angle = angle + dx * 0.01
            self.renderer.tilt = max(-1.5, min(1.5, tilt + dy * 0.01))
        return True

    def _on_release(self, widget, event):
        if event.button != 1 or self._press is None:
            return False
        self._on_motion(widget, event)
        self._press = None
        if not self._dragged:
            return self._on_click(widget, event)
        return True

    def _on_click(self, _widget, event):
        picked, _anchor = self.renderer.nearest_neurons(event.x, event.y)
        if len(picked) == 0:
            return False
        self.sim.stimulate(picked, strength=0.25, duration_ms=400)
        for i in picked[:16]:
            self.renderer.flash(int(i), False)
        self._show_label(self.renderer.region_name(picked))
        if self.on_stimulate:
            self.on_stimulate(picked)
        return True

    def _on_cut_toggled(self, button):
        cut = button.get_active()
        self.sim.set_escape_inputs_cut(cut)
        self.cut_label.set_visible(cut)
        button.set_label("Restore LC4/LPLC2 → GF" if cut else "Cut LC4/LPLC2 → GF")

    def stimulate_group(self, role):
        name, picked = self.groups[role]
        if not len(picked):
            return
        duration = {"dnp09": 1200, "mdn": 600}.get(role, 400)
        self.sim.stimulate(picked, strength=0.25, duration_ms=duration)
        self._show_label(name)
        if self.on_stimulate:
            self.on_stimulate(picked)

    def _show_label(self, text: str) -> None:
        self.label.set_text(text)
        self.label.show()
        if self._label_timer:
            GLib.source_remove(self._label_timer)
        self._label_timer = GLib.timeout_add(2200, self._hide_label)

    def _hide_label(self):
        self.label.hide()
        self._label_timer = None
        return False

    # ------------------------------------------------------------ render

    def draw(self, dt: float) -> None:
        if not self._visible:
            return
        for role, (name, picked) in self.groups.items():
            rate = float(self.sim.neuron_rates[picked].mean()) if len(picked) else 0.0
            self.group_buttons[role].set_label(f"{name} · {len(picked)} neurons · {rate:.0f} Hz")
        if self.sensory:
            rates = self.sensory.rates
            status = "FEEDING" if self.sensory.feeding else "quiet"
            text = (f"Senses · {self.sensory.info['neurons']:,} neurons · {self.sensory.speed:.2f}×\n"
                    f"Sugar GRNs {rates['sugar']:.0f} · Bitter GRNs {rates['bitter']:.0f} Hz\n"
                    f"MN9 {rates['mn9']:.0f} Hz · {status}\n"
                    f"ORN_DM1 {rates['orn']:.0f} → DM1_lPN {rates['pn']:.0f} Hz")
            self.sensory_label.set_markup('<span foreground="#e8eded">'
                                          + GLib.markup_escape_text(self.sensory.error or text) + '</span>')
        self.renderer.drain_spikes()
        rgba = self.renderer.render(dt)
        h, w = rgba.shape[:2]
        pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(
            GLib.Bytes.new(np.ascontiguousarray(rgba).tobytes()),
            GdkPixbuf.Colorspace.RGB, True, 8, w, h, w * 4,
        )
        self.image.set_from_pixbuf(pixbuf)

    # ----------------------------------------------------------- control

    @property
    def visible(self) -> bool:
        return self._visible

    def show(self) -> None:
        self._visible = True
        self.win.show_all()
        self.label.hide()
        self.win.present()

    def hide(self) -> None:
        self._visible = False
        self.win.hide()

    def toggle(self) -> None:
        self.hide() if self._visible else self.show()

    def place_bottom_right(self, monitor: dict) -> None:
        x = monitor["x"] + monitor["width"] - self.WIDTH - 24
        y = monitor["y"] + monitor["height"] - self.HEIGHT - 64
        self.win.move(x, y)
