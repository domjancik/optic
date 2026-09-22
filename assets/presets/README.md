# Tested optics recipes

## LED 5° - three lines - 24 mm throw

Saved in the current browser's Optics presets. The JSON is a durable optics-only
recipe; the adjacent validation JSON records the complete simulated setup.

Use LED mode, an 18 mm pupil diameter, 5° full cone, detector Z = 24 mm,
and a 30 mm detector field. Pattern view at -6 EV displays the lines clearly
with the tested 1 W RGB + neutral-white approximation.

A cylindrical ridge array (6 mm pitch, 0.5 mm relief, 2 mm substrate,
26 mm diameter) sits at Z = 6 mm. PMMA-like material uses n550 = 1.49,
dispersion = 0.004, no absorption. No mask or modulation is needed.

The 500,000-ray spectral simulation produced three lines near X = -6, 0,
and +6 mm with 92.45% of emitted power reaching the detector. This is a
near-field result, not a validated metre-scale wall projection. The source
is an idealized output pupil and cone, not a measured ray set for the LED.

Loading an optics preset preserves source, detector, scene, and projector
position. Set the above source and detector values separately when needed.