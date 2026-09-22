import test from 'node:test';
import assert from 'node:assert/strict';
import { createProject,makeLayer,packLayers } from './layer-state.js';
import { captureOptics,applyOptics,toggleLayerMute } from './optic-presets.js';
test('optics presets restore layers/materials without touching source or scene settings',()=>{
  const p=createProject();p.settings={n550:1.49,dispersion:.004,absorption:0,lightX:3,colorMode:'rgbw',power:1,sceneMode:'model'};
  p.layers.push(makeLayer('mask'));p.layers[1].enabled=false;
  const preset=captureOptics(p,'My optics');
  const target=structuredClone(p);target.settings={...target.settings,n550:1.6,lightX:9,power:2,colorMode:'laser-638'};target.layers=[];
  const restored=applyOptics(target,preset);
  assert.equal(restored.settings.lightX,9);assert.equal(restored.settings.power,2);assert.equal(restored.settings.colorMode,'laser-638');assert.equal(restored.settings.sceneMode,'model');
  assert.equal(restored.settings.n550,1.49);assert.deepEqual(restored.layers,p.layers);
  restored.layers[0].radius_mm=1;assert.notEqual(preset.layers[0].radius_mm,1);
});
test('mute leaves spacing, parameters and selection unchanged',()=>{
  const p=createProject();p.layers.push(makeLayer('optic'));p.selected='source';
  const positions=packLayers(p).map(s=>s.z_mm),next=toggleLayerMute(p,p.layers[0].id);
  assert.equal(next.layers[0].enabled,false);assert.equal(next.selected,'source');assert.deepEqual(packLayers(next).map(s=>s.z_mm),positions);
  assert.deepEqual(toggleLayerMute(next,p.layers[0].id),p);
});
