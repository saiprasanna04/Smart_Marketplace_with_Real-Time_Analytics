# Session 4: Expected Complexity and Fingerprints

## How the implementation works

1. `description_fingerprint` encodes the full description as UTF-8 and computes a SHA-256 digest. It masks that digest to a configurable number of low-order bits, returned as a fixed-width hexadecimal string.
2. `FingerprintIndex` uses a Python dictionary from fingerprint to a list of candidate product records.
3. When a record arrives, it computes the key and examines every record in that key's bucket.
4. The original descriptions are compared with exact string equality. Any exact match marks the incoming product as a duplicate. Any unequal description in that bucket is counted as a fingerprint collision.
5. The record is stored in the bucket after checks. Unequal descriptions are never merged or dropped.

The naive baseline compares each incoming description against every prior description. Both approaches return duplicate product IDs and the benchmark checks those IDs agree.

## Hash tables and complexity

A hash table maps a key to a bucket so code can usually find a bucket in expected `O(1)` time. The fingerprint dictionary lookup has expected constant-time access under ordinary hash distribution assumptions. Checking the bucket then costs time proportional to the number of records sharing that fingerprint. If all records land in one bucket, lookup and insertion can take `O(n)` for one item, and scanning all `n` items can take `O(n^2)` comparisons.

Expected complexity is an average over a stated probability model, such as approximately uniform fingerprints or hash values. Worst-case complexity describes the most costly input arrangement. Amortised complexity bounds total cost over a sequence of operations, such as occasional hash-table resizing; it is different from an expected-time claim. This experiment measures one deterministic input and does not establish an expected-case theorem.

Python's built-in `hash()` for strings is randomized between processes, in part to make crafted collision attacks harder. This project uses `hashlib.sha256`, which produces a stable digest for the same text; there is no random seed and no random input. A configurable narrow width is used only to make collisions likely and visible in a small experiment.

If a `b`-bit fingerprint behaves like a uniform random value, a particular unrelated pair collides with probability about `1 / 2^b`. Among `n` descriptions, a birthday-style approximation for at least one pair collision is `1 - exp(-n(n - 1) / (2 * 2^b))`. Real text and truncated digests are not proof of the uniformity assumptions. Exact comparison remains necessary at every width.

## Collision experiment

The deterministic workload contains the 15 starter products, two deliberate exact duplicates, and 40 synthetic descriptions. The experiment narrows SHA-256 to 4 bits (16 possible fingerprints), so unrelated descriptions share buckets. It runs 31 trials and compares the naive pairwise baseline with the fingerprint candidate path. Ten unequal-description collision examples are written to `session4_collision_examples.csv`; comparison counts and timings are in `session4_comparison.csv`.

In the recorded run, both methods returned the same two duplicate product IDs. Pairwise checking made 1,596 description comparisons. Fingerprint lookup checked 89 candidates and made 89 exact comparisons, while encountering 87 unequal-description collision pairs. The pairwise median was 0.133300 ms and the fingerprint path median was 0.231200 ms. The fingerprint path was slower on this small workload because computing a cryptographic digest and maintaining buckets costs more than the small baseline's simple string comparisons. Fewer comparisons do not automatically mean less elapsed time.

These counts and timings describe this generated workload only. The width is deliberately too small for production duplicate detection; the implementation still verifies exact descriptions so collisions cannot create false duplicates.
