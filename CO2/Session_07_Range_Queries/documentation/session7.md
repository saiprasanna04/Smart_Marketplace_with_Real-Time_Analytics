# Session 7: Range queries and lazy updates

## Implementation and verification

The implementation is in `src/` and correctness checks are in `tests/test_session7.py`. The benchmark below was generated locally with the standard-library script `benchmarks/benchmark_m2.py`.

## Measured results

Trials per row: 5. Timings are local medians. Memory is a recursive `sys.getsizeof` object-graph estimate, not process RSS.

| Algorithm | Baseline | Input size | Queries | Median ms | Operations | Memory bytes | Correct |
|---|---|---:|---:|---:|---:|---:|:---:|
| FenwickTree | naive point-update/range-sum array | 2048 | 160 | 4.356900 | 2939 | 58713 | true |
| Naive array | direct baseline | 2048 | 160 | 6.846300 | 105987 | 27248 | true |
| LazySegmentTree | naive range-add/range-sum array | 2048 | 160 | 9.743700 | 7001 | 174694 | true |
| Naive range array | direct baseline | 2048 | 160 | 8.847800 | 167174 | 30244 | true |

## Measurement notes

- Python counter counts Fenwick internal-node reads/writes; range convention is half-open.
- Counts each updated element and each array element read by range sums.
- Counts recursive segment-tree node visits; update/query workload is deterministic.
- Counts each item changed by an update and each item read by a sum.

Results are from this run and depend on machine load. Complexity claims are theoretical; operation counts follow the named counters or explicitly described loop visits.
