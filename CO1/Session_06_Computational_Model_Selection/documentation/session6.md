# Session 6: Choosing a Computational Model

## Final comparison workload

The benchmark reuses the deterministic product expansion from Session 1 and answers the same five queries for every approach: four existing categories with price/stock conditions plus one absent category. It runs 20, 100, 1,000, and 10,000 product records, checks ordered IDs against the independent reference, and uses 15 timing trials per method and size.

The methods are a list-of-dictionaries linear scan, the same scan in one batched outer pass, a reusable category hash index with individual or batched request calls, and contiguous column arrays with individual or batched requests. The index and contiguous conversion are built outside query timing; the CSV also records their one-time preparation times. `operation_count` is record-query predicate evaluations for scans and category-bucket candidate checks for the index. `collection_passes` counts catalogue or bucket traversals.

Memory is an estimate from recursive `sys.getsizeof` over the Python object graph with shared objects counted once. It is not process RSS or a hardware memory-counter result. All result checks passed.

## Results

| Products | Linear individual (ms) | Category hash individual (ms) | Hash candidates | Hash build (ms) | Contiguous individual (ms) | Estimated memory: linear / hash / columns (bytes) |
|---:|---:|---:|---:|---:|---:|---:|
| 20 | 0.012800 | 0.007500 | 17 | 0.020000 | 0.015300 | 12,417 / 13,608 / 3,271 |
| 100 | 0.047500 | 0.023200 | 81 | 0.046300 | 0.064900 | 45,923 / 47,106 / 9,775 |
| 1,000 | 0.458300 | 0.190600 | 801 | 0.150600 | 0.539500 | 424,000 / 424,599 / 84,015 |
| 10,000 | 4.712100 | 1.948400 | 8,001 | 1.596500 | 5.956400 | 4,210,721 / 4,210,448 / 822,887 |

All listed methods returned the same ordered product IDs as the reference. The linear and contiguous scans made `5N` product-query checks. The category index made 17, 81, 801, and 8,001 candidate checks at the four sizes.

At 10,000 products, the category-index query batch took 1.881500 ms after a one-time 1.596500 ms build. The linear individual-request workload took 4.712100 ms. At 20 and 100 products, the measured index build cost was larger than the query-time savings; at 1,000 and 10,000, the build plus one query-batch sample was lower than the repeated linear scans. These are observations from this fixed category mix and environment.

Batching did not make every approach faster. At 10,000 rows, one-pass batched linear scan took 8.261300 ms compared with 4.712100 ms for individual scans; the batched inner query loop adds Python-level work even though it visits the outer catalogue once. Category hash batching was similar to individual calls (1.881500 ms versus 1.948400 ms). Contiguous batching was slower in this Python loop. Fewer outer passes do not guarantee lower elapsed time.

The full output, including each batched result, operation count, preparation time, and correctness field, is `session6_benchmark.csv`. The log-time graph is `session6_runtime.svg`.

## Choosing a computational model

- **RAM model:** Best for this in-memory work. Count product checks, category candidates, exact description comparisons, buffer copies, and writes. Timing supplies a separate machine-specific observation.
- **External-memory model:** Useful when a catalogue no longer fits in RAM or disk reads dominate. Session 1's `ceil(N / B)` row-block count is only a simulation; no physical storage was timed.
- **Cache-oblivious reasoning:** Explains why sequential columns or arrays can have good locality without knowing cache sizes. The Session 2 timings do not reveal cache misses, so locality remains an explanation, not a measured cause.
- **PRAM model:** Useful for reasoning about independent parallel scans on many processors. No PRAM implementation or parallel speedup was measured.
- **Work-span model:** The sequential scan and current batch loops have sequential dependency chains. A batch scans the outer sequence once, but still performs `N * Q` predicates for `Q` queries. Parallel query or chunk execution could reduce span, but would require coordination and is not implemented here.

## Design decisions from these measurements

Keep the linear scan as the simplest baseline and correctness reference. Use a category index when many requests reuse it and category buckets are selective enough to repay index construction. Retain exact description comparison after fingerprint lookup. Keep column storage as a memory-layout experiment: this Python implementation used much less estimated memory but took longer than the dictionary scan at tested sizes. Do not assume batching is faster; select a batch strategy from measured workload results.

## Limitations

The workload is deterministic and repeats the initial 15 records to scale up, so it does not model a production product distribution. Only one Windows/Python environment was measured. `sys.getsizeof` is an approximate object-graph measure and does not report process RSS or cache residency. Timings exclude data generation and index/column preparation, which are reported separately. No physical disk, GPU, NUMA placement, CPU cache counter, or branch predictor counter was measured. PRAM and work-span are conceptual analyses only.
