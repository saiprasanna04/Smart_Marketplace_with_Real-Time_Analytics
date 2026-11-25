"""Suffix-array and LCP indexing over separated product descriptions.

The executable constructor uses prefix doubling.  A DC3/skew construction
trace is provided separately as a guided teaching aid and is never presented
as the constructor used for measurements.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def build_suffix_array(values: Sequence[int] | str, operation_counts: dict[str, int] | None = None) -> list[int]:
    """Build a suffix array with prefix doubling in O(n log^2 n) in Python."""
    symbols = [ord(character) for character in values] if isinstance(values, str) else list(values)
    size = len(symbols)
    if not size:
        return []
    suffixes = list(range(size))
    ranks = symbols[:]
    width = 1
    passes = sort_key_evaluations = rank_pair_comparisons = 0
    while width < size:
        passes += 1
        sort_key_evaluations += size
        suffixes.sort(
            key=lambda index: (
                ranks[index],
                ranks[index + width] if index + width < size else -1,
            )
        )
        next_ranks = [0] * size
        for position in range(1, size):
            previous = suffixes[position - 1]
            current = suffixes[position]
            previous_key = (
                ranks[previous],
                ranks[previous + width] if previous + width < size else -1,
            )
            current_key = (
                ranks[current],
                ranks[current + width] if current + width < size else -1,
            )
            rank_pair_comparisons += 1
            next_ranks[current] = next_ranks[previous] + (current_key != previous_key)
        ranks = next_ranks
        width *= 2
    if operation_counts is not None:
        operation_counts.update(
            {
                "doubling_passes": passes,
                "sort_key_evaluations": sort_key_evaluations,
                "rank_pair_comparisons": rank_pair_comparisons,
            }
        )
    return suffixes


def build_lcp_array(
    values: Sequence[int] | str,
    suffix_array: Sequence[int],
    operation_counts: dict[str, int] | None = None,
) -> list[int]:
    """Kasai LCP array where entry i compares SA[i-1] with SA[i]."""
    symbols = [ord(character) for character in values] if isinstance(values, str) else list(values)
    size = len(symbols)
    if len(suffix_array) != size or sorted(suffix_array) != list(range(size)):
        raise ValueError("suffix_array must be a permutation of every text position")
    inverse = [0] * size
    for rank, suffix_start in enumerate(suffix_array):
        inverse[suffix_start] = rank
    lcp = [0] * size
    common = 0
    character_comparisons = 0
    for start in range(size):
        rank = inverse[start]
        if rank == 0:
            continue
        previous = suffix_array[rank - 1]
        while (
            start + common < size
            and previous + common < size
            and symbols[start + common] == symbols[previous + common]
        ):
            character_comparisons += 1
            common += 1
        if start + common < size and previous + common < size:
            character_comparisons += 1
        lcp[rank] = common
        if common:
            common -= 1
    if operation_counts is not None:
        operation_counts["character_comparisons"] = character_comparisons
    return lcp


class SuffixArrayIndex:
    """Exact substring lookup across documents with distinct sentinels."""

    def __init__(self, documents: Mapping[str, str]) -> None:
        self.document_ids = list(documents)
        self.documents = dict(documents)
        self.symbols: list[int] = []
        self.position_to_document: list[int | None] = []
        self.position_to_offset: list[int] = []
        self.document_lengths: list[int] = []
        for document_number, (document_id, text) in enumerate(self.documents.items()):
            if not isinstance(text, str):
                raise TypeError(f"document {document_id!r} must be a string")
            self.document_lengths.append(len(text))
            self.symbols.extend(ord(character) for character in text)
            self.position_to_document.extend([document_number] * len(text))
            self.position_to_offset.extend(range(len(text)))
            # Negative, document-unique symbols cannot occur in a query.
            self.symbols.append(-(document_number + 1))
            self.position_to_document.append(None)
            self.position_to_offset.append(-1)
        self.construction_operations: dict[str, int] = {}
        self.suffix_array = build_suffix_array(self.symbols, self.construction_operations)
        self.lcp_operations: dict[str, int] = {}
        self.lcp_array = build_lcp_array(self.symbols, self.suffix_array, self.lcp_operations)
        self.query_character_comparisons = 0

    def _compare_query(self, suffix_start: int, query: Sequence[int]) -> int:
        for offset, symbol in enumerate(query):
            position = suffix_start + offset
            if position >= len(self.symbols):
                return -1
            candidate = self.symbols[position]
            self.query_character_comparisons += 1
            if candidate < symbol:
                return -1
            if candidate > symbol:
                return 1
        return 0

    def search(self, query: str) -> list[dict[str, Any]]:
        """Return every exact occurrence without allowing a match across documents."""
        if not isinstance(query, str):
            raise TypeError("query must be a string")
        if not query:
            return []
        encoded = [ord(character) for character in query]
        low, high = 0, len(self.suffix_array)
        while low < high:
            middle = (low + high) // 2
            if self._compare_query(self.suffix_array[middle], encoded) < 0:
                low = middle + 1
            else:
                high = middle
        matches: list[dict[str, Any]] = []
        position = low
        while position < len(self.suffix_array):
            suffix_start = self.suffix_array[position]
            if self._compare_query(suffix_start, encoded) != 0:
                break
            document_number = self.position_to_document[suffix_start]
            offset = self.position_to_offset[suffix_start]
            if (
                document_number is not None
                and offset + len(query) <= self.document_lengths[document_number]
            ):
                matches.append(
                    {
                        "document_id": self.document_ids[document_number],
                        "offset": offset,
                    }
                )
            position += 1
        matches.sort(key=lambda result: (self.document_ids.index(result["document_id"]), result["offset"]))
        return matches


def product_description_documents(products: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    """Extract exact description text keyed by stable product IDs."""
    return {str(product["product_id"]): str(product["description"]) for product in products}


def guided_dc3_trace(text: str) -> dict[str, Any]:
    """Return an illustrative DC3 construction trace, not an executed DC3 run."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    positions = list(range(len(text)))
    sample = [position for position in positions if position % 3 in (1, 2)]
    return {
        "kind": "guided trace",
        "algorithm_executed": False,
        "implementation_used_for_index": "prefix doubling",
        "text": text,
        "steps": [
            {"step": "1. Add sentinels", "detail": "Append three out-of-alphabet sentinel symbols for merge comparisons."},
            {"step": "2. Sample mod-1/mod-2 suffixes", "positions": sample},
            {"step": "3. Rank triples", "detail": "Sort sampled suffixes by their first three symbols and assign ranks."},
            {"step": "4. Sort mod-0 suffixes", "detail": "Use the first symbol and the sampled rank two positions ahead."},
            {"step": "5. Merge", "detail": "Merge the two sorted groups using constant-size rank comparisons."},
        ],
        "note": "This is a guided DC3 trace; local suffix-array results use the tested prefix-doubling constructor.",
    }


def suffix_demo(products: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    documents = product_description_documents(products)
    index = SuffixArrayIndex(documents)
    query = "USB-C"
    return {
        "document_count": len(documents),
        "indexed_symbols": len(index.symbols),
        "construction": "prefix doubling (measured implementation)",
        "suffix_array_prefix": index.suffix_array[:24],
        "lcp_prefix": index.lcp_array[:24],
        "query": query,
        "matches": index.search(query),
        "absent_query_matches": index.search("__not_in_catalogue__"),
        "dc3_trace": guided_dc3_trace("banana"),
    }
