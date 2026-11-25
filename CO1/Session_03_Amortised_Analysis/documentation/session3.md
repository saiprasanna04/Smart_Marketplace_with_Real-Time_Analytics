# Session 3: Amortised Analysis of Growing Event Storage

## Explicit buffer implementation

`DynamicEventBuffer` owns a preallocated backing array (a Python list of fixed length). Appending writes into an existing slot. When the array is full, the class allocates a new array with twice the capacity and copies each live event using an indexed assignment. It never calls `append` on its backing storage, so Python's internal list-resizing strategy is not part of the experiment.

### Code walkthrough

- `__init__` validates that capacity is positive, allocates that many empty slots, and initializes size, copy, and write counters to zero.
- `size` and `capacity` properties expose the live event count and allocated slot count without allowing callers to change them.
- `append` first sets this operation's copy count to zero. If `size == capacity`, it saves the old backing array, allocates one with twice as many slots, and loops only over live indices to copy each event. Each indexed copy increments the per-append count.
- After any needed resize, `append` writes the new event at index `size`, then increments size. Its counted writes equal copies plus this one new event write.
- The cumulative counters are updated and a snapshot row is stored in `operation_log`. Returning a copy of that row prevents the caller from editing the internal log entry.
- `to_list` returns a new list containing only live slots, not unused capacity. `__len__` and `__iter__` let beginner code inspect the buffer using familiar Python operations.
- `demo_session3.py` adds 16 numbered events, writes each log row through `csv.DictWriter`, and prints the capacity/copy sequence so it can be checked against the CSV.

For each user append, the log records the event count, capacity, copies made in that append, total copies, writes made in that append, and cumulative writes. A write means a copied event reference or the newly appended event reference; the initialization of a new array to `None` and metadata updates are excluded. This operation-count convention is explicit and consistent across rows.

Run `python benchmarks/demo_session3.py` to regenerate `operation_log.csv`. The demonstration starts at capacity 1 and appends 16 events. The observed capacity progression is 1, 2, 4, 4, 8, 8, 8, 8, then 16 for appends 9 through 16. It performs 15 copies and 31 counted writes in total.

## Why total copying is linear

An append that does not fill the array copies nothing. A growth append copies all current elements, so an individual growth can be expensive. Across 16 appends, the copied counts are 1, 2, 4, and 8: 15 copies total. In general, when capacity doubles, the copying costs form a geometric series below `n + n/2 + n/4 + ... < 2n`. Thus `n` appends copy fewer than `2n` existing items, making total copies `O(n)` and amortised copy work `O(1)` per append.

### Accounting method

Charge each append 3 credits: one pays for its own new-slot write and two are saved. When an expansion copies an old event, one saved credit pays for that copy. Before a full capacity-`C` array grows, earlier appends have accumulated enough saved credits to pay for copying its `C` live elements. Therefore the charged cost is at most 3 per append, even though one append's immediate actual cost can be `C + 1` writes.

### Potential method

Let `n` be the current size and `C` the current capacity. Define the nonnegative potential:

`Phi(n, C) = max(0, 2n - C)`.

The amortised cost is actual cost plus the change in potential.

- **No growth:** actual cost is 1 new-slot write. Potential rises by at most 2, so amortised cost is at most 3.
- **Growth:** before the append `n = C`, actual cost is `C` copies plus 1 new-slot write (`C + 1`). The new state is `(C + 1, 2C)`, with potential 2; the old potential is `C`. Amortised cost is `(C + 1) + 2 - C = 3`.

The initial potential is nonnegative, so summing amortised costs bounds total actual work by `3n` for `n` appends.

## Three different cost statements

- **Worst-case individual append:** `Theta(n)` when a full array of `n` items is copied during growth.
- **Amortised append cost:** `O(1)` over any sequence of appends; this is a sequence guarantee, not a claim that every append is cheap.
- **Average-case cost:** an expected cost under a specified probability distribution over inputs or operations. The buffer is deterministic and this experiment specifies no such random distribution, so its observed average over 16 appends (31 writes / 16) is descriptive only, not an average-case theorem.
