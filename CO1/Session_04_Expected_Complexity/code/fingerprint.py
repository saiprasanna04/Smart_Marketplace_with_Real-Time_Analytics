"""Fingerprint-assisted duplicate candidate lookup with exact verification."""

import hashlib
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass


MAX_FINGERPRINT_BITS = hashlib.sha256().digest_size * 8


def description_fingerprint(description: str, width_bits: int = MAX_FINGERPRINT_BITS) -> str:
    """Return a stable SHA-256-based fingerprint narrowed to ``width_bits``."""
    if not isinstance(description, str):
        raise TypeError("description must be a string")
    if not 1 <= width_bits <= MAX_FINGERPRINT_BITS:
        raise ValueError(f"width_bits must be between 1 and {MAX_FINGERPRINT_BITS}")

    digest_value = int.from_bytes(
        hashlib.sha256(description.encode("utf-8")).digest(), "big"
    )
    fingerprint_value = digest_value & ((1 << width_bits) - 1)
    hex_width = (width_bits + 3) // 4
    return f"{fingerprint_value:0{hex_width}x}"


@dataclass(frozen=True)
class FingerprintCheck:
    """Outcome and work counts for inserting one product into a fingerprint index."""

    fingerprint: str
    is_duplicate: bool
    collision_product_ids: tuple[str, ...]
    candidate_checks: int
    exact_comparisons: int


class FingerprintIndex:
    """Map each fingerprint to records, then verify each candidate's full text."""

    def __init__(self, width_bits: int = MAX_FINGERPRINT_BITS) -> None:
        if not 1 <= width_bits <= MAX_FINGERPRINT_BITS:
            raise ValueError(f"width_bits must be between 1 and {MAX_FINGERPRINT_BITS}")
        self.width_bits = width_bits
        self._buckets: dict[str, list[Mapping[str, object]]] = defaultdict(list)

    def add(self, product: Mapping[str, object]) -> FingerprintCheck:
        """Check same-fingerprint candidates exactly, then store this product."""
        description = product.get("description")
        product_id = str(product.get("product_id", "<unknown>"))
        if not isinstance(description, str):
            raise ValueError(f"Product {product_id!r} must have a string description")

        key = description_fingerprint(description, self.width_bits)
        candidates = self._buckets[key]
        exact_matches = 0
        collisions: list[str] = []

        # A matching fingerprint only narrows candidates; the original text decides.
        for candidate in candidates:
            candidate_description = candidate["description"]
            if candidate_description == description:
                exact_matches += 1
            else:
                collisions.append(str(candidate.get("product_id", "<unknown>")))

        candidates.append(product)
        return FingerprintCheck(
            fingerprint=key,
            is_duplicate=exact_matches > 0,
            collision_product_ids=tuple(collisions),
            candidate_checks=len(candidates) - 1,
            exact_comparisons=len(candidates) - 1,
        )


@dataclass(frozen=True)
class DuplicateSummary:
    duplicate_product_ids: tuple[str, ...]
    description_comparisons: int
    fingerprint_candidate_checks: int
    exact_comparisons: int
    collision_pairs: int


def naive_pairwise_duplicates(
    products: Iterable[Mapping[str, object]],
) -> tuple[tuple[str, ...], int]:
    """Compare every new description with all previously seen descriptions."""
    earlier: list[Mapping[str, object]] = []
    duplicate_ids: list[str] = []
    comparisons = 0
    for product in products:
        description = product["description"]
        is_duplicate = False
        for previous in earlier:
            comparisons += 1
            if previous["description"] == description:
                is_duplicate = True
        if is_duplicate:
            duplicate_ids.append(str(product.get("product_id", "<unknown>")))
        earlier.append(product)
    return tuple(duplicate_ids), comparisons


def fingerprint_duplicates(
    products: Iterable[Mapping[str, object]], width_bits: int = MAX_FINGERPRINT_BITS
) -> DuplicateSummary:
    """Find duplicates through fingerprint buckets and exact description checks."""
    index = FingerprintIndex(width_bits)
    duplicate_ids: list[str] = []
    candidates_checked = 0
    exact_comparisons = 0
    collision_pairs = 0

    for product in products:
        outcome = index.add(product)
        if outcome.is_duplicate:
            duplicate_ids.append(str(product.get("product_id", "<unknown>")))
        candidates_checked += outcome.candidate_checks
        exact_comparisons += outcome.exact_comparisons
        collision_pairs += len(outcome.collision_product_ids)

    return DuplicateSummary(
        duplicate_product_ids=tuple(duplicate_ids),
        description_comparisons=exact_comparisons,
        fingerprint_candidate_checks=candidates_checked,
        exact_comparisons=exact_comparisons,
        collision_pairs=collision_pairs,
    )
