import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from desktopfly.app import DesktopFly
from desktopfly.platform.gtkcompat import Gdk
from desktopfly.platform.environment_item import EnvironmentItem
from desktopfly.platform.item_drag import ItemDrag
from desktopfly.platform.niri_coordinates import NiriCoordinates
from desktopfly.world.environment import Source
from desktopfly.world.sugar import SugarDrop


class ItemDragTest(unittest.TestCase):
    def test_fixed_source_motion_and_release_preserve_the_grab_offset(self):
        window = Mock()
        seat = window.get_display.return_value.get_default_seat.return_value
        seat.grab.return_value = Gdk.GrabStatus.SUCCESS
        move, drop = Mock(), Mock()
        drag = ItemDrag(window, lambda: (999, 999, True), move, drop)
        with patch('desktopfly.platform.item_drag.GLib.timeout_add', return_value=1), \
             patch('desktopfly.platform.item_drag.GLib.source_remove'):
            self.assertTrue(drag.press(Mock(), (40, 33)))
            drag.poll()
            move.assert_not_called()
            drag.update((240, 73))
            move.assert_called_once_with(200, 40)
            drag.release((242, 70))
            self.assertFalse(drag.active)
            self.assertFalse(drag.release((900, 900)))
            move.assert_called_with(2, -3)
            drop.assert_called_once()
            seat.ungrab.assert_called_once()

    def test_lost_release_is_detected_without_following_a_stale_cursor(self):
        window = Mock()
        window.get_display.return_value.get_default_seat.return_value.grab.return_value = Gdk.GrabStatus.SUCCESS
        move, drop = Mock(), Mock()
        drag = ItemDrag(window, lambda: (999, 999, False), move, drop)
        with patch('desktopfly.platform.item_drag.GLib.timeout_add', return_value=1):
            drag.press(Mock(), (36, 36))
            self.assertFalse(drag.poll())
        self.assertFalse(drag.active)
        move.assert_not_called()
        drop.assert_called_once()

    def test_bitter_snaps_only_to_nearby_food(self):
        app = DesktopFly.__new__(DesktopFly)
        food = SugarDrop(100, 200)
        app.sugar = SimpleNamespace(drops=[food])
        app.item_views = []
        source = Source(120, 210, 'bitter')
        app.snap_item(source)
        self.assertEqual((source.x, source.y), (100, 200))
        source.x = 150
        app.snap_item(source)
        self.assertEqual(source.x, 150)


class NiriCoordinatesTest(unittest.TestCase):
    def test_brain_on_the_second_monitor_uses_global_coordinates(self):
        parent = Mock()
        parent.get_title.return_value = "Fly Brain"
        coords = NiriCoordinates(parent)
        coords.windows = lambda: [{"title": "Fly Brain", "workspace_id": 2,
                                  "layout": {"tile_pos_in_workspace_view": [100, 50],
                                             "window_offset_in_tile": [4, 6]}}]
        coords.workspaces = [{"id": 2, "output": "DP-3"}]
        coords.outputs = {"DP-3": {"logical": {"x": 2560, "y": 0}}}
        self.assertEqual(coords.origin(), (2664, 56))


class DropBoundsTest(unittest.TestCase):
    def test_offscreen_release_is_reachable_before_snapping(self):
        item = EnvironmentItem.__new__(EnvironmentItem)
        item.monitor = {"width": 1920, "height": 1080}
        item.drop = Source(2000, -1000, "bitter")
        item.preview = None
        item.draw = Mock()
        positions = []
        item.on_drop = lambda drop: positions.append((drop.x, drop.y))
        item.finish_drag()
        self.assertEqual(positions, [(945, -525)])
        item.drop.x, item.drop.y = 123, 234
        item.finish_drag()
        self.assertEqual(positions[-1], (123, 234))
