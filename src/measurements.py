"""Small standard-library helpers for approximate in-memory object sizes."""

import sys


def deep_size_bytes(value: object, seen: set[int] | None = None) -> int:
    """Estimate reachable Python object memory using ``sys.getsizeof``.

    Shared objects are counted once. This is an estimate of Python object
    sizes, not process resident memory and not a measurement of native memory
    used by the operating system or hardware caches.
    """
    if seen is None:
        seen = set()
    object_id = id(value)
    if object_id in seen:
        return 0
    seen.add(object_id)
    total = sys.getsizeof(value)

    if isinstance(value, dict):
        total += sum(deep_size_bytes(key, seen) for key in value.keys())
        total += sum(deep_size_bytes(item, seen) for item in value.values())
    elif isinstance(value, (list, tuple, set, frozenset)):
        total += sum(deep_size_bytes(item, seen) for item in value)
    elif hasattr(value, "__dict__"):
        total += deep_size_bytes(vars(value), seen)

    return total
