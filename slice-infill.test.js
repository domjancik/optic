import test from 'node:test';
import assert from 'node:assert/strict';
import {sliceInfill} from './slice-infill.js';
test('infill brackets irregular distances and retains endpoints',()=>{
 const p=sliceInfill([1,3,9],2);assert.deepEqual(p.map(x=>x.z),[1,2,3,6,9]);assert.deepEqual(p[3],{z:6,a:1,b:2,mix:.5,weight:.6});
 assert.ok(Math.abs(p.reduce((s,x)=>s+x.weight,0)-3)<1e-10);
});
test('disabled infill preserves measured slices and single slices remain valid',()=>{
 assert.deepEqual(sliceInfill([1,3],1),[{z:1,a:0,b:0,mix:0,weight:1},{z:3,a:1,b:1,mix:0,weight:1}]);assert.equal(sliceInfill([2],8).length,1);assert.deepEqual(sliceInfill([],8),[]);
});
