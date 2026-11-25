# Session 12: Offline query processing and exact service review

## Implementation and verification

The implementation is in `src/` and correctness checks are in `tests/test_session12.py`. The benchmark below was generated locally with the standard-library script `benchmarks/benchmark_m2.py`.

## Measured results

Trials per row: 5. Timings are local medians. Memory is a recursive `sys.getsizeof` object-graph estimate, not process RSS.

| Algorithm | Baseline | Input size | Queries | Median ms | Operations | Memory bytes | Correct |
|---|---|---:|---:|---:|---:|---:|:---:|
| Mo range-distinct | naive per-range set | 2200 | 220 | 13.607700 | 42765 | 10618 | true |
| Naive range-distinct | simple baseline | 2200 | 220 | 2.533500 | 126856 | 20992 | true |
| Sorted-block square-root sums | naive per-range sum | 2200 | 220 | 1.707600 | 12224 | 22772 | true |
| Naive range sum | simple baseline | 2200 | 220 | 5.364100 | 126856 | 21060 | true |

## Measurement notes

- Counts left/right window movements over the fixed local product-view ID array.
- Counts every view ID visited in each direct slice.
- Counts complete block totals and edge elements read while processing ranges in sorted left-block order.
- Counts every numeric value read from each direct interval.

Results are from this run and depend on machine load. Complexity claims are theoretical; operation counts follow the named counters or explicitly described loop visits.
