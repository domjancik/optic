import test from 'node:test';
import assert from 'node:assert/strict';
import {playbackRate, retimeStart, playbackTime, frameInterval} from './playback-speed.js';
import {frameCount,nextFrameTime} from './animation-clock.js';
test('speed changes cadence without changing the canonical frame set',()=>{
 const frames=frameCount(8,48);
 for(const rate of [.1,.5,1,2,4]){
  assert.equal(frameInterval(48,rate)*frames,8000/rate);
  let t=0;for(let i=0;i<frames;i++){assert.equal(t,i/48);t=nextFrameTime(t,8,48);}assert.equal(t,0);
 }
});
test('changing speed preserves animation phase and then advances at new speed',()=>{
 const start=retimeStart(5000,1000,1,2);
 assert.equal(playbackTime(5000,start,2,8),4);
 assert.equal(playbackTime(6000,start,2,8),6);
 assert.equal(playbackTime(7000,start,2,8),0);
 assert.equal(retimeStart(5000,start,2,.5),-3000);
});
test('saved speed normalizes invalid values and enforces bounds',()=>{
 for(const value of [undefined,null,NaN,'no'])assert.equal(playbackRate(value),1);
 assert.equal(playbackRate(.01),.1);assert.equal(playbackRate(100),4);assert.equal(playbackRate('0.5'),.5);
});

test('speed does not alter modulated optical configurations',async()=>{
 const {makeLayer,toEngineConfig}=await import('./layer-state.js');
 const layer=makeLayer('optic');layer.modulation.rotation.enabled=true;
 const project={layers:[layer],timeline:{duration:8,speed:1}};
 const baseline=JSON.stringify(toEngineConfig(project,{},2/48));
 for(const speed of [.1,.5,2,4]){project.timeline.speed=speed;assert.equal(JSON.stringify(toEngineConfig(project,{},2/48)),baseline);}
});
