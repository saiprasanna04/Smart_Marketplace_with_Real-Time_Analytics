# Session 8: Persistent catalogue snapshots

## Implementation and verification

The implementation is in `src/` and correctness checks are in `tests/test_session8.py`. The benchmark below was generated locally with the standard-library script `benchmarks/benchmark_m2.py`.

## Measured results

Trials per row: 5. Timings are local medians. Memory is a recursive `sys.getsizeof` object-graph estimate, not process RSS.

| Algorithm | Baseline | Input size | Queries | Median ms | Operations | Memory bytes | Correct |
|---|---|---:|---:|---:|---:|---:|:---:|
| AVL path-copy snapshots | copy-on-write full dictionary snapshots | 500 | 24 | 6.418700 | 191 | 239538 | true |
| Copy-on-write snapshots | full snapshot baseline | 500 | 24 | 6.699100 | 12000 | 500054 | true |

## Measurement notes

- Operation count is the implementation's new immutable tree nodes across updates.
- Operation count is dictionary entries copied for each version; Python object sizes share unchanged row objects.

Results are from this run and depend on machine load. Complexity claims are theoretical; operation counts follow the named counters or explicitly described loop visits.
