"""Unit tests for the record-based external-memory simulation."""

import unittest

from src.hardware_analysis import simulate_block_reads


class BlockReadSimulationTests(unittest.TestCase):
    def test_rounds_up_for_partial_last_block(self) -> None:
        self.assertEqual(simulate_block_reads(65, 64), 2)

    def test_empty_catalogue_needs_no_blocks(self) -> None:
        self.assertEqual(simulate_block_reads(0, 64), 0)

    def test_rejects_nonpositive_block_size(self) -> None:
        with self.assertRaises(ValueError):
            simulate_block_reads(10, 0)


if __name__ == "__main__":
    unittest.main()
