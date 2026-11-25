# Session 9: Suffix arrays and longest common prefixes

## Implementation and verification

The implementation is in `src/` and correctness checks are in `tests/test_session9.py`. The benchmark below was generated locally with the standard-library script `benchmarks/benchmark_m2.py`.

## Measured results

Trials per row: 5. Timings are local medians. Memory is a recursive `sys.getsizeof` object-graph estimate, not process RSS.

| Algorithm | Baseline | Input size | Queries | Median ms | Operations | Memory bytes | Correct |
|---|---|---:|---:|---:|---:|---:|:---:|
| Suffix array + Kasai LCP | direct substring scans | 3771 | 5 | 30.981800 | 99394 | 273972 | true |
| Direct substring scan | simple baseline | 3771 | 5 | 2.451200 | 19416 | 5753 | true |

## Measurement notes

- Measured build and exact queries; operation count includes rank-key evaluations, rank comparisons, LCP character comparisons, and query comparisons.
- Counts character comparisons over all description positions; baseline comparison count 19416.

Results are from this run and depend on machine load. Complexity claims are theoretical; operation counts follow the named counters or explicitly described loop visits.
