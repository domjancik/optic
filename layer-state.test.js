import assert from 'node:assert/strict';
import test from 'node:test';
import { createProject, addLayer, moveLayer, removeLayer, toEngineConfig, poseAt } from './layer-state.js';

test('layers receive stable ids and the source/screen stay fixed', () => {
  const project = createProject();
  const withMask = addLayer(project, 'mask');
  assert.equal(withMask.layers.length, 2);
  assert.match(withMask.layers[1].id, /^layer-/);
  assert.equal(moveLayer(withMask, withMask.layers[1].id, -1).layers[0].type, 'mask');
});

test('engine config emits independent optics and masks in optical order', () => {
  let project = createProject();
  project = addLayer(project, 'mask');
  project.layers[0].gapBeforeMm = 4;
  project.layers[1].gapBeforeMm = 8;
  const config = toEngineConfig(project, { detector_z_mm: 1000 });
  assert.equal(config.optics[0].z_mm, 4);
  assert.equal(config.masks[0].z_mm, 14.35);
  assert.equal(config.mask, undefined);
});

test('modulation is deterministic and leaves an inactive property untouched', () => {
  const layer = createProject().layers[0];
  layer.rotation = 10;
  layer.modulation.rotation = { enabled: true, waveform: 'sine', base: 10, depth: 5, rate: 1, phase: 0 };
  assert.equal(poseAt(layer, 0).rotation, 10);
  assert.ok(Math.abs(poseAt(layer, .25).rotation - 15) < 1e-8);
  assert.equal(poseAt(layer, .25).tilt, layer.tilt);
});

test('reserved layer positions include thickness and maximum tilt envelope', () => {
  const project = createProject();
  project.layers[0].thickness_mm = 4;
  project.layers[0].radius_mm = 10;
  project.layers[0].modulation.tilt = { enabled: true, base: 0, depth: 30, rate: 1, phase: 0 };
  project.layers.push({ ...project.layers[0], id: 'second', gapBeforeMm: 2 });
  const config = toEngineConfig(project, { detector_z_mm: 100 });
  assert.ok(config.optics[0].z_mm >= 6);
  assert.equal(config.optics[1].z_mm > config.optics[0].z_mm + 4, true);
});

test('smooth noise does not jump at its internal keyframes', () => {
  const layer = createProject().layers[0];
  layer.modulation.rotation = { enabled: true, waveform: 'noise', base: 0, depth: 1, rate: 1, phase: 0 };
  assert.ok(Math.abs(poseAt(layer, 1 / 32 - .0001).rotation - poseAt(layer, 1 / 32 + .0001).rotation) < .01);
});

test('tilt base and lower extent are reserved even at a small first gap', () => {
  const p = createProject(), l = p.layers[0]; l.gapBeforeMm = .1;
  l.modulation.tilt = {enabled:true,base:30,depth:10,rate:1,phase:0};
  const a=toEngineConfig(p,{detector_z_mm:100},0), b=toEngineConfig(p,{detector_z_mm:100},.25);
  assert.ok(a.optics[0].z_mm>l.radius_mm*Math.sin(40*Math.PI/180));
  assert.equal(a.optics[0].z_mm,b.optics[0].z_mm);
});

test('bypass preserves following physical slot exactly', () => {
  let p=addLayer(createProject(),'mask');p.layers[0].depth_mm=1;
  const a=toEngineConfig(p,{detector_z_mm:100});p.layers[0].enabled=false;
  const b=toEngineConfig(p,{detector_z_mm:100});assert.equal(a.masks[0].z_mm,b.masks[0].z_mm);
});

test('smooth noise is continuous across cycle wrap', () => {
  const l=createProject().layers[0];l.modulation.rotation={enabled:true,waveform:'noise',base:0,depth:1,rate:1,phase:0};
  assert.ok(Math.abs(poseAt(l,.999999).rotation-poseAt(l,1.000001).rotation)<.001);
});

test('rejects tilt modulation outside the supported axial packing range', () => {
  const p=createProject();
  p.layers[0].modulation.tilt={enabled:true,base:70,depth:25,rate:1,phase:0};
  assert.throws(()=>toEngineConfig(p,{detector_z_mm:100}), /90/);
});
