"""Small cProfile/pstats helpers used by the Session 5 profiling script."""

import cProfile
import csv
import io
import pstats
from collections.abc import Callable
from pathlib import Path
from typing import Any


def profile_callable(function: Callable[..., Any], *args: object, **kwargs: object) -> tuple[Any, cProfile.Profile]:
    """Run one callable under cProfile and return its result and profile object."""
    profiler = cProfile.Profile()
    result = profiler.runcall(function, *args, **kwargs)
    return result, profiler


def profile_rows(profile_name: str, profiler: cProfile.Profile) -> list[dict[str, object]]:
    """Convert pstats entries into rows sorted by cumulative time."""
    stats = pstats.Stats(profiler)
    rows: list[dict[str, object]] = []
    for (filename, line_number, function_name), values in stats.stats.items():
        primitive_calls, total_calls, total_time, cumulative_time, _callers = values
        rows.append(
            {
                "profile": profile_name,
                "function_name": function_name,
                "file": f"{filename}:{line_number}",
                "number_of_calls": total_calls,
                "primitive_calls": primitive_calls,
                "total_time_seconds": total_time,
                "cumulative_time_seconds": cumulative_time,
            }
        )
    return sorted(rows, key=lambda row: float(row["cumulative_time_seconds"]), reverse=True)


def write_profile_text(profiles: list[tuple[str, cProfile.Profile]], destination: Path) -> None:
    """Save readable pstats output for each profiled workload."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as output_file:
        for name, profiler in profiles:
            output_file.write(f"=== {name} ===\n")
            stats = pstats.Stats(profiler, stream=output_file).strip_dirs()
            stats.sort_stats("cumulative").print_stats(20)


def write_profile_csv(profiles: list[tuple[str, cProfile.Profile]], destination: Path) -> None:
    """Save call counts and self/cumulative times as a machine-readable CSV."""
    rows = [row for name, profiler in profiles for row in profile_rows(name, profiler)]
    destination.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "profile",
        "function_name",
        "file",
        "number_of_calls",
        "primitive_calls",
        "total_time_seconds",
        "cumulative_time_seconds",
    ]
    with destination.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
