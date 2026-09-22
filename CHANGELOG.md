## 0.4.22 — Reduce structured SSGI sampling artifacts

- Decorrelate the bounce sampling spiral per pixel with deterministic integer hashing, randomized rotation and stratified radial jitter. Increase samples from 32 to 48.
- Preserve spatial smoothing, direct projection and static-frame stability; no temporal history or optical-cache changes. This reduces regular alias patterns but cannot remove all undersampling.

## 0.4.21 — Soften indirect lighting

- Filter the linear SSGI bounce buffer before tone mapping and compositing, using a 25-tap depth/normal-aware spatial filter.
- Add Softness (0–12 pixels, default 4); preserve the sharp direct projection, silhouettes and Pattern view. No temporal accumulation or optical recomputation.

## 0.4.20 — Optional screen-space diffuse bounce

- Add SSGI, Bounce intensity and Reach controls in Scene. Gather projected linear HDR light from visible surfaces using depth, normals and short screen-space visibility checks.
- Composite only additional indirect light over the existing antialiased direct render. Exclude ambient fill, glare and sandwich visualization from bounce input; preserve Pattern and optical cache keys.
- Single approximate diffuse bounce with assumed 0.6 reflectance, 32 deterministic samples, up to 96-pixel reach, no temporal feedback. Hidden geometry and off-screen lighting remain unavailable. Requires floating-point render targets.

## 0.4.19 — Visible front lens glow

- Add illustrative front-facing lens glow outside the narrow beam, while retaining directional optical-map glare and geometry occlusion. No glow from behind the emitter or from muted sources.
- Add Glow strength (0–100×) independent of optical simulation. Lens tint comes from the map average; the uncalibrated glow is a visual aid.

## 0.4.18 — GPU slice infill

- Add optional GPU infill and 1–16 subdivisions per distance interval in scene sandwich controls. Blend existing neighboring textures without extra simulation, image generation or texture allocation.
- Normalize additive opacity across the denser stack; retain geometry shadows, source modulation and scene depth tests. Toggle off to restore the original measured planes.
- Display-space interpolation only: sparse moving caustics can cross-fade or blur. Optical path inspection and physical detector results remain measured.

## 0.4.17 — Clean scene, source glare and ambient light

- Add Sources overlay toggle, Glare toggle, and 0–10× ambient intensity in the scene viewport; persist separately from optical configuration and cache keys.
- Render additive, depth-tested source halos sampled from the optical map in the camera direction. Follow source color, exposure, distance and per-source brightness/mute; approximate visual glare rather than eye/camera optics.
- Keep detector Pattern view unchanged.

## 0.4.16 — Playback speed

- Add live 0.1–4× playback speed with numeric entry, label drag and wheel adjustment. Retime the existing frame set without changing poses, simulation FPS or cache keys.
- Scale scene brightness modulation by the same speed; rebase its clock on live changes to preserve phase. All optical frames still play in sequence, limited by compute/delivery throughput.

## 0.4.15 — Viewport projector transforms

- Select numbered projector markers directly in the scene. Move with world X/Y/Z handles or the view-plane centre handle; rotate with yaw/pitch rings.
- Shift gives fine movement, Ctrl snaps translation to 0.1 m or rotation to 5 degrees, Escape cancels, and each drag is one undo step. Placement edits and their undo reuse optical results.

## 0.4.14 — Instanced scene projectors and realtime exposure modulation

- Up to eight scene projectors share the same optical map and slices; duplicate/select/remove/mute and edit independent position/direction/brightness in Projector.
- Reuse the existing modulation panel for per-projector EV (sine/triangle/ramp/smooth noise, base/depth/rate/phase). Brightness animation runs at display cadence on Play without tracing optics; static-optics playback also avoids worker requests.
- Sum projected light before tone mapping; cache per-projector hard shadows in an atlas and show numbered source markers. Optics presets and simulation keys exclude scene instances.

## 0.4.13 — Atomic sandwich playback

- Retrieve resident slice frames together in one RAM-cache batch. Queue only missing slices.
- Keep the previous complete sandwich visible until all next-frame slices are ready, then replace it once.

## 0.4.12 — Fine planar optical arrays

- Replace densely sampled pyramid/crossed-prism meshes with exact planar facets and clipped aperture edges; support 0.5–1 mm pitch on a 26 mm optic.
- Verify existing triangular ribs at the same pitches. Fine irregular texture limits remain unchanged.

## 0.4.11 — Shared playback RAM budget and residency timeline

- One off-thread decoded-frame store is shared by detector, CPU and CUDA slice workers. Settings offers 512 MiB, 1, 2 or 4 GiB (default 1 GiB), allocated on demand.
- Timeline bottom strip shows current-configuration RAM residency: green complete, amber partial slice coverage. Budget reduction evicts immediately.
- Cache settings show RAM use and estimated full-loop map memory including enabled slices. Preview canvases/GPU and temporary copies remain additional overhead; disk limit stays 1 GB.

## 0.4.10 — Cached playback delivery

- Retain decoded frames in bounded worker RAM caches (128 MiB per worker), bypassing HTTP, job scheduling, JSON and base64 on hits. Disk cap remains 1 GB.
- Faster base64 decoding, bounded 64 MiB sandwich preview image reuse, and request/decode timing in frame status.
- Export re-acquires a server result when replaying a RAM-cached frame.

## 0.4.9 — LED cone edge softness

- Add LED Edge softness (0–100%): Gaussian slope spread relative to nominal cone half-angle, preserving total optical power. Zero preserves the original hard cone; laser is unchanged.
- Source and result/ray caches invalidate on softness changes.

## 0.4.8 — Optical surface families

- Add linear Fresnel with design focal length/index, crossed triangular prisms, pyramids, and procedural ice/hammer/hair-cell relief.
- Label repeating circular cylindrical lenses as lenticular sheets; retain existing saved kinds.
- All new surfaces use closed refractive meshes and actual surface depth previews. Texture models are generic relief, not measured haze/BSDFs.

## 0.4.7 — Share cache across compute backends

- CPU, CUDA, Auto and Hybrid reuse the same completed maps and outgoing rays for identical physical inputs. Producing backend remains in metrics.
- Existing backend-specific cache entries warm again under the new keys; the shared 1 GB limit is unchanged.

## 0.4.6 — Playback frame alignment

- Use canonical frame/FPS timestamps for playback, scrubbing, and edits; round loop duration to a whole frame count.
- Schedule at the selected FPS without stretching intervals and guard against duplicate playback timers.
- Show the effective frame-grid loop duration in cache estimates.

# Changelog

## 0.4.5 — outgoing-ray reuse

- Trace to a conservative exit plane once and reuse ray slopes/powers for later detector distances, sizes and resolutions.
- Preserve full tracing for samples before the exit plane.
- Retain outgoing rays in a bounded 128 MB memory cache per worker and the existing shared 1 GB disk cache.
- Invalidate for source, optics, masks, material, sampling seed/count, backend or engine changes.

## 0.4.4 — synchronized sandwich playback

- Enable Play in Optical path and preserve playback when switching views.
- Wait for the modulated slice batch before advancing the animation, including Scene overlay playback.
- Cancel pending frame timers on edits and stop playback on slice errors.

## 0.4.3 — optional sandwich shadows

- Scene Shadows checkbox applies the existing projector shadow map to additive slices.
- Changes redraw immediately without optical recomputation.
- Point-source hard shadows within the existing shadow-map coverage; no finite-aperture soft shadows.

## 0.4.2 — hybrid CPU/CUDA slices

- Add optional Hybrid CPU + CUDA backend: detector stays on CUDA, independent distance slices run on both devices.
- Two persistent compute processes with independent cancellation; CPU capped at four threads.
- CUDA can take over a slow CPU tail; first result wins and cancels the duplicate.
- Faster workers take more slices; results remain ordered by distance.
- Cache remains shared with the existing 1 GB limit.

## 0.4.1 — live scene slices

- Move sandwich visibility and independent brightness controls into Scene view.
- Keep scene-enabled slices computing outside the Optical path tab.
- Refresh slices after the primary detector result, avoiding competing compute jobs.
- Cancel stale slice work immediately when a new simulation is requested.

## 0.4.0 — optical path sandwich

- Add additive orbitable/pannable distance slices, source/layer envelopes, opacity and visual spacing.
- Trace each free-space distance in the background using the same source and existing cache.
- Toggle In scene to place the sandwich at physical distances along the projector pose.
- Select a distance to inspect its map; preserve scene, optics and detector settings.
- Up to 24 slices, capped at 512 pixels each to bound memory. Optional sparse traced rays connect slices without crossing optical layers; internal bounce paths are not displayed.

## 0.3.9 — structured fractured glass

- Add Fractured glass: irregular triangular surface with Facet size and Breakage depth controls.
- Use the same closed geometry for depth preview and CPU/CUDA transport.
- Preserve the original Faceted glass shape; cap detail at 1600 interior vertices.

## 0.3.8 — bundled line preset

- Ship the validated 5-degree LED line preset to every browser, independent of local storage.
- Show required source/detector setup; preserve those settings on load.
- Keep custom overrides local; deleting an override reveals the bundled recipe.

## 0.3.7 — scene panning

- Pan with Shift-drag, middle/right-drag, two-finger movement, or Shift + arrow keys.
- Camera translation follows the view plane and zoom level; Reset view clears it.
- Panning changes only the preview camera and never retraces optics or moves the projector.

## 0.3.6 — live exposure response

- Exposure changes redraw immediately during numerical entry as well as drag/wheel edits, without optical recomputation.
- Expand both controls to −12…+12 EV for bright detector caustics.
- Apply scene exposure before tone mapping to ambient fill and projected light together.
- Verified visible changes at −8 and +4 EV in Pattern view using the same cached map.

## 0.3.5 — optics presets and per-layer mute

- Named browser-local presets for optics/masks, physical ordering/gaps, modulation, mute states and material.
- Loading preserves source, projector pose, scene, detector and timeline settings.
- Per-layer mute buttons bypass transport while preserving reserved spacing and selection.
- Undo supports preset loads and mute changes; preset save/replace and deletion leave the scene alone.

## 0.3.4 — numeric settings migration

- Convert persisted numeric strings from legacy controls into numbers on load and before submitting simulations.
- Preserve selected values; reject invalid numeric settings with a field-specific message.
- Validate engine integer fields before range comparisons, preventing int/string TypeErrors.

## 0.3.3 — constrained-window layout

- Fit the app to the viewport instead of pushing playback below fixed minimum panel heights.
- Scroll the complete parameter/modulation panel independently; keep its title visible.
- Place preview above adjacent parameters and layers below 1000 px; compact cards, fields and actions on phones.
- Wrap transport and header controls; reset parameter scroll on layer selection.
- Verified at 800×600, 375×667 and 1280×450, including access to lower modulation controls.

## 0.3.2 — adjacent vertical layer stack

- Place a compact vertical stack directly right of the parameters, with source at bottom and screen at top.
- Up/down reordering follows the displayed optical direction; retain editable gaps and physical path positions.
- Shift+1 selects source, Shift+2–9 select layers in physical order, Shift+0 selects screen; badges update after reordering.
- Keep parameters and stack adjacent on narrow screens; ignore shortcuts in text/number fields and open dialogs.

## 0.3.1 — persistent animation result cache

- Exact-config, engine-versioned, lossless disk results shared across loops and restarts.
- Hard 1 GB database ceiling, 64 MiB free-space reserve, usage/recency eviction.
- Deterministic sequential animation frames with configurable target FPS.
- Cache-hit status, current disk usage, raw and observed-compression loop estimates.
- Cache failure never prevents fresh optical computation; only completed transport results are stored.

## 0.3.0 — spectral source controls and movable mesh projection

- RGBW/WW channel controls, white approximations and named laser colors; editable generic dispersion.
- Compact direct-entry, drag and wheel numerical fields with fine/coarse modifiers.
- Movable generic projector, static full-resolution v15 demo mesh and geometric shadows.
- Preserve scalar detector data separately from approximate spectral display color.
- Correct scene clipping, responsive layout and hue-preserving display tone mapping.

## 0.2.2 — spectral transport preview

- Bin display RGB from the same wavelength-tagged rays; preserve the scalar irradiance and power budget.
- Approximate narrow laser and broadband white spectra, with explicit uncalibrated display colors.
- Export color preview PNG and display RGB NPY separately from physical grayscale irradiance.

## 0.2.1 — cancellation

- Superseded transport stops between 65,536-ray batches, preserving warm workers.
- Batched CPU/CUDA results preserve original random streams. Setup and first compilation remain synchronous inside the worker.

## 0.2.0 — layer studio

- Large projection viewport, physical layer cards, editable gaps, drag/button reordering and per-layer inspectors.
- Direct LED/Gaussian laser source controls; retain material, absorption, high-ray-count, export and view controls.
- Visible actual-mesh surface height and cross-section; aperture previews follow dot/grid/splotch geometry.
- Independent rotation, tilt, position and radius modulation with a time waveform and responsive background computation.
- Property-preserving duplication, undo/redo and persisted source/material/layer settings.
- Responsive WebGL canvas, touch orbit/pinch, keyboard view controls and explicit physics limitations.
- Invalidate stale results and exports as soon as optical parameters change.

## 0.1.2 — layer geometry validation

- Reject tilt envelopes beyond ±90° rather than reserve an invalid axial slot.
- Preserve background-worker error details in the regression assertion.

## 0.1.1 — physical layer ordering and regression checks

- Stable layer IDs, independent masks/optics and property-preserving duplication.
- Reserve lower and upper bounds across tilt/radius modulation; bypass retains slots.
- Deterministic modulation, including smooth noise across cycle boundaries.
- Tests for mask position before/after refraction and reflected return paths.

## 0.1.0 — multi-mask transport and surface inspection

- Multiple independent mask planes on CPU/CUDA, retaining single-mask compatibility.
- Actual-mesh height-map endpoint and centre cross-section in millimetres.

## 0.0.1 — recovered pre-redesign working app

- Fullscreen projection studio with LED/Gaussian ray sources, refracting ridges and a single pattern mask.
- Recovered from recorded file contents and edits before the layer-studio redesign.
- Original 18 tests and live CUDA browser workflow verified before committing.
