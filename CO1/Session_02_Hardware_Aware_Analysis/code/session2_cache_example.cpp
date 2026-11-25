// Optional illustration only: this program was not compiled or measured here.
// On Linux, one may compile it and use `perf stat` to inspect available counters.
#include <chrono>
#include <algorithm>
#include <cstddef>
#include <iostream>
#include <numeric>
#include <random>
#include <vector>

int main() {
    constexpr std::size_t count = 1'000'000;
    std::vector<double> values(count, 1.0);
    std::vector<std::size_t> order(count);
    std::iota(order.begin(), order.end(), 0);
    std::mt19937 generator(2026);  // Fixed seed makes the access order repeatable.
    std::shuffle(order.begin(), order.end(), generator);

    volatile double sum = 0.0;  // Keep the compiler from removing the reads.
    const auto sequential_start = std::chrono::steady_clock::now();
    for (double value : values) sum += value;
    const auto sequential_end = std::chrono::steady_clock::now();

    const auto scattered_start = std::chrono::steady_clock::now();
    for (std::size_t index : order) sum += values[index];
    const auto scattered_end = std::chrono::steady_clock::now();

    const auto sequential_ms = std::chrono::duration<double, std::milli>(
        sequential_end - sequential_start).count();
    const auto scattered_ms = std::chrono::duration<double, std::milli>(
        scattered_end - scattered_start).count();
    std::cout << "sequential_ms=" << sequential_ms
              << " scattered_ms=" << scattered_ms
              << " checksum=" << sum << '\n';
}
