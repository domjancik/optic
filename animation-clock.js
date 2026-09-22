export const frameCount=(duration,fps)=>Math.max(1,Math.round(duration*fps));
// Canonical integer frame indices keep poses identical across scrubbing and loops.
export function frameTime(time,duration,fps){const count=frameCount(duration,fps);return (((Math.round(time*fps)%count)+count)%count)/fps;}
export function nextFrameTime(time,duration,fps){const count=frameCount(duration,fps);return ((Math.round(time*fps)+1)%count)/fps;}
