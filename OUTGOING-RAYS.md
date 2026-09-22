# Outgoing-ray reuse

A trace records each ray at a conservative free-space plane beyond every optic
and mask, retaining its XY position, direction slopes, power and termination
status. Later detector planes are intersected analytically and binned normally.
This retains absorption, Fresnel sampling and spectral color. Samples before
that plane still run the full transport algorithm.

Keys include all source/optics/masks/material/seed/sample-count parameters plus
engine version. Detector distance, field, resolution and display
choices do not invalidate the ray set. Each worker retains at most 128 MiB of
ray arrays in memory. Persisted rays and completed images share the existing
1 GB SQLite cache and its usage-based eviction/free-space reserve. Ray sets
larger than the memory limit bypass intermediate caching.

Changes to geometry/modulation require a new trace. Once an animation pose has
been cached, new downstream slice distances can reuse its outgoing rays.
CPU and CUDA maintain separate physical cache keys.

## Validation and measurement

Reused and full traces were compared on CPU and CUDA for prism, cylindrical
and fractured surfaces with a downstream aperture and three wavelengths.
Scalar/color maps and power fractions matched; sparse ray coordinates agreed
within 1e-9 mm. Cache-key invalidation, byte limits and lossless encoding tested.

RTX 4070 laptop: eight downstream planes, 100,000 rays, 128-square detector,
fractured glass with 2 mm pitch / 1 mm relief. Warm full trace: 0.5984 seconds;
trace once plus seven reuses: 0.2671 seconds (2.24x faster). This measures engine
tracing and binning, excluding HTTP, browser rendering and first disk writes.
The first pair was 1.4951 / 0.2791 seconds and included additional warmup effects.

As of v0.4.7, CPU/CUDA/Auto/Hybrid share cache keys. Backend is retained as provenance, not a cache discriminator; minor numerical differences are accepted for art preparation.
