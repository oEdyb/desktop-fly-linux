import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from desktopfly.platform.brain_window import BrainWindow


def event(x, y, button=1):
    return SimpleNamespace(x=x, y=y, button=button)


class BrainInputTest(unittest.TestCase):
    def setUp(self):
        self.brain = BrainWindow.__new__(BrainWindow)
        self.brain.renderer = SimpleNamespace(angle=0.0, tilt=-0.15)
        self.brain._press = None
        self.brain._dragged = False
        self.brain._on_click = Mock(return_value=True)

    def test_drag_rotates_without_stimulation(self):
        self.brain._on_press(None, event(100, 100))
        self.brain._on_motion(None, event(200, 50))
        self.brain._on_release(None, event(200, 50))
        self.assertAlmostEqual(self.brain.renderer.angle, 1.0)
        self.assertAlmostEqual(self.brain.renderer.tilt, -0.65)
        self.brain._on_click.assert_not_called()

    def test_small_pointer_jitter_still_stimulates(self):
        self.brain._on_press(None, event(100, 100))
        release = event(102, 101)
        self.brain._on_release(None, release)
        self.brain._on_click.assert_called_once_with(None, release)

    def test_right_click_does_not_stimulate(self):
        self.assertFalse(self.brain._on_press(None, event(100, 100, 3)))
        self.assertFalse(self.brain._on_release(None, event(100, 100, 3)))
        self.brain._on_click.assert_not_called()


if __name__ == '__main__':
    unittest.main()
