import test from 'node:test';
import assert from 'node:assert/strict';
import {glareSample} from './scene-glare.js';
import {projectorBasis} from './scene-math.js';
const light={...projectorBasis(),position:[0,0,0],gain:1};
test('glare samples only forward illuminated viewing directions',()=>{
 assert.deepEqual(glareSample([0,0,2],light,1,.6),{uv:[.5,.5],strength:.25,facing:1});
 assert.equal(glareSample([0,0,-2],light,1,.6),null);
 const offAxis=glareSample([2,0,2],light,1,.6);assert.equal(offAxis.uv,null);assert.ok(offAxis.facing>0);
 assert.equal(glareSample([0,0,2],{...light,gain:0},1,.6),null);
});
test('glare follows source exposure gain and distance',()=>{
 assert.equal(glareSample([0,0,2],{...light,gain:2},1,.6).strength,.5);
 assert.equal(glareSample([0,0,4],light,1,.6).strength,.0625);
});
