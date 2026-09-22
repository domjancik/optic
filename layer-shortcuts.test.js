import test from 'node:test';
import assert from 'node:assert/strict';
import { shortcutLayer } from './layer-shortcuts.js';
test('shortcuts count upward from source and follow reordered layers',()=>{
  const layers=[{id:'mask'},{id:'optic'}];
  const key=code=>({code,shiftKey:true});
  assert.equal(shortcutLayer(key('Digit1'),layers),'source');
  assert.equal(shortcutLayer(key('Digit2'),layers),'mask');
  assert.equal(shortcutLayer(key('Digit3'),layers),'optic');
  assert.equal(shortcutLayer(key('Digit2'),[...layers].reverse()),'optic');
  assert.equal(shortcutLayer(key('Digit0'),layers),'screen');
  assert.equal(shortcutLayer(key('Digit9'),layers),null);
  assert.equal(shortcutLayer({code:'Digit2'},layers),null);
  assert.equal(shortcutLayer({...key('Digit2'),ctrlKey:true},layers),null);
});
