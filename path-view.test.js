import test from 'node:test';
import assert from 'node:assert/strict';
import {sliceDistances,OpticalPathView} from './path-view.js';
test('distance slices include both endpoints and reject unsafe sizes',()=>{
  assert.deepEqual(sliceDistances(10,30,3),[10,20,30]);
  for(const args of [[0,30,3],[30,10,3],[10,30,25],[10,30,2.5],[NaN,30,3]])assert.throws(()=>sliceDistances(...args));
});

test('scene overlay requests slices even when path tab is hidden',()=>{
  const state={active:false,el:()=>({checked:true})};
  const wanted=Object.getOwnPropertyDescriptor(OpticalPathView.prototype,'wanted').get;
  assert.equal(wanted.call(state),true);
  state.el=()=>({checked:false});assert.equal(wanted.call(state),false);
  state.active=true;assert.equal(wanted.call(state),true);
});
test('suspending background slices cancels their current revision',()=>{
  const messages=[],state={serial:4,worker:{postMessage:m=>messages.push(m)}};
  OpticalPathView.prototype.suspend.call(state);
  assert.deepEqual(messages,[{type:'cancel',revision:5}]);
});

test('hybrid cancellation reaches both slice workers with the same revision',()=>{
  const gpu=[],cpu=[],state={serial:6,worker:{postMessage:m=>gpu.push(m)},cpuWorker:{postMessage:m=>cpu.push(m)}};
  OpticalPathView.prototype.suspend.call(state);
  assert.deepEqual(gpu,[{type:'cancel',revision:7}]);assert.deepEqual(cpu,gpu);
});

test('idle CUDA takes over a slow CPU tail once',()=>{
 const gpu=[],worker={postMessage:m=>gpu.push(m)},cpuWorker={},state={sliceConfig:OpticalPathView.prototype.sliceConfig,worker,cpuWorker,queue:[],inFlight:new Map([[cpuWorker,300]]),hedged:new Set(),setup:{backend:'hybrid',config:{resolution:128}},slices:[],distances:[300],serial:9,status:{}};
 OpticalPathView.prototype.next.call(state,worker);
 assert.equal(gpu.length,1);assert.equal(gpu[0].backend,'cuda');assert.equal(gpu[0].config.detector_z_mm,300);
 OpticalPathView.prototype.next.call(state,worker);assert.equal(gpu.length,1);
});

test('animation advances once only after the full slice batch completes',()=>{
 let advanced=0;const worker={},cpuWorker={},state={worker,cpuWorker,queue:[],inFlight:new Map(),hedged:new Set(),setup:{backend:'cuda'},slices:[{}],distances:[10,20],status:{},onComplete:()=>advanced++};
 OpticalPathView.prototype.next.call(state,worker);assert.equal(advanced,0);
 state.slices.push({});OpticalPathView.prototype.next.call(state,worker);assert.equal(advanced,1);
 OpticalPathView.prototype.next.call(state,cpuWorker);assert.equal(advanced,1);
});

test('partial next-frame slices do not replace displayed sandwich',()=>{
 let commits=0,advanced=0;const worker={},state={worker,cpuWorker:{},queue:[],inFlight:new Map(),hedged:new Set(),setup:{backend:'cuda'},slices:[{z:1},{z:2}],pendingSlices:[{z:1}],distances:[1,2],status:{},commitSlices(){commits++;this.slices=this.pendingSlices;},onComplete(){advanced++;}};
 OpticalPathView.prototype.next.call(state,worker);assert.equal(commits,0);assert.equal(state.slices.length,2);
 state.pendingSlices.push({z:2});OpticalPathView.prototype.next.call(state,worker);assert.equal(commits,1);assert.equal(advanced,1);
});
