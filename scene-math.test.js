import assert from 'node:assert/strict';
import test from 'node:test';
import { blenderToPreview, projectorBasis, projectPoint } from './scene-math.js';

test('converts Blender Z-up coordinates to preview Y-up', () => {
  assert.deepEqual(blenderToPreview([2, 3, 4]), [2, 4, -3]);
  assert.deepEqual(blenderToPreview([0, 0, 1]), [0, 1, 0]);
});

test('projector forward direction follows yaw and pitch in degrees', () => {
  assert.deepEqual(projectorBasis(0, 0).forward.map(v => Math.round(v)), [0, 0, 1]);
  assert.equal(Math.round(projectorBasis(90, 0).forward[0]), 1);
});

test('projects only points in front of the local optical axis', () => {
  const pose = { position: [0, 0, 0], ...projectorBasis(0, 0) };
  assert.deepEqual(projectPoint([0, 0, 2], pose, 1, 2), [.5, .5]);
  assert.equal(projectPoint([0, 0, -2], pose, 1, 2), null);
});
