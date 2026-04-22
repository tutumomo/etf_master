"""
test_event_driven_scan_trigger.py — Tests for D1/D2 event-driven scan trigger logic

Tests the pure function `should_trigger_scan(event_flag, event_state) -> tuple[bool, str]`
which determines whether an event should trigger an immediate scan.
"""

import sys
from pathlib import Path

# Import the function from scripts/event_driven_scan_trigger.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from event_driven_scan_trigger import should_trigger_scan


class TestShouldTriggerScan:
    """Test cases for the pure function should_trigger_scan."""

    def test_no_event_flag(self):
        """Test: no event triggered.

        When event_flag is empty or triggered=False, should return (False, 'no_event').
        """
        event_flag = {}
        event_state = {}

        should_trigger, reason = should_trigger_scan(event_flag, event_state)

        assert should_trigger is False
        assert reason == 'no_event'

    def test_level_l1_too_low(self):
        """Test: level L1 is below threshold.

        L1 events should not trigger scans; only L2/L3 should.
        """
        event_flag = {
            'triggered': True,
            'level': 'L1',
            'should_notify': True,
            'event_hash': 'abc'
        }
        event_state = {}

        should_trigger, reason = should_trigger_scan(event_flag, event_state)

        assert should_trigger is False
        assert reason == 'level_too_low:L1'

    def test_should_notify_false(self):
        """Test: should_notify=False indicates notification already sent.

        If should_notify is False, the event has already been notified,
        so scan should not be triggered.
        """
        event_flag = {
            'triggered': True,
            'level': 'L2',
            'should_notify': False,
            'event_hash': 'abc'
        }
        event_state = {}

        should_trigger, reason = should_trigger_scan(event_flag, event_state)

        assert should_trigger is False
        assert reason == 'already_notified_same_hash'

    def test_same_hash_already_triggered(self):
        """Test: same event_hash has already triggered a scan.

        If the current event_hash matches the last triggered hash in event_state,
        cooldown applies and we should not re-trigger.
        """
        event_flag = {
            'triggered': True,
            'level': 'L3',
            'should_notify': True,
            'event_hash': 'abc123'
        }
        event_state = {
            'event_scan_triggered_hash': 'abc123'
        }

        should_trigger, reason = should_trigger_scan(event_flag, event_state)

        assert should_trigger is False
        assert reason == 'already_triggered_this_event'

    def test_l2_triggers(self):
        """Test: L2 event with new hash triggers scan.

        L2 event with should_notify=True and a new (different) event_hash
        should trigger a scan.
        """
        event_flag = {
            'triggered': True,
            'level': 'L2',
            'should_notify': True,
            'event_hash': 'newHash'
        }
        event_state = {
            'event_scan_triggered_hash': 'oldHash'
        }

        should_trigger, reason = should_trigger_scan(event_flag, event_state)

        assert should_trigger is True
        assert reason == 'event_L2'

    def test_l3_triggers(self):
        """Test: L3 event with clean state triggers scan.

        L3 event with should_notify=True and no prior hash in event_state
        should trigger a scan.
        """
        event_flag = {
            'triggered': True,
            'level': 'L3',
            'should_notify': True,
            'event_hash': 'hash456'
        }
        event_state = {}

        should_trigger, reason = should_trigger_scan(event_flag, event_state)

        assert should_trigger is True
        assert reason == 'event_L3'

    def test_triggered_false_with_level_l3(self):
        """Test: triggered=False takes precedence regardless of level.

        Even if level=L3 (which would normally trigger), if triggered=False,
        the no_event check should short-circuit and return (False, 'no_event').
        """
        event_flag = {
            'triggered': False,
            'level': 'L3',
            'should_notify': True,
            'event_hash': 'abc'
        }
        event_state = {}

        should_trigger, reason = should_trigger_scan(event_flag, event_state)

        assert should_trigger is False
        assert reason == 'no_event'
