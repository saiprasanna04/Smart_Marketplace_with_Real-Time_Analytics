"""Session 10 tests against direct scanning and the Session 9 suffix array."""

import random
import unittest

from src.suffix_automaton import ProductDescriptionAutomata, SuffixAutomaton
from src.suffix_index import SuffixArrayIndex


class Session10SuffixAutomatonTests(unittest.TestCase):
    def test_exact_membership_and_occurrence_count(self) -> None:
        automaton = SuffixAutomaton("banana")
        self.assertTrue(automaton.contains("ana"))
        self.assertEqual(automaton.occurrence_count("ana"), 2)
        self.assertFalse(automaton.contains("apple"))
        self.assertEqual(automaton.occurrence_count("apple"), 0)

    def test_clone_is_traced_for_repeated_string(self) -> None:
        trace = SuffixAutomaton("banana").trace()
        self.assertTrue(trace["clones"])
        clone_ids = {entry["clone_state"] for entry in trace["clones"]}
        self.assertTrue(any(state["clone"] and state["state"] in clone_ids for state in trace["states"]))
        self.assertTrue(all(entry["redirected_transitions"] for entry in trace["clones"]))

    def test_multi_document_results_match_suffix_array_and_direct_scan(self) -> None:
        documents = {
            "P1": "anana banana",
            "P2": "bandana",
            "P3": "cocoa cacao",
        }
        automata = ProductDescriptionAutomata(documents)
        suffixes = SuffixArrayIndex(documents)
        for query in ("ana", "ban", "nana", "cacao", "missing"):
            actual = {row["document_id"]: row["occurrences"] for row in automata.search(query)}
            suffix_matches = suffixes.search(query)
            expected_counts = {}
            for row in suffix_matches:
                expected_counts[row["document_id"]] = expected_counts.get(row["document_id"], 0) + 1
            self.assertEqual(actual, expected_counts)
            direct_counts = {
                product_id: sum(1 for offset in range(len(text)) if text.startswith(query, offset))
                for product_id, text in documents.items()
            }
            self.assertEqual(actual, {key: value for key, value in direct_counts.items() if value})

    def test_deterministic_randomized_membership_matches_naive(self) -> None:
        rng = random.Random(1010)
        for _ in range(20):
            text = "".join(rng.choice("abc") for _ in range(18))
            automaton = SuffixAutomaton(text)
            for _ in range(40):
                start = rng.randrange(len(text))
                width = rng.randrange(1, 5)
                query = text[start : start + width]
                self.assertEqual(automaton.contains(query), query in text)
            self.assertFalse(automaton.contains("z"))

    def test_empty_query_is_not_listed_as_a_product_match(self) -> None:
        index = ProductDescriptionAutomata({"P1": "text"})
        self.assertEqual(index.search(""), [])


if __name__ == "__main__":
    unittest.main()
