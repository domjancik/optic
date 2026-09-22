import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeSettings } from './settings-state.js';
test('migrates persisted numerical strings without changing selected values',()=>{
  assert.deepEqual(normalizeSettings({rays:'2000000',resolution:'512',backend:'cpu'},{rays:500000,resolution:256,backend:'cuda'}),{rays:2000000,resolution:512,backend:'cpu'});
});
test('invalid numeric settings give a field-specific message',()=>{
  for(const value of ['',null,'many',Infinity])assert.throws(()=>normalizeSettings({rays:value},{rays:500000}),/rays.*finite number/);
});
