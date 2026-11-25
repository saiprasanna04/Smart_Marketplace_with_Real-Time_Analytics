# Session 10: Suffix automata for description text

## Implementation and verification

The implementation is in `src/` and correctness checks are in `tests/test_session10.py`. The benchmark below was generated locally with the standard-library script `benchmarks/benchmark_m2.py`.

## Measured results

Trials per row: 5. Timings are local medians. Memory is a recursive `sys.getsizeof` object-graph estimate, not process RSS.

| Algorithm | Baseline | Input size | Queries | Median ms | Operations | Memory bytes | Correct |
|---|---|---:|---:|---:|---:|---:|:---:|
| Per-document suffix automata | direct substring scans | 3771 | 5 | 43.808400 | 12273 | 2242154 | true |
| Direct substring scan | simple baseline | 3771 | 5 | 2.348500 | 19416 | 5753 | true |

## Measurement notes

- Counts transition-existence checks during construction and transition checks during queries; direct scans are the oracle.
- Counts character comparisons over all description positions; baseline comparison count 19416.

Results are from this run and depend on machine load. Complexity claims are theoretical; operation counts follow the named counters or explicitly described loop visits.
