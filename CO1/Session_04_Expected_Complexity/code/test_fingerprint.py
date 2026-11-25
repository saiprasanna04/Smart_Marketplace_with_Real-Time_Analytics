"""Tests for exact verification of fingerprint duplicate candidates."""

import unittest

from src.fingerprint import (
    FingerprintIndex,
    description_fingerprint,
    fingerprint_duplicates,
)


def product(product_id: str, description: str) -> dict[str, str]:
    return {"product_id": product_id, "description": description}


def colliding_descriptions(width_bits: int, count: int) -> list[str]:
    buckets: dict[str, list[str]] = {}
    for number in range(10_000):
        text = f"collision candidate {number}"
        key = description_fingerprint(text, width_bits)
        buckets.setdefault(key, []).append(text)
        if len(buckets[key]) == count:
            return buckets[key]
    raise AssertionError("Could not find enough deterministic fingerprint collisions")


class FingerprintTests(unittest.TestCase):
    def test_identical_descriptions_are_duplicates(self) -> None:
        result = fingerprint_duplicates(
            [product("A", "same description"), product("B", "same description")]
        )
        self.assertEqual(result.duplicate_product_ids, ("B",))
        self.assertEqual(result.exact_comparisons, 1)

    def test_different_descriptions_are_not_duplicates(self) -> None:
        result = fingerprint_duplicates([product("A", "first"), product("B", "second")])
        self.assertEqual(result.duplicate_product_ids, ())

    def test_deliberate_fingerprint_collision_is_not_a_duplicate(self) -> None:
        first, second = colliding_descriptions(1, 2)
        self.assertEqual(
            description_fingerprint(first, 1), description_fingerprint(second, 1)
        )
        index = FingerprintIndex(width_bits=1)
        index.add(product("A", first))
        outcome = index.add(product("B", second))
        self.assertFalse(outcome.is_duplicate)
        self.assertEqual(outcome.collision_product_ids, ("A",))

    def test_multiple_candidates_are_checked_exactly(self) -> None:
        first, other = colliding_descriptions(2, 2)
        index = FingerprintIndex(width_bits=2)
        index.add(product("A", first))
        index.add(product("B", other))
        outcome = index.add(product("C", first))
        self.assertTrue(outcome.is_duplicate)
        self.assertEqual(outcome.candidate_checks, 2)
        self.assertEqual(outcome.collision_product_ids, ("B",))

    def test_empty_descriptions_can_be_duplicates(self) -> None:
        result = fingerprint_duplicates([product("A", ""), product("B", "")])
        self.assertEqual(result.duplicate_product_ids, ("B",))


if __name__ == "__main__":
    unittest.main()
