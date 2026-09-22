# Hybrid CPU + CUDA

Select Hybrid CPU + CUDA in the backend menu. The main detector stays on CUDA.
Sandwich slices use two persistent processes; each takes another slice when ready.
CPU tracing uses at most four Numba threads (and no more than half logical CPUs).
CUDA takes nearer queued slices, CPU takes farther ones. When CUDA finishes its
queue, it may duplicate the last CPU slice: the first result wins and cancels the
other. Results are sorted by physical distance, regardless of completion order.
Parameter edits cancel both slice workers. Each backend has a separate cancellation
watermark so cancelling CPU work does not cancel CUDA work. Both use the existing
shared SQLite cache with its 1 GB cap; cache errors do not prevent computation.

## Local measurement, 2026-09-21

Eight uncached fractured-glass slices, 100,000 rays each, 128-square detector,
2 mm facet pitch, 1 mm relief, throws 100–450 mm. Both workers warmed first.
An alternating CUDA / Hybrid / Hybrid / CUDA run measured 1.638 / 0.647 / 0.641 /
0.641 seconds. The first pass still had preparation overhead; the stable runs
show no meaningful Hybrid speedup. CUDA won all eight slices, including the
speculative CPU tail. Before tail takeover, Hybrid waited 5.6 seconds for CPU.

These timings are illustrative, not a guarantee. Hybrid can spend extra CPU work
without improving throughput. CUDA-only remains available and is the default.
