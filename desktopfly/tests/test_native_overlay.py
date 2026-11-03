import subprocess
import sys
import textwrap
import unittest


class NativeOverlayTest(unittest.TestCase):
    def test_native_hit_grab_release_cancel_and_destroy(self):
        code = '''
            from types import SimpleNamespace
            from unittest.mock import Mock
            from desktopfly.platform import native_layer as native
            from gi.repository import Gtk
            events = []
            native.emit = lambda event, **values: events.append((event, values))
            scene = native.Scene.__new__(native.Scene)
            food = dict(x=100, y=100, width=72, height=72, radius=12,
                        visible=True, drag=True, click=True)
            scene.entries = {0: food, 1: {**food, "radius": 24, "drag": False, "click": False}}
            scene.active = None
            scene.start = scene.last = (0, 0)
            layer = native.MonitorLayer.__new__(native.MonitorLayer)
            layer.scene = scene
            layer.geometry = SimpleNamespace(x=0, y=0, width=1920, height=1080)
            layer.window = Mock()
            layer.pictures = {}
            scene.layers = [layer]
            surface = layer.window.get_surface.return_value
            assert scene.hit(136, 136) == 0, "Body must not block Food"
            layer.right_click(None, 1, 136, 136)
            assert events[-1] == ("click", {"id": 0, "button": 3})
            layer.region()
            assert not surface.set_input_region.call_args.args[0].contains_point(1900, 1000)
            gesture = Mock()
            layer.begin(gesture, 140, 133)
            assert scene.active == 0
            assert scene.start == (140, 133)
            gesture.set_state.assert_called_with(Gtk.EventSequenceState.CLAIMED)
            assert events[-1] == ("press", {"id": 0})
            assert surface.set_input_region.call_args.args[0].contains_point(1900, 1000)
            layer.update(gesture, 200, 40)
            assert events[-1] == ("drag", {"id": 0, "dx": 200, "dy": 40})
            layer.end(gesture, 202, 37)
            assert events[-2] == ("drag", {"id": 0, "dx": 2, "dy": -3})
            assert events[-1] == ("drop", {"id": 0}) and scene.active is None
            assert not surface.set_input_region.call_args.args[0].contains_point(1900, 1000)
            before = len(events)
            layer.cancel()
            assert len(events) == before, "Drop cannot repeat"
            layer.begin(gesture, 136, 136)
            layer.cancel()
            assert scene.active is None and events[-1][0] == "drop"
            layer.begin(gesture, 136, 136)
            scene.command({"op": "destroy", "id": 0})
            assert scene.active is None and 0 not in scene.entries
            assert scene.hit(136, 136) is None, "Only the noninteractive body remains"
            assert not surface.set_input_region.call_args.args[0].contains_point(1900, 1000)
        '''
        result = subprocess.run([sys.executable, '-c', textwrap.dedent(code)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
