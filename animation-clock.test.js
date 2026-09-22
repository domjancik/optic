import test from 'node:test';
import assert from 'node:assert/strict';
import { frameTime, frameCount, nextFrameTime } from './animation-clock.js';
test('loops repeat bit-identical times, including fractional duration',()=>{
  const duration=1.37,fps=24,count=frameCount(duration,fps);
  let t=0;const first=[];
  for(let i=0;i<count;i++){first.push(t);t=nextFrameTime(t,duration,fps);}
  assert.equal(t,0);
  for(let i=0;i<count;i++){assert.equal(t,first[i]);t=nextFrameTime(t,duration,fps);}
  assert.equal(frameTime(duration,duration,fps),0);
});

test('fractional duration uses exact FPS steps rather than stretching frames',()=>{
  const duration=1.37,fps=24;
  let t=0;
  for(let i=0;i<frameCount(duration,fps);i++){
    assert.equal(t,i/fps);
    t=nextFrameTime(t,duration,fps);
  }
  assert.equal(t,0);
});
test('scrubbing snaps to the same grid as playback and wraps its quantized loop',()=>{
  assert.equal(frameTime(.51,1.37,24),12/24);
  assert.equal(frameTime(frameCount(1.37,24)/24,1.37,24),0);
});

test('modulated simulation configs are byte-identical on repeated loops and scrub seeks',async()=>{
  const {makeLayer,toEngineConfig}=await import('./layer-state.js');
  const layer=makeLayer('optic');layer.modulation.rotation.enabled=true;
  const project={layers:[layer]},duration=1.37,fps=24,frames=frameCount(duration,fps);
  const configs=[];let t=0;
  for(let loop=0;loop<10;loop++)for(let i=0;i<frames;i++){
    const config=JSON.stringify(toEngineConfig(project,{},t));
    if(!loop)configs.push(config);else assert.equal(config,configs[i]);
    assert.equal(JSON.stringify(toEngineConfig(project,{},frameTime(i/fps+.001,duration,fps))),config);
    t=nextFrameTime(t,duration,fps);
  }
  assert.equal(frameTime(7/24,duration,30),9/30);
});
