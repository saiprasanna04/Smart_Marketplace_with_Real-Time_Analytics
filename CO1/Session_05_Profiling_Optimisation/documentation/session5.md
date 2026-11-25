# Session 5: Profiling-Driven Optimisation

## What was profiled

`benchmarks/profile_session5.py` uses `cProfile` and `pstats` on two separate workloads:

1. Catalogue ingestion from a generated 10,000-row CSV file.
2. The baseline `linear_search` over the same 10,000 product records using the Session 1 query (`Electronics`, price at most 100, stock at least 1).

The generated CSV is temporary. The raw profile files, readable pstats output, and function summary CSV are saved in this directory. cProfile adds overhead, so its times are used to locate work, not to compare optimization speed. The before/after speed comparison uses unprofiled `perf_counter_ns` timing and medians over 31 trials.

## Profile output and how to read it

| Workload | Function | Calls | Total time (s) | Cumulative time (s) |
|---|---|---:|---:|---:|
| Ingestion, 10,000 rows | `load_catalogue` | 1 | 0.128765 | 0.282803 |
| Ingestion, 10,000 rows | `csv.__next__` | 10,001 | 0.032138 | 0.078175 |
| Ingestion, 10,000 rows | dictionary `get` | 80,000 | 0.018070 | 0.018070 |
| Baseline search, 10,000 rows | `linear_search` | 1 | 0.003035 | 0.003411 |
| Baseline search, 10,000 rows | list `append` | 1,334 | 0.000376 | 0.000376 |

In the pstats output, **calls** is how many times a function ran. **Total time** (also called `tottime`) is time in that function's own body, excluding called functions. **Cumulative time** (`cumtime`) includes its callees. The CSV additionally stores the source location and primitive call count. `load_catalogue` has one profile call but a much larger cumulative time because reading and validating 10,000 records is substantial. `linear_search` is the main cost within one search request.

The CSV and readable pstats text include more functions than this summary table. The `.prof` files can be reopened with `pstats.Stats` for additional sorting or filtering.

## One selected optimisation: reusable category buckets

The selected query bottleneck is the full record scan for repeated catalogue requests. `CategoryIndex` builds a dictionary from exact category names to lists of product records. Each query then checks only the records in the requested category bucket before applying the same price and stock filters. Index construction is measured separately and excluded from per-query timing; the intended use is to reuse the index across requests.

The profile showed `linear_search` performs work proportional to all 10,000 products for every request. The category index narrows the query's candidate set to 2,667 records in this deterministic workload. The index has `O(N)` build time and space. A query takes expected `O(1)` to retrieve a bucket plus `O(M)` filtering for `M` records in that category; worst case remains `O(N)` when a category contains all products.

## Before and after measurements

Both versions used the same generated product records and the same exact query. The benchmark ran 31 trials at each size, checked the result IDs against the independent reference, and reports the median search time. Index construction is shown separately.

| Size | Method | Median query time (ms) | Index build median (ms) | Records considered | Correct |
|---:|---|---:|---:|---:|:---:|
| 20 | Linear baseline | 0.002300 | 0 | 20 | Yes |
| 20 | Category hash index | 0.001500 | 0.003900 | 6 | Yes |
| 100 | Linear baseline | 0.009500 | 0 | 100 | Yes |
| 100 | Category hash index | 0.005400 | 0.013700 | 27 | Yes |
| 1,000 | Linear baseline | 0.095500 | 0 | 1,000 | Yes |
| 1,000 | Category hash index | 0.049500 | 0.125600 | 267 | Yes |
| 10,000 | Linear baseline | 1.022000 | 0 | 10,000 | Yes |
| 10,000 | Category hash index | 0.589600 | 1.305600 | 2,667 | Yes |

For 10,000 products, the measured query was about 1.7 times faster after the index was built. The median index-build time was about 1.31 ms, so a single query does not repay that setup cost in this run. Under these observed timings, about four such queries are needed to repay the build cost. This break-even estimate is environment- and workload-specific. No improvement is claimed for a one-off request.

## Test runs before and after

Before the category-index optimization, the existing suite had 24 passing tests. After the optimization, the same pre-existing tests passed again; the final suite had 26 passing tests, including two additional Session 6 batch/index checks. The Session 5 benchmark also compared result IDs with the oracle at all four sizes.

## Terms and limitations

- **Algorithmic complexity** describes how work grows. The index preprocesses in `O(N)` and narrows common selective queries, while its worst-case query remains `O(N)`.
- **Constant-factor optimisation** reduces work or overhead without changing worst-case asymptotic growth. The actual gain depends on the category distribution and reuse count.
- **Profiling** attributes runtime to functions and call paths; cProfile's instrumentation perturbs timings.
- **Benchmarking** runs controlled workloads repeatedly and compares unprofiled measurements.
- **Measurement noise** comes from scheduling, caches, interpreter state, and other activity. Medians reduce some outlier effects but do not eliminate noise.

Hardware/software details are in `environment.txt`. No hardware counters, cache misses, branch misses, or storage-device metrics were collected.
