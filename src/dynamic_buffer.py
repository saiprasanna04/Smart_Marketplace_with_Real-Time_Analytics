"""Explicitly managed dynamic event storage for amortised analysis."""


class DynamicEventBuffer:
    """A growable array that copies elements itself when its capacity fills.

    The backing list is preallocated and changed only by indexed assignment.
    This makes the buffer's copy operations visible instead of relying on
    Python's hidden list growth strategy.
    """

    def __init__(self, initial_capacity: int = 1) -> None:
        if initial_capacity <= 0:
            raise ValueError("initial_capacity must be greater than 0")
        self._storage: list[object | None] = [None] * initial_capacity
        self._size = 0
        self._capacity = initial_capacity
        self._cumulative_copies = 0
        self._total_actual_writes = 0
        self.operation_log: list[dict[str, int]] = []

    @property
    def size(self) -> int:
        """Number of events currently stored."""
        return self._size

    @property
    def capacity(self) -> int:
        """Number of event slots currently allocated."""
        return self._capacity

    @property
    def cumulative_copies(self) -> int:
        """Total existing elements copied during all growth operations."""
        return self._cumulative_copies

    @property
    def total_actual_writes(self) -> int:
        """Copies plus appended event writes; allocation initialization is excluded."""
        return self._total_actual_writes

    def append(self, event: object) -> dict[str, int]:
        """Append one event, doubling capacity and explicitly copying if full."""
        copies_this_append = 0

        if self._size == self._capacity:
            old_storage = self._storage
            new_capacity = self._capacity * 2
            new_storage: list[object | None] = [None] * new_capacity

            # Copy each live event with a visible indexed write.
            for index in range(self._size):
                new_storage[index] = old_storage[index]
                copies_this_append += 1
            self._storage = new_storage
            self._capacity = new_capacity

        # This is the one write that stores the newly appended event.
        self._storage[self._size] = event
        self._size += 1
        writes_this_append = copies_this_append + 1
        self._cumulative_copies += copies_this_append
        self._total_actual_writes += writes_this_append

        row = {
            "appended_events": self._size,
            "capacity": self._capacity,
            "copies_this_append": copies_this_append,
            "cumulative_copies": self._cumulative_copies,
            "writes_this_append": writes_this_append,
            "total_actual_writes": self._total_actual_writes,
        }
        self.operation_log.append(row)
        return dict(row)

    def to_list(self) -> list[object | None]:
        """Return a new list containing only the events currently stored."""
        return self._storage[: self._size]

    def __len__(self) -> int:
        return self._size

    def __iter__(self):
        for index in range(self._size):
            yield self._storage[index]
