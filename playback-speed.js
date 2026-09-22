export function playbackRate(value){return value==null||!Number.isFinite(Number(value))?1:Math.max(.1,Math.min(4,Number(value)));}
// Rebase wall-clock origins so rate changes preserve the current animation phase.
export const retimeStart=(now,start,oldRate,newRate)=>now-(now-start)*oldRate/newRate;
export const playbackTime=(now,start,rate,duration)=>((now-start)*rate/1000)%duration;
export const frameInterval=(fps,rate)=>1000/(fps*rate);
