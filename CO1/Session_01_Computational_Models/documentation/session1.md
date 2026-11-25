# Session 1: Computational Models and Project Baseline

## Baseline search

The catalogue loader reads `data/products.csv` and checks all required fields: `product_id`, `title`, `description`, `category`, `price`, `stock`, and `version`. It reports the file and row for missing or invalid values. Prices must be finite, nonnegative numbers; stock must be a nonnegative integer; product IDs must be unique.

`linear_search` compares each record's category, price, and stock with the query. Category equality is exact. The maximum price and minimum stock boundaries are inclusive. It returns both the matching product records and the number of records inspected. Because this search returns every match, it scans the full catalogue, including when there are no matches.

The reference implementation in `src/search.py` uses a separate list-comprehension implementation. The CLI and benchmark compare ordered product ID lists from both implementations to catch correctness errors.

For a catalogue of `N` records, the baseline performs `N` record inspections and has `O(N)` time complexity. Its result list uses `O(K)` additional space for `K` matches.

## Computational models

### RAM model and basic operation counting

The Random Access Machine (RAM) model treats simple operations on values in memory as taking constant time. For this scan, a useful basic operation is inspecting one product record and checking its fields. We count that directly in `records_inspected`; we do not estimate it from elapsed time. A full scan of `N` products therefore records exactly `N` inspections.

The RAM model is useful for reasoning about growth as input size changes. It abstracts away CPU details, Python interpreter overhead, caches, and storage devices.

### External-memory model and block transfers

The external-memory model distinguishes fast memory from slower storage. If a sequential block can hold `B` product records, a scan over `N` consecutively stored records touches approximately `ceil(N / B)` blocks. The benchmark includes `simulate_block_reads(N, B)` and lets `--block-size` configure `B` (default 64 records).

This is a simple **simulation of block transfers**, based on an assumed number of records per block. It does not read from or measure a physical disk, filesystem, or operating-system cache. Real CSV byte sizes and storage behavior are not modeled.

### Cache-oblivious model and memory locality

A cache-oblivious algorithm is designed without knowing the cache size or block size. A linear scan has good sequential locality: it visits adjacent records in order, which can make effective use of cache lines and read-ahead. The implementation does not tune itself to a particular cache, and Python object layout can still affect actual locality.

### PRAM model

The Parallel Random Access Machine (PRAM) model imagines multiple processors accessing shared memory in synchronized steps. PRAM variants differ in whether simultaneous reads or writes to one location are allowed. It is useful for studying parallel algorithms, but Session 1's search is sequential and does not use PRAM processors.

### Work-span model

The work-span model describes a parallel algorithm with total work `W` (all operations combined) and span `S` (the longest dependency chain). With `P` processors, execution time is bounded below by at least `max(W / P, S)`. The current linear scan has `W = O(N)` and `S = O(N)` because records are checked one after another. Splitting a scan into independent chunks could reduce span, but would add coordination and result-combination work; that is outside this baseline.

## Why equal Big-O does not mean equal runtime

Big-O describes how work grows with input size while ignoring constant factors and many machine details. Two `O(N)` implementations can differ in Python-level function calls, condition order, object allocation, data representation, branch behavior, cache locality, interpreter version, processor, background load, and whether data is already in memory. An algorithm that reads a file also includes storage and parsing costs that a search-only timing excludes.

The benchmark times only the in-memory linear search, runs multiple trials, and records the median to reduce the influence of occasional timing noise. Its elapsed time is an observation from the current environment; record inspections are the separate operation-count measure.

## Reproducible benchmark method

The starter CSV contains 15 valid records. The benchmark grows it to 20, 100, and 1,000 records by cycling through those records in order, preserving all fields, and assigning a unique ID and title suffix to each generated record. No randomness is used, so the generated catalogues are deterministic.

Each trial searches the `Electronics` category with `max_price = 100.0` and `min_stock = 1`. The reference result is checked on every trial. The CSV output records product count, records inspected, median time, match count, trial count, block size, and simulated block reads.

Benchmark output is saved in `reports/M1/session1_benchmark.csv`.

### Results from this run

This run used 9 trials per size and a simulated block size of 64 records. Search timing covers only the in-memory scan and will vary by machine and system load.

| Products | Records inspected | Median time (ms) | Matches | Simulated block reads |
|---:|---:|---:|---:|---:|
| 20 | 20 | 0.002100 | 3 | 1 |
| 100 | 100 | 0.008700 | 14 | 2 |
| 1,000 | 1,000 | 0.090000 | 134 | 16 |
