const rad = degrees => degrees * Math.PI / 180;
export const blenderToPreview = ([x, y, z]) => [x, z, y === 0 ? 0 : -y];
export const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
export const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
export const normalise = value => { const size = Math.hypot(...value) || 1; return value.map(part => part / size); };

export function projectorBasis(yawDegrees = 0, pitchDegrees = 0) {
  const yaw = rad(yawDegrees), pitch = rad(pitchDegrees);
  const forward = normalise([Math.sin(yaw) * Math.cos(pitch), Math.sin(pitch), Math.cos(yaw) * Math.cos(pitch)]);
  const right = normalise(cross([0, 1, 0], forward));
  return { forward, right, up: normalise(cross(forward, right)) };
}

/** Maps a world point to detector UV; behind-source points cannot receive light. */
export function projectPoint(point, pose, distanceM, fieldM) {
  const relative = point.map((value, index) => value - pose.position[index]);
  const axial = dot(relative, pose.forward);
  if (axial <= 1e-7) return null;
  const x = dot(relative, pose.right) * distanceM / (axial * fieldM) + .5;
  const y = dot(relative, pose.up) * distanceM / (axial * fieldM) + .5;
  return [x, y];
}

export function fitFromBounds(bounds) {
  const min = blenderToPreview(bounds.min), max = blenderToPreview(bounds.max);
  const center = min.map((value, index) => (value + max[index]) / 2);
  const radius = Math.max(.1, Math.hypot(max[0] - min[0], max[1] - min[1], max[2] - min[2]) / 2);
  return { center, radius, yaw: .55, pitch: .28, zoom: 1.5 };
}
