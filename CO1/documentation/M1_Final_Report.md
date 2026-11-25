# Smart Marketplace Search and Real-Time Analytics System
## Module 1 Final Report: Sessions 1–6

## Project introduction

This M.Tech project studies marketplace catalogue search and event storage through algorithm engineering: specify correctness, count meaningful operations, compare representations, measure elapsed time, and explain which computational model each result supports. Python is the primary implementation language and the project uses only the Python standard library.

## Problem statement

Given product records with separate IDs, titles, descriptions, categories, prices, stock counts, and versions, answer exact category/maximum-price/minimum-stock queries. The system also needs a visible baseline, reproducible workloads, collision-safe duplicate candidates, explicit dynamic storage, and reports that separate measured results from theory and simulation.

## Session 1: Computational models and baseline

The CSV loader validates every required header and field, converts price to `float` and stock to `int`, rejects invalid values and duplicate IDs, and includes the row in validation errors. `linear_search` returns all exact category matches meeting the inclusive price and stock limits, plus an explicit record-inspection count. A separate reference comprehension acts as the correctness oracle.

The benchmark creates 20, 100, and 1,000 valid records by deterministic cycling of the 15 starter rows. It uses the same `Electronics`, `max_price=100`, `min_stock=1` query, checks IDs against the oracle, and times only the in-memory scan.

| Products | Inspections | Median time (ms) | Matches | Trials |
|---:|---:|---:|---:|---:|
| 20 | 20 | 0.002100 | 3 | 9 |
| 100 | 100 | 0.008700 | 14 | 9 |
| 1,000 | 1,000 | 0.090000 | 134 | 9 |

The full CSV is [session1_benchmark.csv](session1_benchmark.csv). The RAM count is exactly `N` inspections for a full scan. For a sequential external-memory model with `B=64` records per assumed block, the block simulation reports 1, 2, and 16 transfers. This is not disk-I/O measurement.

## Session 2: Hardware performance bottlenecks

The exact Session 1 query was run over dictionary records and a column representation with packed numeric arrays. Each version inspected every record and returned identical IDs. Thirty-one trials were timed per size.

| Products | Indirect dictionaries (ms) | Contiguous columns (ms) | Correct |
|---:|---:|---:|:---:|
| 20 | 0.002100 | 0.002200 | Yes |
| 100 | 0.009100 | 0.008700 | Yes |
| 1,000 | 0.093400 | 0.121300 | Yes |

Columns use less pointer-heavy numeric storage in principle, but the Python indexed loop was slower at 1,000 rows in this run. The experiment measured elapsed time only. Cache hierarchy, sequential/scattered locality, branch prediction, SIMD, NUMA, and GPU transfer costs are explained in [session2.md](session2/session2.md); none of their hardware counters or GPU/NUMA timings were measured. An optional C++ example was not compiled because `g++` was unavailable.

## Session 3: Amortised event storage

`DynamicEventBuffer` uses a fixed-length backing list and indexed assignments. When full, it allocates double capacity and explicitly copies live elements. For 16 appends from capacity 1, observed capacities were:

`1, 2, 4, 4, 8, 8, 8, 8, 16, 16, 16, 16, 16, 16, 16, 16`

The demonstration made 15 copies and 31 counted writes (15 copies plus 16 appended-event writes). A growth append can cost `Theta(n)` individually, while the geometric copy sum is linear, so amortised cost is `O(1)` per append. Accounting and potential-function proofs are in [session3.md](session3/session3.md); the observed operation log is [operation_log.csv](session3/operation_log.csv).

## Session 4: Expected complexity and fingerprints

SHA-256 fingerprints are configurable in width. The dictionary retrieves only same-fingerprint candidates, then the implementation compares original descriptions exactly. Thus unequal descriptions are never considered duplicates even in a collision bucket. The experiment used 57 records, two exact duplicates, 4-bit fingerprints, and 31 trials.

| Method | Description/exact comparisons | Candidate checks | Collision pairs | Median (ms) | Correct |
|---|---:|---:|---:|---:|:---:|
| Naive pairwise | 1,596 | 0 | 0 | 0.133300 | Yes |
| Fingerprint candidates | 89 | 89 | 87 | 0.231200 | Yes |

The narrow fingerprint reduced exact comparison count but took longer on this small workload because SHA-256 and bucket management have overhead. Matching fingerprints alone do not prove descriptions equal. The collision examples and full comparison CSV are in [session4](session4/session4.md).

## Session 5: Profiling-driven optimization

cProfile/pstats profiled 10,000-row catalogue ingestion and a baseline search. The ingestion function had 0.282803 s cumulative profiled time; `linear_search` had 0.003411 s cumulative profiled time in one query. Profiled time includes instrumentation overhead and is not used for the speed comparison.

One repeated-query optimization was evaluated: a reusable dictionary of category buckets. The search filters the selected bucket rather than every product. The 10,000-row category bucket contained 2,667 candidates.

| Products | Linear median (ms) | Indexed median (ms) | Index build median (ms) | Correct |
|---:|---:|---:|---:|:---:|
| 20 | 0.002300 | 0.001500 | 0.003900 | Yes |
| 100 | 0.009500 | 0.005400 | 0.013700 | Yes |
| 1,000 | 0.095500 | 0.049500 | 0.125600 | Yes |
| 10,000 | 1.022000 | 0.589600 | 1.305600 | Yes |

The query phase was faster after index construction, but the setup cost means one request does not benefit in this measurement. At 10,000 rows, about four repeated requests are needed to repay the measured build cost. The index keeps worst-case query complexity at `O(N)`, while selective category buckets reduce typical candidate work. The same pre-existing 24 correctness tests passed before and after; the later full suite contains 26 passing tests. Profiles, environment, and CSV are in [session5](session5/session5.md).

## Session 6: Final benchmark and model choice

The final run tested 20, 100, 1,000, and 10,000 records against five fixed queries, with 15 trials. Every result matched the oracle. Query times below are for individual requests; index and column preparation are separate.

| Products | Linear ms | Category hash ms | Hash candidate checks | Contiguous ms | Estimated memory: linear / hash / columns (bytes) |
|---:|---:|---:|---:|---:|---:|
| 20 | 0.012800 | 0.007500 | 17 | 0.015300 | 12,417 / 13,608 / 3,271 |
| 100 | 0.047500 | 0.023200 | 81 | 0.064900 | 45,923 / 47,106 / 9,775 |
| 1,000 | 0.458300 | 0.190600 | 801 | 0.539500 | 424,000 / 424,599 / 84,015 |
| 10,000 | 4.712100 | 1.948400 | 8,001 | 5.956400 | 4,210,721 / 4,210,448 / 822,887 |

The five-query individual linear and contiguous workloads performed `5N` predicate checks. The category index examined only records in the requested category buckets. The column layout used the smallest estimated Python object graph but was slower in this Python implementation. A one-pass batch reduced outer collection passes but did not automatically reduce runtime: at 10,000 rows, batched linear was 8.261300 ms versus 4.712100 ms for individual linear requests. Full methods, batched results, preparation time, operation counts, and correctness fields are in [session6_benchmark.csv](session6/session6_benchmark.csv).

![Session 6 median runtime by data size](session6/session6_runtime.svg)

## Computational model selection

| Experiment | Most useful model | What it explains | What was actually measured |
|---|---|---|---|
| Linear scans and candidate counts | RAM | Per-record work and growth in `N` | Explicit inspections and elapsed time |
| Block-read estimate | External-memory | Transfers in assumed blocks of `B` rows | Formula simulation only; no physical I/O |
| Dictionary/column layout | Cache-oblivious reasoning | Why sequential locality may matter without knowing cache size | Python elapsed time only; no cache counters |
| Parallel scan discussion | PRAM | Concurrent shared-memory algorithm possibilities | No PRAM execution |
| Sequential and batch loops | Work-span | Total work and dependency chain | Operation counts; no parallel speedup |

## Final design decisions

1. Keep the exact linear scan as the simplest baseline and independent-oracle target.
2. Reuse the category hash index for repeated queries when the saved candidate checks repay its build and memory cost.
3. Keep full-description equality after fingerprint lookup; fingerprints only select candidates.
4. Keep explicit doubling storage for visible amortised analysis.
5. Retain contiguous columns as a memory-layout teaching example, not the default Python search, because measured loops were slower here.
6. Treat batching as an API and traversal choice, not an assumed performance win.

## Limitations

The larger catalogues repeat the initial 15 products in deterministic order and are not representative of every live marketplace distribution. Results come from one Python 3.14.7 / Windows 11 AMD64 environment on an Intel processor. Timing noise remains despite medians. The Python memory estimate is not process RSS. The block model assumes records per block. No cache-miss, branch-miss, NUMA, GPU, or physical disk metrics were collected. The optional C++ example was not run. The fingerprint collision experiment intentionally uses only 4 bits and does not represent production fingerprint width.

## Conclusion

The project now has a tested baseline, measurable representations, explicit dynamic-array accounting, collision-safe fingerprinting, a profile-guided repeated-query index, and a final multi-method benchmark. The RAM model and operation counters support the strongest conclusions. Hardware-specific explanations remain theory unless a suitable counter or device measurement is added.

## M1 acceptance checklist

- [x] Required product CSV fields validate and errors identify the invalid input.
- [x] Exact linear filtering counts inspections and passes the independent oracle.
- [x] Deterministic benchmarks cover 20, 100, 1,000, and 10,000 products.
- [x] Indirect and column-based searches return identical IDs.
- [x] Dynamic event storage doubles explicitly and logs copies and writes.
- [x] Fingerprint collisions are checked with exact source descriptions.
- [x] cProfile/pstats output, environment details, and an honest before/after comparison are saved.
- [x] Final individual and batch comparisons record timing, operation count, memory estimate, and correctness.
- [x] Reports distinguish actual measurements from theory and simulation.
- [x] Full test suite passes with no third-party dependency installation.
