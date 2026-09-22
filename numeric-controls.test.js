import assert from 'node:assert/strict';
import test from 'node:test';
import { clamp, decimalPlaces, stepNumericValue } from './numeric-controls.js';

test('clamp respects finite bounds and keeps an in-range number', () => {
  assert.equal(clamp(11, 0, 10), 10);
  assert.equal(clamp(-1, 0, 10), 0);
  assert.equal(clamp(4.25, 0, 10), 4.25);
});

test('stepNumericValue preserves decimal precision and clamps results', () => {
  assert.equal(decimalPlaces('.001'), 3);
  assert.equal(stepNumericValue(.005, .001, -1, 0, 1), .004);
  assert.equal(stepNumericValue(.999, .001, 1, 0, 1), 1);
});

test('stepNumericValue uses shift for fine and control for coarse increments', () => {
  assert.equal(stepNumericValue(10, .2, 1, 0, 20, { shiftKey: true }), 10.02);
  assert.equal(stepNumericValue(10, .2, 1, 0, 20, { ctrlKey: true }), 12);
});
