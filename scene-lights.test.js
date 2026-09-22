import test from 'node:test';
import assert from 'node:assert/strict';
import {ensureSceneSources,sceneLightsAt,sceneExposureAt} from './scene-lights.js';
import {createProject,toEngineConfig} from './layer-state.js';
test('scene instances preserve original source position and never change optical configuration',()=>{
 const p=createProject();p.settings={lightX:2,lightY:3,lightZ:4,lightYaw:15,lightPitch:8};
 const before=toEngineConfig(p,{},0);ensureSceneSources(p);
 assert.deepEqual(sceneLightsAt(p,0)[0].position,[2,3,4]);
 const extra=structuredClone(p.sceneSources[0]);extra.lightX=7;extra.exposure=2;p.sceneSources.push(extra);
 const lights=sceneLightsAt(p,0);assert.equal(lights.length,2);assert.equal(lights[1].gain,4);assert.equal(lights[1].position[0],7);
 assert.deepEqual(toEngineConfig(p,{},0),before);
});
test('brightness uses the existing waveform phase rate base and depth in EV',()=>{
 const p=createProject();p.settings={};ensureSceneSources(p);const source=p.sceneSources[0];
 source.modulation.exposure={enabled:true,waveform:'sine',base:-1,depth:2,rate:1,phase:0};
 assert.equal(sceneExposureAt(source,.25),1);assert.equal(sceneLightsAt(p,.25)[0].gain,2);
 source.enabled=false;assert.equal(sceneLightsAt(p,.25)[0].gain,0);
});
