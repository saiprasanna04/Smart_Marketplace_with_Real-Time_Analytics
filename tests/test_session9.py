"""Session 9 suffix-array/LCP correctness and document-boundary checks."""

import unittest

from src.suffix_index import (
    SuffixArrayIndex,
    build_lcp_array,
    build_suffix_array,
    guided_dc3_trace,
)


class Session9SuffixIndexTests(unittest.TestCase):
    def test_known_suffix_array_and_lcp_for_banana(self) -> None:
        suffix_array = build_suffix_array("banana")
        self.assertEqual(suffix_array, [5, 3, 1, 0, 4, 2])
        self.assertEqual(build_lcp_array("banana", suffix_array), [0, 1, 3, 0, 0, 2])

    def test_search_matches_direct_scanning_and_absent_query(self) -> None:
        documents = {"P1": "cacao cocoa", "P2": "cocoa cacao", "P3": "no match"}
        index = SuffixArrayIndex(documents)
        for query in ("ca", "coa", "cocoa", "match", "absent"):
            actual = {(row["document_id"], row["offset"]) for row in index.search(query)}
            expected = {
                (document_id, offset)
                for document_id, text in documents.items()
                for offset in range(len(text))
                if text.startswith(query, offset)
            }
            self.assertEqual(actual, expected)

    def test_unique_separators_prevent_cross_document_matches(self) -> None:
        index = SuffixArrayIndex({"left": "cat", "right": "alog"})
        self.assertEqual(index.search("talog"), [])
        self.assertEqual(index.search("cat"), [{"document_id": "left", "offset": 0}])
        self.assertEqual(index.search("alog"), [{"document_id": "right", "offset": 0}])

    def test_empty_documents_and_empty_query(self) -> None:
        index = SuffixArrayIndex({"empty": "", "text": "ab"})
        self.assertEqual(index.search(""), [])
        self.assertEqual(index.search("a"), [{"document_id": "text", "offset": 0}])

    def test_dc3_trace_is_explicitly_guided_not_executed(self) -> None:
        trace = guided_dc3_trace("banana")
        self.assertEqual(trace["kind"], "guided trace")
        self.assertFalse(trace["algorithm_executed"])
        self.assertEqual(trace["implementation_used_for_index"], "prefix doubling")


if __name__ == "__main__":
    unittest.main()
