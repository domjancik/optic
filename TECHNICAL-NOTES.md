# Optic technical notes

Focused physical detector-map simulator, implemented and tested on 2026-09-20.
Run `python app.py` here, or run `start.ps1`, then open http://127.0.0.1:8766.
The server binds to localhost only. No remote services or Blender are required.
Dependencies: Python, numpy, scipy, numba, Pillow. Install them using `pip install -r requirements.txt`.

## Use

1. Set effective source pupil diameter, full cone angle, and **optical** power.
2. Choose triangular ridges, cylindrical/elliptical-profile ridges, a synthetic convex shard, or a flat reference plate.
3. Select a card to edit its properties. Add independent optics and masks; move their cards to change physical order. Gaps are between reserved axial envelopes, including the extremes of enabled tilt/radius modulation. Bypassing a layer retains its physical slot.
4. Changes automatically retrace after a short debounce. Auto backend is selected by default; CPU and CUDA can also be selected explicitly.
5. Orbit the central 3D scene by dragging; scroll or pinch to zoom. Switch to Pattern for the traced reference plane. Exposure and camera changes redraw immediately without retracing.
6. Modulate individual layer properties with sine, triangle, ramp or smooth noise. Pause stops scheduling new poses; an already running pose may finish.
7. Save maps explicitly to write raw NPY, grayscale Radiance HDR, preview PNG and configuration/metrics JSON. Live updates write only the bounded disposable result cache; permanent map exports remain explicit.

The layer studio uses local WebGL2, a central projection, ordered layer cards and a selected-layer inspector. Source settings include LED and Gaussian laser rays. The optic inspector exposes an actual-mesh surface height map and centre cross-section. Projector selects either the bench or the bundled demo mesh, with X/Y/Z position and yaw/pitch. Moving the projector transforms the generic optical stack together and reuses the detector map without retracing.

The browser Web Worker handles requests, polling, decoding and latest-change queueing. A persistent Python process runs optical transport separately from the threaded HTTP server. Pending edits are coalesced; changing samples or optics cancels superseded transport between 65,536-ray batches. Source generation, geometry setup and first compilation cannot be interrupted midway. A live 5M-ray cancellation followed by a small replacement completed in about 1.75 seconds including work already underway. Camera, exposure and UI input remain available during computation. First use includes compilation. A warm 100k-ray CUDA update was about 150 ms during UI verification; 2M rays took about 1.1 s. These timings exclude network polling and display overhead and are not frame-rate promises.

CPU was faster for most small benchmark scenes below. CUDA is selectable and verified on the RTX 4070 Laptop GPU. `auto` tries CUDA then CPU and reports fallback; it is not an autotuner.

### 3D projection approximation

The physical simulation computes irradiance on the selected detector plane. The 3D renderer reuses that map as a point projector at the movable source position: UV coordinates derive from direction, with distance-squared and receiver-angle correction plus hard shadow maps from receiver geometry. This is useful for scene layout and appearance, but it does not retain finite-pupil position/direction correlations, produce correct near-field parallax or soft shadows, or trace interreflection. Changing optical geometry or reference distance retraces the detector map. Scene surfaces and display exposure are illustrative, not calibrated photometry.

## Physics and approximation boundaries

- Rays start at z=0 in air, carrying position, unit direction, wavelength in nm, and optical power in W. Default source is an independent uniform pupil and uniform-solid-angle cone. The full angle is **not FWHM**. It is a sensitivity model, not a measured LED/collimator model.
- The supplier's 20 mm lens and 21.90 x 13.50 mm holder are packaging references, not an optical prescription. The 47.5 mm PCB outline does not determine emitting-area size or angular distribution. The 4 W electrical rating is not used as optical power.
- Source rays are cached in the UI server when source parameters are unchanged. Fixed LED/lens behavior is represented by this outgoing ray set; the proprietary lens itself is not traced.
- Closed, polygonal optics use exact ray/triangle intersections, a stackless BVH, Snell refraction, unpolarized Fresnel reflection, total internal reflection, and Beer-Lambert absorption. Fresnel branches are sampled statistically without doubling ray counts. No denoising or artificial line textures are used.
- CPU and CUDA compile the same double-precision transport equations. This favors matching numerical behavior over peak GPU throughput; CUDA is not using RTX hardware traversal. Meshes/BVHs are currently rebuilt for each pose; source rays are reused. Detector binning is on CPU. These are potential future optimizations, not implemented claims.
- All optics share one material and must have non-overlapping axial envelopes. Nested glass, touching solids, rough-surface scattering, diffraction, fluorescence, polarization tracking, birefringent crystals, housing shadows and light returned into the source optics are not modeled. Rays missing an optic continue through air: there is no implicit opaque disc carrier.
- Prism ridges have planar facets aligned exactly with mesh columns. Rounded ridges are tessellated (48 segments per pitch); refine this before trusting narrow caustic widths. Circular rims are polygonal. The shard is a deterministic synthetic convex polyhedron, not a scan of a real fragment.
- JSON supports wavelength samples and weights plus a Cauchy-like index adjustment: n(lambda)=n550+B*(1/lambda_um² - 1/0.55²). Source offers RGB + white/warm-white, approximate 4000 K/2700 K white, and 450/520/532/638/650 nm lasers. Channel levels are relative optical powers, not electrical PWM calibration. Color mode enables an illustrative B=0.004 when B was zero; edit Dispersion in Settings, including B=0 to compare. Each ray retains its wavelength through refraction, so color separation is geometric dispersion, not a painted overlay. Display RGB is an approximate wavelength mapping, not calibrated colorimetry. White presets use sampled blackbody envelopes, not measured LED spectra; LED die offsets are unknown and share one source pupil. Scalar exports sum spectral **power**, not lux. More spectral samples share the existing ray budget and may increase color noise.
- A map applies to its chosen plane and dimensions. Recompute for different distance, tilt, optic geometry or source properties. Higher ray count reduces Monte Carlo noise, not uncertainty in the real components.

## Outputs

`irradiance.npy`: float32 W/m², row zero at negative detector Y (lower edge).
`irradiance.hdr`: RGBE grayscale copies of W/m², top row at positive Y. This stores irradiance, **not radiance**; do not use it as an environment map and expect calibrated lighting. Preview PNG is exposure/gamma adjusted and must not be used for quantitative analysis.
`result.json`: exact input, measured timings, flux budget and preview scale.
Outputs are stored beneath `outputs/`; they accumulate until you remove unwanted runs.

For Blender, map a preview onto an emission-shaded target plane for visualization, or use the linear HDR with a deliberately calibrated material. This reproduces the appearance on that particular plane; it does not recreate the complete outgoing light field or room illumination.

## Python and CLI

```python
import engine
cfg = engine.defaults()
rays = engine.source_rays(cfg)
result = engine.simulate(cfg, backend='cpu', source=rays)
```

`source` can be a measured/custom N x 8 array `[x_mm,y_mm,z_mm,dx,dy,dz,wavelength_nm,power_W]`, with rays starting in air upstream of every optic, normalized directions, positive total power. Current UI uses the generated source; ray-file format converters are not included. Imported sources override the source-generation fields in cfg; metrics report actual total power and ray count.

`python app.py --config example.json --backend cuda --out outputs/my-study`
The config file must contain a complete configuration, such as the `config` object in a saved result JSON.

## Verification and measured performance

`python -m unittest test_engine test_jobs test_mask test_ridges_laser test_layers test_surface_map test_mask_order -v` runs 29 checks for Snell's law, Fresnel reflectance, TIR, slab multiple reflections, absorption, closed meshes, detector crop/energy, source reuse, laser envelopes, mask ordering, surface inspection, CPU/GPU agreement and file exports. `node --test layer-state.test.js` runs 9 layer-state checks. CUDA comparison requires a working CUDA toolkit and NVIDIA GPU; it deliberately fails rather than quietly skipping GPU verification. The worker test needs subprocess permission; on this Windows host the restricted sandbox fails it while the normal local environment passes.

`python benchmark.py` regenerates maps, a 24-frame two-disc sequence, timing records and a two-seed sampling study. Results: `outputs/benchmark/benchmark.json`.

Warm 500,000-ray 512² maps on this machine, initial measured run (source generation, geometry, transport, transfer and detector binning included; image export excluded):

| Optic | CPU | RTX 4070 Laptop CUDA |
|---|---:|---:|
| Flat plate | 0.192 s | 0.227 s |
| Triangular ridges | 0.211 s | 0.271 s |
| Rounded ridges | 0.383 s | 0.809 s |
| Synthetic shard | 0.185 s | 0.174 s |

These are measurements of this implementation, not a controlled Blender comparison or a real-time guarantee. Initial compilation and competing applications change latency. CUDA 13 DLL discovery is adapted locally within the Python process for this Windows installation; no system CUDA files were changed. Unused CUDA 12 packages downloaded during troubleshooting were removed; the running engine uses the existing CUDA 13.1 toolkit.

## References

- Mitsuba emitter-first caustics: https://mitsuba.readthedocs.io/en/latest/src/inverse_rendering/caustics_optimization.html
- Fixed subsystem reuse: https://optics.ansys.com/hc/en-us/articles/11969397310227-Reducing-Simulation-Time-with-Cover-Lens-on-Sources

This is a validated numerical prototype under stated assumptions, not a calibrated prediction for the purchased LED and optics. Compare a real bare-beam map and a known reference prism/plate before manufacturing optical parts.

## Elongated ridges and laser source

The triangular option is a one-dimensional array of long straight triangular ridges, not a grid of pyramids. Identical planar facets give two main refracted directions under collimated illumination; a count of ridges does not imply the same count of far-field lines. Cylindrical ridges have circular cross-sections, constant along their length. Their radius is R=(pitch²/4+sag²)/(2*sag); a shallow lenslet approximately focuses at R/(n-1). The profile thumbnail exaggerates sag to show shape.

“Try parallel-line focus” sets an expanded 532 nm Gaussian laser (18 mm 1/e² diameter, 0.003 degree full divergence, 5 mW), 2 mm pitch, 0.005 mm circular sag, index 1.49 and a detector at 215 mm. These are illustrative parameters, not specifications of the purchased component. Scan detector distance to see the separate line foci merge away from focus. Source waist is at z=0. Gaussian rays sample independent position/direction distributions; divergence below lambda/(pi*w0) is rejected. This models an M²>=1 Gaussian envelope, not coherent optical phase. It does not compute grating orders, interference, speckle or diffraction-limited line widths at the ridges; narrow-focus maps remain geometric approximations. CUDA supports this ray model just as it supports the LED model.

Sources: https://www.edmundoptics.com/f/cylindrical-microlens-arrays/14569/ and https://www.edmundoptics.com/f/lenticular-arrays/12445/ .
Run `python -m unittest test_ridges_laser -v` for the focused ridge and laser checks.

### Controls retained in v0.2.0

| Previous control | Layer studio location |
|---|---|
| LED / laser, pupil, divergence, optical power, wavelength | Select Source |
| Second disc, separate phase | Add optic; edit its independent rotation/modulation |
| Tilt and wobble | Optic Tilt; modulation target Tilt / wobble |
| Mask type, count, radius, offsets | Add mask; selected-layer inspector |
| Mask Z / disc spacing | Reorder cards and set the gaps; path labels show resulting Z |
| Material index, absorption, rays up to 5M, resolution | Settings |
| Detector distance, field, exposure | Select Screen, or Settings |
| Fullscreen, reset camera, objects/shadows | Header, viewport, Settings respectively |
| Detector power, unresolved rays, mask losses | Bottom status |
| Raw map export | Save maps, enabled only for the current result |

The line-focus preset replaces the working stack with an illustrative configuration; Undo restores it. Numerical fields support direct entry, label dragging and mousewheel adjustment; Shift gives finer steps and Ctrl coarser steps. Fields commit on blur/Enter and label drags update live. Surface inspection shows the layer's base geometry in local coordinates; it is not an animated camera-depth view. Masks are thin planes and do not support tilt.

## Pattern mask layer

Use Add mask, then choose a single circular hole, an N×N dot grid, or a deterministic grid of irregular splotches. Adjust radius, spacing, grid count, rotation and X/Y offsets. The preview window is not a finite outer mask boundary. The physical model is an infinite opaque absorbing plane with the selected open regions. Reorder its card before or after an optic to test an upstream or downstream mask. Placement inside an optic envelope is rejected. The CPU and CUDA transport check mask intersections along each ray segment, including returning reflected rays. Blocked power is reported separately as `fractions.masked`. It is not renormalized. An aperture does not automatically form a sharp projected image; divergence and focusing determine blur. No aperture diffraction, thickness, scattering or edge bevels are modeled.

## Multiple mask transport and surface inspection

The engine now accepts `masks: [...]` with up to 16 independently positioned mask planes. An explicit list overrides the legacy `mask` field, including an empty list. Every free-space ray segment is tested against each crossed mask before the next glass intersection; transparent openings do not consume the bounce budget. The list's storage order cannot change physics: world positions determine traversal. Mask planes need 0.01 mm separation and may not intersect a glass axial envelope. Optics also accept optional X/Y translation in mm.

`POST /api/surface-map` with `{ "optic": { ... } }` returns a 128×128 local-space upper-surface height map and exact centre cross-section sampled from the same triangle mesh used by transport. Heights are millimetres above the local base plane, including thickness; null samples lie outside the polygonal footprint. Pose is deliberately removed so rotation/translation do not alter the profile inspection. The map represents the upper envelope; it is not a full volume description or a camera depth buffer. Samples can miss a mathematical ridge peak between pixels. Height queries are cached independently of optical tracing.

## v0.3.0 scene and color preview

The bundled receiver is a generic demonstration scene. Export your own Blender scene with `export_scene.py`. Receiver surfaces use a generic opaque diffuse approximation; original materials, lights and animation are not reproduced.

Colored display maps come from the same transported rays, alongside unchanged physical irradiance. Exports additionally include `display_rgb.npy` for color runs. A warm 500k-ray, 512-square prism case measured 275 ms scalar versus 451 ms with color; this is one case, not a general speed guarantee. Full mesh drawing and shadow maps are browser GPU work; optical tracing stays in the background Python worker.

Verification: 39 Python checks across transport, cancellation, spectra, masks and jobs, plus 15 Node checks for layer state, numerical controls and scene coordinates. Run `python -m pytest -p no:cacheprovider test_*.py` and `node --test layer-state.test.js numeric-controls.test.js scene-math.test.js`.

## Persistent frame cache (v0.3.1)

Completed interactive jobs are cached losslessly in `.result-cache/results.sqlite`. Keys cover the full optical configuration, seed, sample count, requested backend and a fingerprint of the transport/source code. Camera, projector pose and exposure do not affect the optical map. An exact hit skips source generation and ray transport. Only completed transport results are stored; cache I/O failure falls back to computation. Explicit exported maps in `outputs/` are separate from the cache budget.

The database has a hard **1,000,000,000-byte** ceiling including its index. SQLite uses memory journals and releases unused pages on eviction. Cache writes also preserve 64 MiB of free disk, so the usable cache may be smaller. Eviction favors frequently reused entries, discounts usage with age, and breaks ties by oldest access. Results survive restarts; incompatible engine fingerprints naturally miss and old entries are evicted as space is needed.

Playback uses `round(duration × FPS)` deterministic frames and visits them sequentially. The first loop may run slower than its nominal duration while frames compute; cached replay runs up to the chosen target FPS, subject to disk, HTTP, decoding and rendering overhead. This avoids timestamp drift between repetitions. Scrubbing retains its exact requested pose. A nonanimated stack needs just one unique map.

Settings shows target FPS, cache occupancy, raw loop map size, and an estimated compressed loop size based on the current frame. Estimates are not allocation guarantees: compression varies with caustic occupancy and poses. For an 8-second loop at 24 fps and 512², raw maps are 201 MB monochrome or 1.01 GB with scalar plus RGBA color. Reduce pixels or FPS if the loop does not fit; scalar storage scales with pixels squared, while ray count affects compute time and compressibility rather than map dimensions.

Cache checks: `python -m pytest -p no:cacheprovider test_result_cache.py test_jobs.py test_cancellation.py test_http.py`; timeline checks: `node --test animation-clock.test.js`.

## Vertical stack shortcuts (v0.3.2)

The stack sits immediately to the right of the parameter inspector. Light travels upward: source at bottom, layers in physical sequence, screen at top. Drag cards or use Up/Down to reorder. Shift+1 selects the source; Shift+2 through Shift+9 select the first eight optical/mask layers counted from the source; Shift+0 selects the screen. Badges follow the current physical order. Shortcuts leave typing in input fields and dialogs alone. Extra layers remain accessible by clicking their cards. On narrow screens the preview sits above the adjacent parameters and stack.

### Constrained windows (v0.3.3)

The application fits the available viewport height, with playback always in the bottom row. Below 1000 px wide, the preview moves above the parameter inspector and adjacent layer rail. Scroll inside the parameter panel to reach geometry and modulation; the panel title stays visible. Layer cards scroll independently, and selecting another layer returns its parameter panel to the top. Compact headers, numeric fields and wrapping footer controls support narrow and short windows without document overflow.

### Optics presets and mute (v0.3.5)

Open **Presets** above the layer stack to name and save the current optics, replace a preset by the same name, load it, or delete it. Presets persist in this browser's local storage. They include optic/mask geometry, order, gaps, modulation, enabled states and common material settings. They exclude source spectrum/power/beam, projector position/orientation, scene, detector, exposure, compute and timeline settings. Loading stops playback and supports Undo.

Use **Mute** below any optical or mask card to bypass it without changing selection or its reserved axial space. Click **Muted** to restore it. The existing inspector enable switch stays synchronized. Muting and loading a preset retrace the optics or reuse an exact cached result; they never reset the scene camera or projector pose.

### Exposure (v0.3.6)

Screen → Exposure and Settings → Exposure EV update the display immediately while typing, dragging or using the wheel. The range is −12 to +12 EV. One EV doubles display exposure before tone mapping; very bright caustics can remain saturated until exposure is reduced substantially. Both Pattern and Scene respond; scene ambient fill now follows the same display exposure. Optical power, scalar exported irradiance, cache keys and source/scene position remain unchanged. PNG exports retain their independent export tone scale.