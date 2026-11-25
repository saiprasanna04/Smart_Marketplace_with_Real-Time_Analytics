"""Per-document suffix automata for exact description-substring lookup."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass
class _State:
    length: int
    link: int
    transitions: dict[str, int] = field(default_factory=dict)
    first_end: int = -1
    occurrences: int = 0
    is_clone: bool = False


class SuffixAutomaton:
    """Suffix automaton with suffix links, transition trace, and counts."""

    def __init__(self, text: str) -> None:
        if not isinstance(text, str):
            raise TypeError("suffix automaton input must be a string")
        self.text = text
        self.states = [_State(length=0, link=-1)]
        self._last = 0
        self.clone_trace: list[dict[str, Any]] = []
        self.construction_operations = 0
        for position, character in enumerate(text):
            self._extend(character, position)
        self._propagate_occurrences()
        self.query_operations = 0

    def _extend(self, character: str, position: int) -> None:
        current = len(self.states)
        self.states.append(
            _State(length=self.states[self._last].length + 1, link=0, first_end=position, occurrences=1)
        )
        cursor = self._last
        while cursor != -1:
            self.construction_operations += 1
            if character in self.states[cursor].transitions:
                break
            self.states[cursor].transitions[character] = current
            cursor = self.states[cursor].link

        if cursor == -1:
            self.states[current].link = 0
        else:
            target = self.states[cursor].transitions[character]
            if self.states[cursor].length + 1 == self.states[target].length:
                self.states[current].link = target
            else:
                clone_id = len(self.states)
                clone_source = self.states[target]
                clone = _State(
                    length=self.states[cursor].length + 1,
                    link=clone_source.link,
                    transitions=dict(clone_source.transitions),
                    first_end=clone_source.first_end,
                    occurrences=0,
                    is_clone=True,
                )
                self.states.append(clone)
                while cursor != -1:
                    self.construction_operations += 1
                    if self.states[cursor].transitions.get(character) != target:
                        break
                    self.states[cursor].transitions[character] = clone_id
                    cursor = self.states[cursor].link
                self.states[target].link = clone_id
                self.states[current].link = clone_id
                self.clone_trace.append(
                    {
                        "position": position,
                        "character": character,
                        "clone_state": clone_id,
                        "source_state": target,
                        "clone_length": clone.length,
                        "clone_suffix_link": clone.link,
                        "redirected_transitions": True,
                    }
                )
        self._last = current

    def _propagate_occurrences(self) -> None:
        for state_id in sorted(range(1, len(self.states)), key=lambda index: self.states[index].length, reverse=True):
            parent = self.states[state_id].link
            if parent >= 0:
                self.states[parent].occurrences += self.states[state_id].occurrences

    def state_for(self, query: str) -> int | None:
        if not isinstance(query, str):
            raise TypeError("query must be a string")
        if not query:
            return 0
        current = 0
        for character in query:
            self.query_operations += 1
            next_state = self.states[current].transitions.get(character)
            if next_state is None:
                return None
            current = next_state
        return current

    def contains(self, query: str) -> bool:
        return self.state_for(query) is not None

    def occurrence_count(self, query: str) -> int:
        state_id = self.state_for(query)
        if state_id is None:
            return 0
        return self.states[state_id].occurrences

    def trace(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "states": [
                {
                    "state": state_id,
                    "length": state.length,
                    "suffix_link": state.link,
                    "transitions": dict(sorted(state.transitions.items())),
                    "clone": state.is_clone,
                    "occurrences": state.occurrences,
                }
                for state_id, state in enumerate(self.states)
            ],
            "clones": list(self.clone_trace),
        }


class ProductDescriptionAutomata:
    """One suffix automaton per product description, with explicit product IDs."""

    def __init__(self, documents: Mapping[str, str]) -> None:
        self.automata = {
            str(product_id): SuffixAutomaton(description)
            for product_id, description in documents.items()
        }

    def search(self, query: str) -> list[dict[str, Any]]:
        if not query:
            return []
        matches = []
        for product_id, automaton in self.automata.items():
            count = automaton.occurrence_count(query)
            if count:
                matches.append({"document_id": product_id, "occurrences": count})
        return matches

    def trace_for(self, product_id: str) -> dict[str, Any]:
        try:
            return self.automata[product_id].trace()
        except KeyError as error:
            raise KeyError(f"No automaton exists for product {product_id!r}") from error


def automaton_demo(documents: Mapping[str, str]) -> dict[str, Any]:
    """Build product automata and compare one query with direct suffix lookup."""
    index = ProductDescriptionAutomata(documents)
    sample_product_id = next(iter(documents), None)
    sample_text = documents[sample_product_id] if sample_product_id is not None else ""
    query = "noise"
    trace_automaton = SuffixAutomaton("banana")
    return {
        "document_count": len(documents),
        "query": query,
        "matches": index.search(query),
        "guided_clone_example": trace_automaton.trace(),
        "multi_document_strategy": "one independent automaton per product description",
        "sample_document_id": sample_product_id,
        "sample_document_characters": len(sample_text),
    }
