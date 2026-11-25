# Session 2: Hardware Performance Bottlenecks

## Experiment

This experiment uses the shared deterministic workload from Session 1 and the same filter: category `Electronics`, maximum price `100.0`, and minimum stock `1`. Each dataset is scanned as a list of product dictionaries (indirect field access) and as a column-based representation (packed numeric arrays plus ID/category columns). The filtering conditions and returned product IDs are checked for equality before timings are accepted.

The script measures the in-memory searches over 20, 100, and 1,000 records, repeats each search 31 times by default, and records the median. Catalogue generation and conversion to columns happen outside the timed search. The Python timing is an actual elapsed-time measurement from the current environment; it is not a cache counter.

Results are in `session2_benchmark.csv`.

### Results from this run

The run used 31 trials for each representation and size. All six comparisons returned the same IDs and inspected every record.

| Size | Representation | Median time (ms) | Matches | Inspected | Correct |
|---:|---|---:|---:|---:|:---:|
| 20 | Indirect dictionaries | 0.002100 | 3 | 20 | Yes |
| 20 | Column arrays | 0.002200 | 3 | 20 | Yes |
| 100 | Indirect dictionaries | 0.009100 | 14 | 100 | Yes |
| 100 | Column arrays | 0.008700 | 14 | 100 | Yes |
| 1,000 | Indirect dictionaries | 0.093400 | 134 | 1,000 | Yes |
| 1,000 | Column arrays | 0.121300 | 134 | 1,000 | Yes |

For this run, column storage was close at 20 and 100 rows and slower at 1,000. Both approaches still do the same number of row checks. This is an observation from one Python/environment setup, not evidence that one layout is universally faster.

## Hardware concepts

### CPU cache hierarchy and locality

CPUs commonly use small, fast L1 caches, larger L2 caches, and a still larger shared or per-core L3 cache before reaching main memory. Exact sizes and sharing differ by processor. A cache line transfers a neighborhood of memory together, so reading nearby data can make later nearby reads faster.

Sequential access walks addresses in order and usually has good spatial locality. Scattered access jumps among addresses and may use fewer bytes from each fetched cache line. A list of dictionaries adds pointer/reference traversals to find each field. The column representation makes price and stock values compact and sequential, though its Python string columns still contain references. Python object allocation and interpreter behavior also affect the measured timings.

### Branch prediction

The CPU predicts the direction of conditional branches so it can keep executing while the condition is resolved. A branch-heavy filter has several conditional checks. If their outcomes are hard to predict, wrong predictions can waste work. A branch-light or predictable filter has fewer decisions or outcomes that follow a regular pattern. The search benchmark measures elapsed runtime only; it does **not** measure branch misses. Its Python `if` statements do not tell us whether the CPU predictor guessed correctly.

### SIMD

SIMD (Single Instruction, Multiple Data) applies one operation to several values in parallel, such as checking many packed prices against one threshold. It is most useful for regular numeric data and sufficiently large batches. Python's ordinary loop over `array` values does not automatically promise SIMD execution. A compiled loop or a vectorized numeric library may use SIMD, but that is a different implementation and was not measured here.

### NUMA locality

On a Non-Uniform Memory Access (NUMA) machine, memory attached to the current processor socket can be faster to access than memory attached to another socket. Thread placement and where memory was allocated can affect performance. This single-process Python timing did not control thread affinity or allocate data across NUMA nodes, and no NUMA effects were measured.

### GPU memory hierarchy and transfers

GPUs have registers, shared/on-chip memory, and device global memory. Moving product data from host RAM to device memory costs time, as do launching a kernel and copying results back. GPU processing can help when a large enough workload amortizes these costs and the filtering can be expressed in parallel. This project did not use a GPU; no GPU performance is claimed.

## Measurement boundaries

Measured: median Python elapsed time for the two searches, record count, and matching IDs. The data-layout descriptions explain what the program stores. The report's cache, branch, SIMD, NUMA, and GPU discussion is hardware theory, not a set of measured counters. No cache misses, branch misses, NUMA effects, disk traffic, or GPU transfers were collected.

An optional C++ illustration is in `../../../benchmarks/session2_cache_example.cpp`. It has a fixed random seed and compares sequential and shuffled reads. It was not compiled here because `g++` is not available on PATH. On Linux with a compiler and `perf`, a user can try:

```bash
g++ -O2 -std=c++17 benchmarks/session2_cache_example.cpp -o cache_example
perf stat -e cache-references,cache-misses,branches,branch-misses ./cache_example
```

Counter names and access permissions depend on the platform. The C++ example is optional; Python remains the project's primary implementation.
