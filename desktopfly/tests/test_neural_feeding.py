import unittest

from desktopfly.body.fly import Fly, State
from desktopfly.simcore.signals import BrainSignals


class NeuralFeedingTest(unittest.TestCase):
    def test_contact_needs_motor_output(self):
        fly = Fly()
        fly.state = State.IDLE
        fly.state_age = 1
        signal = BrainSignals(sugar_contact=True, feeding_output=False)
        fly.brain_behavior(signal, 0.016, (1920, 1080), None)
        self.assertIsNot(fly.state, State.FEEDING)
        signal.feeding_output = True
        fly.brain_behavior(signal, 0.016, (1920, 1080), None)
        self.assertIs(fly.state, State.FEEDING)
        fly.state_age = 1
        signal.feeding_output = False
        fly.brain_behavior(signal, 0.016, (1920, 1080), None)
        self.assertIsNot(fly.state, State.FEEDING)

    def test_escape_still_outranks_mn9(self):
        fly = Fly()
        fly.state = State.FEEDING
        signal = BrainSignals(sugar_contact=True, feeding_output=True, escape=True)
        fly.brain_behavior(signal, 0.016, (1920, 1080), None)
        self.assertIs(fly.state, State.FLYING)
