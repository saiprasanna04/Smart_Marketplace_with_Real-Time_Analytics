"""Static and dynamic category-tree path aggregation for Session 11."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from src.range_queries import FenwickTree


class HeavyLightDecomposition:
    """Heavy-light path sums over a static forest with point-value updates."""

    def __init__(
        self,
        values: Mapping[str, int],
        edges: Iterable[tuple[str, str]],
    ) -> None:
        self.values = dict(values)
        self.adjacency: dict[str, list[str]] = {node: [] for node in self.values}
        for left, right in edges:
            if left not in self.values or right not in self.values:
                raise ValueError("every category edge must name a known category")
            if left == right:
                raise ValueError("category hierarchy cannot contain a self-cycle")
            self.adjacency[left].append(right)
            self.adjacency[right].append(left)

        self.parent: dict[str, str | None] = {}
        self.depth: dict[str, int] = {}
        self.component: dict[str, int] = {}
        self.heavy: dict[str, str | None] = {}
        roots: list[str] = []
        visited: set[str] = set()
        for root in self.values:
            if root in visited:
                continue
            component_id = len(roots)
            roots.append(root)
            self.parent[root] = None
            self.depth[root] = 0
            self.component[root] = component_id
            visited.add(root)
            stack = [(root, None)]
            order: list[str] = []
            while stack:
                node, parent = stack.pop()
                order.append(node)
                for neighbor in self.adjacency[node]:
                    if neighbor == parent:
                        continue
                    if neighbor in visited:
                        raise ValueError("category hierarchy edges must form a forest")
                    visited.add(neighbor)
                    self.parent[neighbor] = node
                    self.depth[neighbor] = self.depth[node] + 1
                    self.component[neighbor] = component_id
                    stack.append((neighbor, node))
            subtree_size = {node: 1 for node in order}
            self.heavy.update({node: None for node in order})
            for node in reversed(order):
                parent_node = self.parent[node]
                if parent_node is not None:
                    subtree_size[parent_node] += subtree_size[node]
                    current_heavy = self.heavy[parent_node]
                    if current_heavy is None or subtree_size[node] > subtree_size[current_heavy]:
                        self.heavy[parent_node] = node

        self.head: dict[str, str] = {}
        self.position: dict[str, int] = {}
        ordered_values: list[int] = []
        next_position = 0
        pending_chains = [(root, root) for root in reversed(roots)]
        while pending_chains:
            node, chain_head = pending_chains.pop()
            while node is not None:
                self.head[node] = chain_head
                self.position[node] = next_position
                ordered_values.append(int(self.values[node]))
                next_position += 1
                for child in self.adjacency[node]:
                    if self.parent.get(child) == node and child != self.heavy[node]:
                        pending_chains.append((child, child))
                node = self.heavy[node]
        self._tree = FenwickTree(ordered_values)
        self.path_segments_visited = 0

    def update_value(self, node: str, value: int) -> None:
        if node not in self.position:
            raise KeyError(node)
        self.values[node] = value
        self._tree.point_update(self.position[node], value)

    def _interval_sum(self, left: int, right: int) -> int:
        self.path_segments_visited += 1
        return int(self._tree.range_sum(left, right))

    def path_sum(self, left: str, right: str) -> int:
        if left not in self.position or right not in self.position:
            raise KeyError("path query references an unknown category")
        if self.component[left] != self.component[right]:
            raise ValueError("path endpoints belong to different category trees")
        total = 0
        while self.head[left] != self.head[right]:
            if self.depth[self.head[left]] < self.depth[self.head[right]]:
                left, right = right, left
            chain_head = self.head[left]
            total += self._interval_sum(self.position[chain_head], self.position[left] + 1)
            parent = self.parent[chain_head]
            if parent is None:
                raise ValueError("path traversal reached a different forest root")
            left = parent
        if self.depth[left] > self.depth[right]:
            left, right = right, left
        total += self._interval_sum(self.position[left], self.position[right] + 1)
        return total


@dataclass
class _LinkCutNode:
    key: str
    value: int
    parent: "_LinkCutNode | None" = None
    left: "_LinkCutNode | None" = None
    right: "_LinkCutNode | None" = None
    reversed: bool = False
    aggregate: int = 0

    def __post_init__(self) -> None:
        self.aggregate = self.value


class LinkCutForest:
    """Link-cut tree supporting dynamic link, cut, connectivity, and path sums."""

    def __init__(self, values: Mapping[str, int]) -> None:
        self.nodes = {key: _LinkCutNode(key, int(value)) for key, value in values.items()}
        self.rotations = 0
        self.accesses = 0

    def _node(self, key: str) -> _LinkCutNode:
        try:
            return self.nodes[key]
        except KeyError as error:
            raise KeyError(f"unknown forest node {key!r}") from error

    @staticmethod
    def _aux_root(node: _LinkCutNode) -> bool:
        parent = node.parent
        return parent is None or (parent.left is not node and parent.right is not node)

    @staticmethod
    def _pull(node: _LinkCutNode) -> None:
        node.aggregate = (
            node.value
            + (node.left.aggregate if node.left else 0)
            + (node.right.aggregate if node.right else 0)
        )

    @staticmethod
    def _toggle(node: _LinkCutNode | None) -> None:
        if node is not None:
            node.left, node.right = node.right, node.left
            node.reversed = not node.reversed

    def _push(self, node: _LinkCutNode) -> None:
        if node.reversed:
            self._toggle(node.left)
            self._toggle(node.right)
            node.reversed = False

    def _rotate(self, node: _LinkCutNode) -> None:
        parent = node.parent
        if parent is None:
            return
        grandparent = parent.parent
        if parent.left is node:
            middle = node.right
            node.right = parent
            parent.left = middle
        else:
            middle = node.left
            node.left = parent
            parent.right = middle
        if middle is not None:
            middle.parent = parent
        parent.parent = node
        node.parent = grandparent
        if grandparent is not None:
            if grandparent.left is parent:
                grandparent.left = node
            elif grandparent.right is parent:
                grandparent.right = node
        self._pull(parent)
        self._pull(node)
        self.rotations += 1

    def _splay(self, node: _LinkCutNode) -> None:
        ancestors = [node]
        cursor = node
        while not self._aux_root(cursor):
            assert cursor.parent is not None
            cursor = cursor.parent
            ancestors.append(cursor)
        for ancestor in reversed(ancestors):
            self._push(ancestor)
        while not self._aux_root(node):
            parent = node.parent
            assert parent is not None
            grandparent = parent.parent
            if not self._aux_root(parent):
                assert grandparent is not None
                if (parent.left is node) == (grandparent.left is parent):
                    self._rotate(parent)
                else:
                    self._rotate(node)
            self._rotate(node)

    def _access(self, node: _LinkCutNode) -> None:
        self.accesses += 1
        last: _LinkCutNode | None = None
        cursor: _LinkCutNode | None = node
        while cursor is not None:
            self._splay(cursor)
            cursor.right = last
            if last is not None:
                last.parent = cursor
            self._pull(cursor)
            last = cursor
            cursor = cursor.parent
        self._splay(node)

    def _make_root(self, node: _LinkCutNode) -> None:
        self._access(node)
        self._toggle(node)

    def _find_root_node(self, node: _LinkCutNode) -> _LinkCutNode:
        self._access(node)
        cursor = node
        self._push(cursor)
        while cursor.left is not None:
            cursor = cursor.left
            self._push(cursor)
        self._splay(cursor)
        return cursor

    def connected(self, left: str, right: str) -> bool:
        if left == right:
            self._node(left)
            return True
        return self._find_root_node(self._node(left)) is self._find_root_node(self._node(right))

    def link(self, left: str, right: str) -> None:
        """Connect two components; reject a cycle-producing category move."""
        a, b = self._node(left), self._node(right)
        self._make_root(a)
        if self._find_root_node(b) is a:
            raise ValueError("link would create a cycle in the category forest")
        a.parent = b

    def cut(self, left: str, right: str) -> None:
        """Remove an existing direct edge or reject the requested cut."""
        a, b = self._node(left), self._node(right)
        self._make_root(a)
        self._access(b)
        if b.left is not a or a.right is not None:
            raise ValueError("cut endpoints are not joined by a direct forest edge")
        b.left.parent = None
        b.left = None
        self._pull(b)

    def path_sum(self, left: str, right: str) -> int:
        a, b = self._node(left), self._node(right)
        if not self.connected(left, right):
            raise ValueError("path endpoints are in different forest components")
        self._make_root(a)
        self._access(b)
        return b.aggregate

    def update_value(self, key: str, value: int) -> None:
        node = self._node(key)
        self._access(node)
        node.value = int(value)
        self._pull(node)


def marketplace_category_tree(
    category_sales: Mapping[str, int] | None = None,
) -> tuple[dict[str, int], list[tuple[str, str]]]:
    """Small deterministic hierarchy linking the actual catalogue categories."""
    category_sales = category_sales or {}
    parents = {
        "Electronics": "Technology",
        "Office Supplies": "Technology",
        "Accessories": "Technology",
        "Home & Kitchen": "Home",
        "Clothing": "Fashion",
        "Bags & Luggage": "Fashion",
        "Sports & Outdoors": "Sports",
    }
    values = {"Marketplace": 0, "Technology": 0, "Home": 0, "Fashion": 0, "Sports": 0}
    values.update({category: int(category_sales.get(category, 0)) for category in parents})
    edges = [(parent, "Marketplace") for parent in ("Technology", "Home", "Fashion", "Sports")]
    edges.extend((category, parent) for category, parent in parents.items())
    return values, edges


def category_forest_demo() -> dict[str, object]:
    values = {"Marketplace": 0, "Technology": 4, "Electronics": 7, "Office": 3}
    edges = [("Marketplace", "Technology"), ("Technology", "Electronics"), ("Technology", "Office")]
    forest = LinkCutForest(values)
    trace = []
    for left, right in edges:
        forest.link(left, right)
        trace.append({"operation": "link", "left": left, "right": right, "status": "applied"})
    path_total = forest.path_sum("Marketplace", "Electronics")
    try:
        forest.link("Marketplace", "Electronics")
        cycle_rejected = False
    except ValueError:
        cycle_rejected = True
    forest.cut("Technology", "Electronics")
    trace.append({"operation": "cut", "left": "Technology", "right": "Electronics", "status": "applied"})
    return {
        "initial_path_sum": path_total,
        "cycle_rejected": cycle_rejected,
        "trace": trace,
        "complexity": "Link-cut tree amortized O(log n) per link, cut, connectivity, or path aggregate.",
    }
