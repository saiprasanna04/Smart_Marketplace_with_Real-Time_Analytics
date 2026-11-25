"""Session 11 path-query and dynamic-forest checks."""

import random
import unittest
from collections import deque

from src.category_forest import HeavyLightDecomposition, LinkCutForest, category_forest_demo


def naive_path(adjacency, values, start, end):
    previous = {start: None}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        if node == end:
            break
        for neighbor in adjacency[node]:
            if neighbor not in previous:
                previous[neighbor] = node
                queue.append(neighbor)
    if end not in previous:
        raise ValueError("unconnected")
    total = 0
    node = end
    while node is not None:
        total += values[node]
        node = previous[node]
    return total


class Session11CategoryTreeTests(unittest.TestCase):
    def test_hld_matches_naive_paths_and_point_updates(self) -> None:
        rng = random.Random(1111)
        values = {f"C{index}": rng.randrange(-5, 20) for index in range(24)}
        edges = [(f"C{i}", f"C{(i - 1) // 2}") for i in range(1, 24)]
        adjacency = {node: set() for node in values}
        for left, right in edges:
            adjacency[left].add(right)
            adjacency[right].add(left)
        hld = HeavyLightDecomposition(values, edges)
        for _ in range(120):
            left = f"C{rng.randrange(24)}"
            right = f"C{rng.randrange(24)}"
            self.assertEqual(hld.path_sum(left, right), naive_path(adjacency, values, left, right))
            if rng.random() < 0.2:
                node = f"C{rng.randrange(24)}"
                values[node] = rng.randrange(-10, 30)
                hld.update_value(node, values[node])
        self.assertGreater(hld.path_segments_visited, 0)

    def test_hld_rejects_cycles_and_disconnected_path_queries(self) -> None:
        with self.assertRaises(ValueError):
            HeavyLightDecomposition({"A": 1, "B": 2, "C": 3}, [("A", "B"), ("B", "C"), ("C", "A")])
        forest = HeavyLightDecomposition({"A": 1, "B": 2}, [])
        with self.assertRaises(ValueError):
            forest.path_sum("A", "B")

    def test_link_cut_links_cuts_cycle_rejection_and_path_sum(self) -> None:
        forest = LinkCutForest({"A": 1, "B": 2, "C": 3, "D": 4})
        forest.link("A", "B")
        forest.link("B", "C")
        forest.link("C", "D")
        self.assertTrue(forest.connected("A", "D"))
        self.assertEqual(forest.path_sum("A", "D"), 10)
        with self.assertRaises(ValueError):
            forest.link("A", "D")
        forest.cut("B", "C")
        self.assertFalse(forest.connected("A", "D"))
        with self.assertRaises(ValueError):
            forest.path_sum("A", "D")
        forest.link("A", "D")
        self.assertEqual(forest.path_sum("B", "D"), 7)
        with self.assertRaises(ValueError):
            forest.cut("B", "D")

    def test_link_cut_dynamic_operations_match_naive_forest(self) -> None:
        rng = random.Random(1112)
        values = {str(index): rng.randrange(1, 20) for index in range(12)}
        forest = LinkCutForest(values)
        adjacency = {node: set() for node in values}
        for _ in range(150):
            left, right = rng.sample(list(values), 2)
            if rng.random() < 0.57:
                connected = forest.connected(left, right)
                if connected:
                    with self.assertRaises(ValueError):
                        forest.link(left, right)
                else:
                    forest.link(left, right)
                    adjacency[left].add(right)
                    adjacency[right].add(left)
            elif adjacency[left] and rng.random() < 0.5:
                neighbor = rng.choice(sorted(adjacency[left]))
                forest.cut(left, neighbor)
                adjacency[left].remove(neighbor)
                adjacency[neighbor].remove(left)
            else:
                connected = forest.connected(left, right)
                self.assertEqual(connected, self._connected(adjacency, left, right))
                if connected:
                    self.assertEqual(forest.path_sum(left, right), naive_path(adjacency, values, left, right))

    @staticmethod
    def _connected(adjacency, start, end):
        queue = [start]
        visited = {start}
        while queue:
            node = queue.pop()
            if node == end:
                return True
            for neighbor in adjacency[node] - visited:
                visited.add(neighbor)
                queue.append(neighbor)
        return False

    def test_category_demo_rejects_cycle_after_valid_link_cut_trace(self) -> None:
        result = category_forest_demo()
        self.assertEqual(result["initial_path_sum"], 11)
        self.assertTrue(result["cycle_rejected"])
        self.assertEqual([row["status"] for row in result["trace"]], ["applied"] * 4)


if __name__ == "__main__":
    unittest.main()
