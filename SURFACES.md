# Optical surface coverage

| UI type | Geometry and expected behavior |
|---|---|
| Linear Fresnel (one line) | Straight grooves with slopes varying across the aperture, designed via Snell's law for parallel input and a common line at the selected focal distance from the grooved exit. Each groove uses its centre slope, so finite groove width limits focus sharpness. Design index is separate from actual material index. |
| Lenticular sheet (circular) | Repeating circular cylindrical lenslets. Pitch and sag define curvature and repeated line foci. This retains the saved `cylindrical` kind. |
| Elliptical ridges | Existing repeating elliptical cylindrical profile, retained for artistic shaping. |
| Triangular ridges | Constant triangular ribs: angular redirection/splitting, not a common line focus. |
| Crossed triangular prisms | Sum of orthogonal triangular profiles on one face; two-axis refraction. Not two separate crossed sheets. Those can be assembled as two rotated layers. |
| Pyramid array | Square-based pyramids with planar faces; two-axis angular redistribution. |
| Ice / Hammered / Hair-cell | Seeded generic correlated relief: sharp irregular, rounded irregular, or elongated grain respectively. Pitch controls correlation scale and relief controls height. These are procedural approximations, not measured supplier patterns. |
| Faceted / Fractured glass | Existing convex shard and irregular planar fracture surfaces. |

All profiles are closed solids traced with the existing refraction, Fresnel reflection and absorption transport on CPU/CUDA. Depth preview samples the actual mesh. Rotation turns the profile in its plane. Irregular texture radius/pitch is bounded to 12 to avoid silently undersampling fine features; the UI/backend reports invalid values.

No measured BSDF haze, volume scattering, laser diffraction orders or speckle is added by these geometric models. Crosses/diamonds/comb patterns depend on source, spacing and other layers; no particular projected shape is guaranteed. A divergent LED does not produce the ideal collimated-input Fresnel focus.

Fresnel relief is an envelope allowance: increase it or reduce pitch if the designed groove height does not fit. Focal length is measured from the exit surface approximately (groove relief makes the distance slightly different across the face). The linear facets approximate a continuous acylindrical design.

Reference: https://www.fresneltech.com/resources and https://www.fresneltech.com/fresnel-lenses distinguish cylindrical Fresnel, lenticular and prism arrays. Manufacturer profile measurements would be required to match a particular purchased sheet.

Planar pyramid/crossed-prism arrays use exact facets clipped to a 128-sided circular aperture, with radius/pitch <= 40. A 26 mm disc supports 0.5–1 mm pitch. Triangular ribs already use cusp-aligned planar strips (radius/pitch <= 100); pitch is centre-to-centre. Relief remains independent of pitch and determines facet angle.
