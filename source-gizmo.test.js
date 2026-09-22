import test from 'node:test';
import assert from 'node:assert/strict';
import {projectScreen,screenRay,axisOffset,planeHit,rotationDelta} from './source-gizmo-math.js';
const camera={eye:[0,0,-5],forward:[0,0,1],right:[1,0,0],up:[0,1,0],width:800,height:600};
test('screen projection and rays agree at source position',()=>{
 const p=projectScreen([1,0,0],camera),ray=screenRay(p,camera);
 const hit=planeHit(ray,[0,0,0],[0,0,1]);assert.ok(Math.abs(hit[0]-1)<1e-9);assert.equal(hit[2],0);
});
test('axis dragging moves only along selected world axis',()=>{
 const ray=screenRay(projectScreen([2,0,0],camera),camera);
 assert.ok(Math.abs(axisOffset(ray,[0,0,0],[1,0,0])-2)<1e-9);
 assert.equal(axisOffset(screenRay([400,300],camera),[0,0,0],[0,0,1]),null);
});
test('rotation wraps smoothly across the signed angle boundary',()=>{
 assert.ok(Math.abs(rotationDelta(-179*Math.PI/180,179*Math.PI/180)-2)<1e-9);
});
