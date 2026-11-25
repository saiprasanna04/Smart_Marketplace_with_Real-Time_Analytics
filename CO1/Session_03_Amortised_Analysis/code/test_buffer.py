"""Tests for explicit dynamic event-buffer growth and preservation."""

import unittest

from src.dynamic_buffer import DynamicEventBuffer


class DynamicEventBufferTests(unittest.TestCase):
    def test_empty_buffer_has_no_events_or_writes(self) -> None:
        buffer = DynamicEventBuffer(initial_capacity=1)
        self.assertEqual(buffer.size, 0)
        self.assertEqual(buffer.to_list(), [])
        self.assertEqual(buffer.total_actual_writes, 0)

    def test_capacity_doubles_when_full(self) -> None:
        buffer = DynamicEventBuffer(initial_capacity=1)
        capacities = [buffer.append(f"E{number}")["capacity"] for number in range(1, 6)]
        self.assertEqual(capacities, [1, 2, 4, 4, 8])

    def test_events_are_preserved_across_growth(self) -> None:
        buffer = DynamicEventBuffer(initial_capacity=1)
        events = [{"event_id": number} for number in range(16)]
        for event in events:
            buffer.append(event)
        self.assertEqual(buffer.to_list(), events)
        self.assertEqual(list(buffer), events)

    def test_multiple_resizes_count_copies_and_writes(self) -> None:
        buffer = DynamicEventBuffer(initial_capacity=1)
        for number in range(16):
            buffer.append(number)
        self.assertEqual(buffer.capacity, 16)
        self.assertEqual(buffer.cumulative_copies, 15)
        self.assertEqual(buffer.total_actual_writes, 31)
        self.assertEqual([row["appended_events"] for row in buffer.operation_log], list(range(1, 17)))


if __name__ == "__main__":
    unittest.main()
