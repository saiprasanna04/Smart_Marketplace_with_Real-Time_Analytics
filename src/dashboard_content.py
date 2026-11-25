"""Roadmap content based on the project brief and existing M1 reports."""

from __future__ import annotations


PHASE_TITLES = (
    "Algorithm Engineering and Hardware-Aware Analysis",
    "Advanced Data Structures",
    "Probabilistic Data Structures",
    "Vector Search and High-Dimensional Similarity",
    "Streaming and Online Algorithms",
    "Production Search and Retrieval Systems",
)


SESSION_DETAILS: dict[int, dict[str, object]] = {
    1: {
        "title": "Session 1: Computational models and project baseline",
        "description": (
            "Establish an exact sequential search baseline and compare its observed "
            "work with RAM and external-memory reasoning."
        ),
        "objective": (
            "Search the catalogue for products that have stock and cost strictly "
            "less than the supplied price limit, then verify ordered IDs against "
            "an independent oracle."
        ),
        "concepts": [
            "RAM model and basic operation counts",
            "External-memory block-transfer assumptions",
            "Linear scan complexity and why elapsed time is machine-dependent",
            "The repository report also discusses cache-oblivious, PRAM, and work-span models",
        ],
        "tasks": [
            "Load the validated product catalogue and the 20-record hand-trace fixture.",
            "Search in-stock products strictly below the supplied price limit; default to ₹60,000.",
            "Count record inspections, stock checks, price checks, result writes, and total counted operations.",
            "Compare ordered product IDs with the independent reference implementation at 20, 100, and 1,000 records.",
            "Record the RAM and external-memory assumptions used to interpret the measurements.",
        ],
        "acceptance": [
            "The hand-trace fixture contains exactly 20 valid, uniquely identified products.",
            "The deterministic benchmark catalogue contains exactly 1,000 products.",
            "Zero-stock products and products priced at or above the limit are excluded.",
            "The linear search returns the same ordered product IDs as the independent oracle at all three sizes.",
            "Operation counters match the checks performed by the implementation; block reads are labeled as a simulation.",
        ],
        "deliverables": [
            "data/products_hand_trace.csv",
            "data/products_1000.csv and benchmarks/build_session1_data.py",
            "src/session1.py and tests/test_session1.py",
            "Live benchmark results and downloadable CSV from the dashboard",
            "reports/M1/session1.md (existing baseline report)",
        ],
        "status": "completed",
        "source": "Project brief, existing reports/M1/session1.md, and verified Session 1 implementation.",
    },
    2: {
        "title": "Session 2: Hardware performance bottlenecks",
        "description": (
            "Compare the existing dictionary-record scan with a column-based "
            "representation while keeping result IDs and predicates equivalent."
        ),
        "objective": "Investigate how data representation and memory locality relate to observed scan performance.",
        "concepts": [
            "Indirect dictionary access and contiguous columns",
            "Sequential locality and cache behavior as a reasoning model",
            "Elapsed time versus hardware-counter measurements",
        ],
        "tasks": [
            "Run the same category, price, and stock filter on dictionary and column representations.",
            "Check returned product IDs before accepting timing rows.",
            "Record timing results and explain which hardware effects were not measured.",
        ],
        "acceptance": [
            "Both existing search representations return the same ordered product IDs.",
            "Both scans inspect every product in the tested catalogue.",
            "Reports distinguish elapsed-time measurements from cache or hardware-counter claims.",
        ],
        "deliverables": [
            "src/hardware_analysis.py",
            "benchmarks/benchmark_session2.py",
            "reports/M1/session2/session2_benchmark.csv",
            "reports/M1/session2/session2.md",
        ],
        "status": "completed",
        "source": "Existing Session 2 implementation, tests, and M1 report.",
    },
    3: {
        "title": "Session 3: Amortised analysis of growing event storage",
        "description": "Make dynamic-array capacity growth, copies, and writes observable.",
        "objective": "Explain the cost of individual growth appends and the total work over a sequence of appends.",
        "concepts": [
            "Geometric capacity doubling",
            "Worst-case versus amortised cost",
            "Accounting and potential-function arguments",
        ],
        "tasks": [
            "Append the reproducible event sequence to the explicit dynamic buffer.",
            "Record capacity, copies, and writes for every append.",
            "Relate observed counts to the amortised analysis in the existing report.",
        ],
        "acceptance": [
            "Growth preserves all appended events.",
            "Capacity doubles when full and the operation log records copies and writes.",
            "Tests verify the recorded capacity and aggregate counts.",
        ],
        "deliverables": [
            "src/dynamic_buffer.py",
            "benchmarks/demo_session3.py",
            "reports/M1/session3/operation_log.csv",
            "reports/M1/session3/session3.md",
        ],
        "status": "completed",
        "source": "Existing Session 3 implementation, tests, and M1 report.",
    },
    4: {
        "title": "Session 4: Expected complexity and fingerprints",
        "description": "Use fingerprint buckets to find candidates and retain exact description checks.",
        "objective": "Compare pairwise duplicate checks with collision-safe fingerprint candidate lookup.",
        "concepts": [
            "Expected and worst-case complexity",
            "SHA-256 fingerprints and configurable width",
            "Collision handling through exact source-text comparison",
        ],
        "tasks": [
            "Compare the existing pairwise and fingerprint-assisted duplicate methods.",
            "Exercise narrow fingerprints that produce unequal-description collisions.",
            "Record candidate checks, exact comparisons, collisions, timings, and correctness.",
        ],
        "acceptance": [
            "Both methods return the same duplicate product IDs.",
            "An unequal-description fingerprint collision is not reported as a duplicate.",
            "Exact source descriptions are compared for candidates.",
        ],
        "deliverables": [
            "src/fingerprint.py",
            "benchmarks/benchmark_session4.py",
            "reports/M1/session4/session4_comparison.csv",
            "reports/M1/session4/session4_collision_examples.csv",
            "reports/M1/session4/session4.md",
        ],
        "status": "completed",
        "source": "Existing Session 4 implementation, tests, and M1 report.",
    },
    5: {
        "title": "Session 5: Profiling-driven optimisation",
        "description": "Profile ingestion and search, then assess a reusable category index for repeated queries.",
        "objective": "Use profile evidence to choose and measure one repeated-query optimization.",
        "concepts": [
            "cProfile and pstats output",
            "Category-index construction and candidate filtering",
            "Preparation cost, query cost, and workload reuse",
        ],
        "tasks": [
            "Profile catalogue ingestion and the baseline search on the existing workload.",
            "Compare a reusable category index with the linear baseline.",
            "Check IDs against the reference and report index-build cost separately.",
        ],
        "acceptance": [
            "The indexed and baseline methods return the same results.",
            "Profiles and before/after timings are stored as report artifacts.",
            "The report describes the measured workload and index setup cost.",
        ],
        "deliverables": [
            "src/profiler.py and src/search.py",
            "benchmarks/profile_session5.py",
            "reports/M1/session5/session5_profile_stats.csv",
            "reports/M1/session5/before_after_benchmark.csv",
            "reports/M1/session5/session5.md",
        ],
        "status": "completed",
        "source": "Existing Session 5 implementation, tests, and M1 report.",
    },
    6: {
        "title": "Session 6: Choosing a computational model",
        "description": "Compare the existing scan, index, batch, and contiguous approaches against one workload.",
        "objective": "Use operation counts, timing, memory estimates, and preparation costs to discuss model choice.",
        "concepts": [
            "RAM and external-memory cost reasoning",
            "Cache-oblivious locality reasoning",
            "PRAM and work-span concepts",
            "Measured timing and memory-estimate limitations",
        ],
        "tasks": [
            "Run the existing five-query workload across the documented catalogue sizes.",
            "Compare individual and batched scans, category indexing, and contiguous columns.",
            "Check results against the reference and report preparation, operation, and memory values.",
        ],
        "acceptance": [
            "Every compared method returns the expected ordered product IDs.",
            "The benchmark records timing, operation counts, collection passes, preparation time, and memory estimate.",
            "The report identifies theoretical models and simulations separately from measured values.",
        ],
        "deliverables": [
            "benchmarks/benchmark_session6.py",
            "reports/M1/session6/session6_benchmark.csv",
            "reports/M1/session6/session6_runtime.svg",
            "reports/M1/session6/session6.md",
            "reports/M1/M1_Final_Report.md",
        ],
        "status": "completed",
        "source": "Existing Session 6 implementation, tests, and M1 report.",
    },
    7: {
        "title": "Session 7: Range queries and lazy updates",
        "description": "Answer historical sales ranges while sales arrive and apply stock adjustments over indexed ranges.",
        "objective": "Compare point-update/prefix-query and range-update/range-query structures against naive arrays.",
        "problem": "An analyst requests total sales between days 3 and 9. A manager applies a stock adjustment to a range of catalogue positions.",
        "why": "Repeatedly scanning daily sales or every stock value repeats work; tree summaries update and answer ranges in logarithmic time.",
        "implementation": "FenwickTree implements point updates and prefix/range sums. LazySegmentTree implements range-add and range-sum with deferred child updates.",
        "concepts": ["Fenwick tree bit decomposition", "Prefix-sum subtraction", "Segment-tree intervals", "Lazy propagation", "Half-open range conventions"],
        "tasks": ["Aggregate simulated purchase events by day.", "Query days 3–9 and compare to a direct sum.", "Apply a stock delta to a catalogue interval and compare to a naive array.", "Record tree-node operations and elapsed time against direct scans."],
        "acceptance": ["Point updates and prefix/range sums match a naive array.", "Range additions and overlapping range sums match a naive array.", "Single, full, empty, and boundary ranges are checked.", "Randomized operations match the oracle."],
        "deliverables": ["src/range_queries.py", "tests/test_session7.py", "benchmarks/benchmark_m2.py", "reports/M2/session7.md"],
        "module": "Module 2: Advanced Data Structures",
        "complexity": "Fenwick operations O(log N); lazy segment-tree range updates and queries O(log N); each structure uses O(N) storage.",
        "test_files": ["tests/test_session7.py"],
        "source": "User-provided Session 7 requirements; official curriculum PDF was not present in the attachments.",
    },
    8: {
        "title": "Session 8: Persistent catalogue snapshots",
        "description": "Reproduce earlier catalogue state after inventory changes by retaining immutable versions.",
        "objective": "Compare copy-on-write snapshots, fat-node histories, and AVL path-copying persistence across V0, V1, and V2.",
        "problem": "After inventory updates, an analyst must query the earlier catalogue snapshot without seeing later stock values.",
        "why": "Immutable snapshots make historical reports reproducible and give cache entries a stable catalogue version identifier.",
        "implementation": "PersistentCatalogue is an immutable AVL tree that path-copies updated nodes. FatNodeMap keeps versioned per-key histories; the demo also compares full map copies.",
        "concepts": ["Copy-on-write", "Fat-node modification histories", "Path copying", "Structural sharing", "Version-aware cache keys"],
        "tasks": ["Create versions V0, V1, and V2 from product records.", "Update stock in V1 and V2, then re-query V0.", "Trace a fat-node lookup and compare snapshot memory estimates."],
        "acceptance": ["V0 remains unchanged after both updates.", "V1 and V2 expose their own inventory values.", "Path-copying and copy-on-write memory are compared.", "Catalogue version IDs are part of the data contract and cache keys."],
        "deliverables": ["src/persistent_catalogue.py", "tests/test_session8.py", "benchmarks/benchmark_m2.py", "reports/M2/session8.md"],
        "module": "Module 2: Advanced Data Structures",
        "complexity": "AVL lookup and path-copy update O(log N); each update allocates O(log N) tree nodes. A full copied snapshot uses O(N) entries.",
        "test_files": ["tests/test_session8.py"],
        "source": "User-provided Session 8 requirements; official curriculum PDF was not present in the attachments.",
    },
    9: {
        "title": "Session 9: Suffix arrays and longest common prefixes",
        "description": "Find exact phrases and repeated substrings in product descriptions without scanning each description for every query.",
        "objective": "Build suffix and LCP arrays, map positions to products, and reject matches that cross document separators.",
        "problem": "Catalogue managers need to locate exact substrings and repeated phrases across descriptions.",
        "why": "A suffix index reuses one preprocessing pass for many exact substring queries and LCP inspection.",
        "implementation": "The measured constructor uses prefix doubling and Kasai LCP. A separate, labelled DC3 trace explains its sample/rank/merge stages; it is not an executed DC3 implementation.",
        "concepts": ["Suffix ordering", "Prefix doubling", "Kasai LCP", "Generalized text indexes", "Unique document sentinels", "DC3/skew construction"],
        "tasks": ["Index real product descriptions with unique separators.", "Search exact phrases and compare offsets with direct scanning.", "Check absent queries and cross-document boundaries.", "Inspect the guided DC3 trace."],
        "acceptance": ["Known suffix-array and LCP examples match expected values.", "Substring search matches direct scanning.", "Absent substrings return no matches.", "Unique separators prevent cross-document matches."],
        "deliverables": ["src/suffix_index.py", "tests/test_session9.py", "benchmarks/benchmark_m2.py", "reports/M2/session9.md"],
        "module": "Module 2: Advanced Data Structures",
        "complexity": "Prefix-doubling construction O(N log² N) with Python comparison sorting; LCP O(N); query O(|P| log N + matches).",
        "test_files": ["tests/test_session9.py"],
        "source": "User-provided Session 9 requirements; official curriculum PDF was not present in the attachments.",
    },
    10: {
        "title": "Session 10: Suffix automata for description text",
        "description": "Use per-product suffix automata to test exact substring membership and count occurrences.",
        "objective": "Trace states, transitions, suffix links, and clones, then compare description queries with Session 9.",
        "problem": "A manager needs reusable exact substring queries over many product descriptions.",
        "why": "A suffix automaton stores the substrings of a text in a compact state graph and answers membership by following transitions.",
        "implementation": "SuffixAutomaton builds transitions and suffix links, creates clones when needed, and propagates occurrence counts. Each product has an independent automaton, so document boundaries cannot be crossed.",
        "concepts": ["End-position equivalence classes", "Transitions", "Suffix links", "Clone states", "Occurrence propagation"],
        "tasks": ["Build one automaton per product description.", "Trace clone creation on a repeated short string.", "Compare query presence and occurrence counts with Session 9 and direct scans."],
        "acceptance": ["Substring membership matches direct scanning.", "A clone is traced with redirected transitions.", "Multi-document results match the suffix-array index.", "Each document is mapped explicitly."],
        "deliverables": ["src/suffix_automaton.py", "tests/test_session10.py", "benchmarks/benchmark_m2.py", "reports/M2/session10.md"],
        "module": "Module 2: Advanced Data Structures",
        "complexity": "O(N) expected construction and O(|P|) query for constant-time dictionary transitions; O(N) states/transitions up to constant factors.",
        "test_files": ["tests/test_session10.py"],
        "source": "User-provided Session 10 requirements; official curriculum PDF was not present in the attachments.",
    },
    11: {
        "title": "Session 11: Category tree queries and dynamic forests",
        "description": "Aggregate sales along the category hierarchy and model legal category moves.",
        "objective": "Compare static heavy-light path queries with dynamic link-cut operations against naive paths.",
        "problem": "An analyst needs category path totals, while a manager may move a category under a valid new parent.",
        "why": "Static trees support fast path aggregation after decomposition; dynamic forests support link and cut without rebuilding every query structure.",
        "implementation": "HeavyLightDecomposition linearizes a static forest for path sums. LinkCutForest uses splay-based preferred paths for links, cuts, connectivity, and path sums; cycle-producing links are rejected.",
        "concepts": ["Heavy-light decomposition", "Path aggregates", "Splay trees", "Preferred paths", "Link-cut trees", "Static topology rebuilds"],
        "tasks": ["Build a category hierarchy from catalogue categories and purchase revenue.", "Compare HLD and link-cut path sums with a naive traversal.", "Trace legal links/cuts and reject a cycle-producing move."],
        "acceptance": ["HLD path sums match naive traversal.", "Link-cut path sums match the static result.", "Legal links and cuts work.", "Cycle-producing category moves are rejected and static rebuild implications are explained."],
        "deliverables": ["src/category_forest.py", "tests/test_session11.py", "benchmarks/benchmark_m2.py", "reports/M2/session11.md"],
        "module": "Module 2: Advanced Data Structures",
        "complexity": "HLD path query O(log² N) with Fenwick-backed chain ranges; link-cut operations O(log N) amortized.",
        "test_files": ["tests/test_session11.py"],
        "source": "User-provided Session 11 requirements; official curriculum PDF was not present in the attachments.",
    },
    12: {
        "title": "Session 12: Offline query processing and exact service review",
        "description": "Answer many historical range-distinct queries over the fixed view-event array while measuring window movement.",
        "objective": "Implement Mo ordering and square-root range sums, then compare all answers with naive loops.",
        "problem": "Independent historical range-distinct queries revisit the same view-event positions many times.",
        "why": "Offline ordering reuses a moving window, while block decomposition summarizes static intervals for range queries.",
        "implementation": "mo_range_distinct sorts half-open ranges by left block and alternating right endpoints. SqrtRangeSum and sorted_block_range_sums support static range sums.",
        "concepts": ["Offline query batches", "Mo's algorithm", "Square-root decomposition", "Block ordering", "Window movement counts"],
        "tasks": ["Load the fixed anonymous view-event array.", "Count distinct product IDs for overlapping and boundary intervals.", "Record pointer movements and compare against naive answers.", "Review how exact search, range, version, string, and category services connect."],
        "acceptance": ["Mo answers match naive distinct counts.", "Boundary and empty intervals are tested.", "Pointer movement counts are recorded.", "Sorted-block range sums match a direct baseline."],
        "deliverables": ["src/offline_analytics.py", "tests/test_session12.py", "data/events.csv", "benchmarks/benchmark_m2.py", "reports/M2/M2_Final_Report.md"],
        "module": "Module 2: Advanced Data Structures",
        "complexity": "Mo pointer work O((N + Q) sqrt(N)) in standard analysis; static square-root range sums O(sqrt N) query time.",
        "test_files": ["tests/test_session12.py"],
        "source": "User-provided Session 12 requirements; official curriculum PDF was not present in the attachments.",
    },
}


def build_roadmap(completion_checks: dict[int, bool] | None = None) -> list[dict[str, object]]:
    """Return the roadmap; only sessions with passing live checks are completed."""
    phases: list[dict[str, object]] = []
    for phase_number, title in enumerate(PHASE_TITLES, start=1):
        start = (phase_number - 1) * 6 + 1
        end = start + 5
        phase_sessions = []
        prior_phase2_checks_pass = True
        for session_number in range(start, end + 1):
            if session_number in SESSION_DETAILS:
                session = {"number": session_number, **SESSION_DETAILS[session_number]}
                if 7 <= session_number <= 12:
                    passed = bool(completion_checks and completion_checks.get(session_number))
                    session["status"] = (
                        "completed" if passed else "active" if prior_phase2_checks_pass else "upcoming"
                    )
                    prior_phase2_checks_pass = prior_phase2_checks_pass and passed
                session.setdefault("module", PHASE_TITLES[phase_number - 1])
                session.setdefault("problem", session["objective"])
                session.setdefault("why", session["description"])
                session.setdefault("implementation", "See the linked source and deliverables for the implemented method.")
                session.setdefault("complexity", "See the linked session report for analysis.")
                session.setdefault("test_files", [f"tests/test_session{session_number}.py"])
            else:
                session = {
                    "number": session_number,
                    "title": f"Session {session_number}: Curriculum details pending",
                    "description": "Awaiting the authoritative curriculum for this session.",
                    "objective": "Pending authoritative curriculum.",
                    "concepts": ["Pending authoritative curriculum."],
                    "tasks": ["Pending authoritative curriculum."],
                    "acceptance": ["Pending authoritative curriculum."],
                    "deliverables": ["Pending authoritative curriculum."],
                    "status": "upcoming",
                    "source": "Curriculum attachment not present in the workspace yet.",
                }
            phase_sessions.append(session)

        phase_status = "upcoming"
        if phase_number == 1:
            phase_status = "completed"
        elif phase_number == 2:
            phase_status = (
                "completed"
                if completion_checks and all(completion_checks.get(number, False) for number in range(7, 13))
                else "active"
            )
        phases.append(
            {
                "number": phase_number,
                "title": title,
                "session_start": start,
                "session_end": end,
                "status": phase_status,
                "sessions": phase_sessions,
            }
        )
    return phases
