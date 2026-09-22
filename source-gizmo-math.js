import {dot,normalise} from './scene-math.js';
const sub=(a,b)=>a.map((v,i)=>v-b[i]);
export function projectScreen(point,camera){const q=sub(point,camera.eye),z=dot(q,camera.forward);if(z<=.001)return null;return [(dot(q,camera.right)*1.6/(camera.width/camera.height)/z*.5+.5)*camera.width,(.5-dot(q,camera.up)*1.6/z*.5)*camera.height];}
export function screenRay([x,y],c){const sx=(x/c.width*2-1)*(c.width/c.height)/1.6,sy=(1-y/c.height*2)/1.6;return {origin:c.eye,direction:normalise(c.forward.map((v,i)=>v+sx*c.right[i]+sy*c.up[i]))};}
export function planeHit(ray,origin,normal){const den=dot(ray.direction,normal);if(Math.abs(den)<1e-5)return null;const t=dot(sub(origin,ray.origin),normal)/den;if(t<0)return null;return ray.origin.map((v,i)=>v+t*ray.direction[i]);}
export function axisOffset(ray,origin,axis){const w=sub(ray.origin,origin),b=dot(ray.direction,axis),den=1-b*b;if(den<1e-5)return null;return (dot(w,axis)-b*dot(w,ray.direction))/den;}
export function rotationDelta(angle,start){return Math.atan2(Math.sin(angle-start),Math.cos(angle-start))*180/Math.PI;}
