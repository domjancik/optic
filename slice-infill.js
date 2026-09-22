// Display-only samples: reuse adjacent textures, never allocate simulated maps.
export function sliceInfill(distances,subdivisions=1){
 const steps=Math.max(1,Math.min(16,Math.round(subdivisions)||1)),out=[];
 for(let i=0;i<distances.length;i++){
  out.push({z:distances[i],a:i,b:i,mix:0,weight:1});
  if(i+1<distances.length)for(let j=1;j<steps;j++)out.push({z:distances[i]+(distances[i+1]-distances[i])*j/steps,a:i,b:i+1,mix:j/steps,weight:1});
 }
 for(const p of out)p.weight=distances.length/out.length;
 return out;
}
