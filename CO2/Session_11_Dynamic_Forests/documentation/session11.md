# Session 11: Category tree queries and dynamic forests

## Implementation and verification

The implementation is in `src/` and correctness checks are in `tests/test_session11.py`. The benchmark below was generated locally with the standard-library script `benchmarks/benchmark_m2.py`.

## Measured results

Trials per row: 5. Timings are local medians. Memory is a recursive `sys.getsizeof` object-graph estimate, not process RSS.

| Algorithm | Baseline | Input size | Queries | Median ms | Operations | Memory bytes | Correct |
|---|---|---:|---:|---:|---:|---:|:---:|
| Heavy-light decomposition | naive BFS path traversal | 240 | 180 | 3.036100 | 7403 | 119715 | true |
| Link-cut forest | naive BFS path traversal | 240 | 180 | 9.401200 | 7436 | 64968 | true |
| Naive BFS path traversal | simple baseline | 240 | 180 | 7.316800 | 21971 | 91444 | true |

## Measurement notes

- Timer includes static decomposition and queries; operations count chain ranges and Fenwick internal accesses.
- Timer includes linking the initial forest and queries; counts splay rotations and access calls.
- Counts queue nodes visited across each path search; adjacency and values are the same inputs.

Results are from this run and depend on machine load. Complexity claims are theoretical; operation counts follow the named counters or explicitly described loop visits.
