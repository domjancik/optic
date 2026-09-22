import {projectScreen,screenRay,axisOffset,planeHit,rotationDelta} from './source-gizmo-math.js';
import {dot,cross,normalise} from './scene-math.js';
const axes={x:[1,0,0],y:[0,1,0],z:[0,0,1]};
const add=(a,b,s=1)=>a.map((v,i)=>v+s*b[i]);
export class SourceGizmo {
 constructor(canvas,callbacks){
  this.canvas=canvas;this.callbacks=callbacks;this.mode='move';
  this.root=document.createElementNS('http://www.w3.org/2000/svg','svg');this.root.classList.add('source-gizmo');this.root.setAttribute('aria-label','Selected projector transform gizmo');canvas.parentElement.append(this.root);
  this.root.onpointerdown=e=>this.begin(e);this.root.onpointermove=e=>this.move(e);
  this.root.onpointerup=e=>this.end(e,false);this.root.onpointercancel=e=>this.end(e,true);
  this.keyHandler=e=>{if(e.key==='Escape'&&this.drag){e.preventDefault();this.end(null,true);}};window.addEventListener('keydown',this.keyHandler);
 }
 update(lights,camera,index,visible){
  this.lights=lights;this.camera=camera;this.index=index;this.root.style.display=visible?'':'none';if(!visible)return;
  const source=lights[index];if(!source)return;const centre=projectScreen(source.position,camera);if(!centre){this.root.replaceChildren();return;}
  this.root.style.left=this.canvas.offsetLeft+'px';this.root.style.top=this.canvas.offsetTop+'px';this.root.setAttribute('width',camera.width);this.root.setAttribute('height',camera.height);this.root.setAttribute('viewBox',`0 0 ${camera.width} ${camera.height}`);
  const distance=dot(source.position.map((v,i)=>v-camera.eye[i]),camera.forward),length=distance*140/(camera.height*1.6);this.length=length;
  let html='';
  if(this.mode==='move'){
   for(const [key,axis]of Object.entries(axes)){const end=projectScreen(add(source.position,axis,length),camera);if(!end)continue;const collapsed=Math.hypot(end[0]-centre[0],end[1]-centre[1])<12;html+=`<g class="gizmo-${key} ${collapsed?'gizmo-faint':''}"><path d="M${centre.join(' ')} L${end.join(' ')}"/><circle data-handle="${key}" cx="${end[0]}" cy="${end[1]}" r="10"><title>Move ${key.toUpperCase()} · Shift fine · Ctrl snap 0.1 m</title></circle><text x="${end[0]+12}" y="${end[1]-8}">${key.toUpperCase()}</text></g>`;}
   html+=`<rect data-handle="plane" x="${centre[0]-7}" y="${centre[1]-7}" width="14" height="14" class="gizmo-plane"><title>Move in view plane</title></rect>`;
  }else{
   const yaw=Math.atan2(source.forward[0],source.forward[2]);
   for(const [key,a,b]of [['yaw',[1,0,0],[0,0,1]],['pitch',[Math.sin(yaw),0,Math.cos(yaw)],[0,1,0]]]){
    const points=Array.from({length:65},(_,i)=>{const angle=i/64*Math.PI*2;return projectScreen(add(add(source.position,a,length*Math.cos(angle)),b,length*Math.sin(angle)),camera);});
    if(points.some(p=>!p))continue;const d=points.map((p,i)=>(i?'L':'M')+p.join(' ')).join(' ');html+=`<path class="gizmo-ring gizmo-${key==='yaw'?'y':'x'}" data-handle="${key}" d="${d}"><title>Rotate ${key} · Shift fine · Ctrl snap 5°</title></path>`;
   }
  }
  this.root.innerHTML=html;
 }
 begin(e){const handle=e.target.dataset.handle;if(!handle||e.button!==0)return;e.stopPropagation();e.preventDefault();const light=this.lights[this.index],rect=this.root.getBoundingClientRect(),pixel=[e.clientX-rect.left,e.clientY-rect.top],camera=structuredClone(this.camera),ray=screenRay(pixel,camera),yaw=Math.atan2(light.forward[0],light.forward[2]),pitch=Math.asin(Math.max(-1,Math.min(1,light.forward[1])));
  const origin=[...light.position],a=handle==='yaw'?[1,0,0]:[Math.sin(yaw),0,Math.cos(yaw)],b=handle==='yaw'?[0,0,1]:[0,1,0],normal=handle==='plane'?camera.forward:normalise(cross(a,b));
  const hit=planeHit(ray,origin,normal),startAngle=hit?Math.atan2(dot(hit.map((v,i)=>v-origin[i]),b),dot(hit.map((v,i)=>v-origin[i]),a)):null;
  this.drag={handle,index:this.index,origin,yaw:yaw*180/Math.PI,pitch:pitch*180/Math.PI,camera,pixel,a,b,normal,hit,startAngle,axisStart:axes[handle]?axisOffset(ray,origin,axes[handle]):null,pointer:e.pointerId};
  this.root.setPointerCapture(e.pointerId);this.callbacks.begin?.();
 }
 move(e){const d=this.drag;if(!d)return;e.stopPropagation();e.preventDefault();const rect=this.root.getBoundingClientRect(),pixel=[e.clientX-rect.left,e.clientY-rect.top],ray=screenRay(pixel,d.camera),fine=e.shiftKey?.1:1,pose={lightX:d.origin[0],lightY:d.origin[1],lightZ:d.origin[2],lightYaw:d.yaw,lightPitch:d.pitch};
  if(axes[d.handle]){const offset=axisOffset(ray,d.origin,axes[d.handle]);if(offset===null||d.axisStart===null)return;let delta=(offset-d.axisStart)*fine;if(e.ctrlKey)delta=Math.round(delta/.1)*.1;const position=add(d.origin,axes[d.handle],delta);['lightX','lightY','lightZ'].forEach((k,i)=>pose[k]=Math.max(-50,Math.min(50,position[i])));}
  else if(d.handle==='plane'){const hit=planeHit(ray,d.origin,d.normal);if(!hit||!d.hit)return;['lightX','lightY','lightZ'].forEach((k,i)=>{let v=d.origin[i]+(hit[i]-d.hit[i])*fine;if(e.ctrlKey)v=Math.round(v/.1)*.1;pose[k]=Math.max(-50,Math.min(50,v));});}
  else {const hit=planeHit(ray,d.origin,d.normal);let delta;if(hit&&d.startAngle!==null){const v=hit.map((v,i)=>v-d.origin[i]);delta=rotationDelta(Math.atan2(dot(v,d.b),dot(v,d.a)),d.startAngle)*fine;}else delta=(pixel[0]-d.pixel[0]-(pixel[1]-d.pixel[1]))*.5*fine;if(e.ctrlKey)delta=Math.round(delta/5)*5;if(d.handle==='yaw')pose.lightYaw=d.yaw-delta;else pose.lightPitch=Math.max(-89,Math.min(89,d.pitch+delta));}
  this.callbacks.change?.(d.index,pose);
 }
 end(e,cancel){const d=this.drag;if(!d)return;this.drag=null;if(this.root.hasPointerCapture(d.pointer))this.root.releasePointerCapture(d.pointer);if(cancel)this.callbacks.change?.(d.index,{lightX:d.origin[0],lightY:d.origin[1],lightZ:d.origin[2],lightYaw:d.yaw,lightPitch:d.pitch});this.callbacks.end?.(cancel);}
}
