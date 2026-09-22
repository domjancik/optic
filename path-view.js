import { simulationWorker, cachedBatch } from './playback-store.js';
import { attachNumericControls } from './numeric-controls.js';
// Distance slices use independent physical detector traces through the full stack.
export function sliceDistances(start,end,count){
  if(!Number.isFinite(start)||!Number.isFinite(end)||start<=0||end<=start||!Number.isInteger(count)||count<2||count>24)throw Error('Use positive increasing distances and 2–24 slices.');
  return Array.from({length:count},(_,i)=>start+(end-start)*i/(count-1));
}

export class OpticalPathView {
  constructor(host,getSetup,onSlices=()=>{}){
    this.previewCache=new Map();this.onSlices=onSlices;this.getSetup=getSetup;this.active=false;this.serial=0;this.slices=[];this.yaw=.65;this.pitch=.25;this.zoom=1;this.pan=[0,0];
    this.root=document.createElement('div');this.root.className='path-view';this.root.hidden=true;
    this.root.innerHTML=`<div class="path-controls"><label>From mm<input data-p="from" type="number" step="1"></label><label>To mm<input data-p="to" type="number" step="1"></label><label>Slices<input data-p="count" type="number" min="2" max="24" value="8"></label><label>Opacity<input data-p="opacity" type="number" min="0.05" max="1" step="0.05" value="0.65"></label><label>Spacing<input data-p="spacing" type="number" min="0.1" max="10" step="0.1" value="1"></label><label>Ray paths<input data-p="rays" type="checkbox"></label><button data-p="run">Sample</button><button data-p="reset">Reset</button><button data-p="expand">Expand</button><select data-p="slice" aria-label="Inspect distance slice"><option value="-1">Sandwich</option></select></div><canvas aria-label="Optical path sandwich. Drag to orbit, Shift or right drag to pan, wheel to zoom."></canvas><p class="path-status" role="status"></p>`;
    host.append(this.root);this.canvas=this.root.querySelector('canvas');this.ctx=this.canvas.getContext('2d');
    this.el=k=>k==='scene'?document.getElementById('showSandwich'):this.root.querySelector(`[data-p="${k}"]`);this.status=this.root.querySelector('.path-status');
    this.worker=simulationWorker();this.cpuWorker=simulationWorker();
    for(const worker of [this.worker,this.cpuWorker])worker.onmessage=({data:r})=>this.receive(r,worker);
    this.worker.onerror=e=>{this.status.textContent=e.message;};
    this.el('expand').onclick=()=>{this.root.classList.toggle('expanded');this.el('expand').textContent=this.root.classList.contains('expanded')?'Restore':'Expand';this.draw();};
    this.el('run').onclick=()=>this.run();this.el('reset').onclick=()=>{this.yaw=.65;this.pitch=.25;this.zoom=1;this.pan=[0,0];this.el('slice').value='-1';this.draw();};
    for(const k of ['from','to','count'])this.el(k).onchange=()=>this.run();
    for(const k of ['opacity','spacing','slice','rays'])this.el(k).oninput=()=>{this.publish();this.draw();};
    attachNumericControls(this.root);
    let drag=null;this.canvas.oncontextmenu=e=>e.preventDefault();
    this.canvas.onpointerdown=e=>{drag=[e.clientX,e.clientY];this.canvas.setPointerCapture(e.pointerId);};
    this.canvas.onpointerup=this.canvas.onpointercancel=()=>drag=null;
    this.canvas.onpointermove=e=>{if(!drag)return;const dx=e.clientX-drag[0],dy=e.clientY-drag[1];drag=[e.clientX,e.clientY];if(e.shiftKey||(e.buttons&6)){this.pan[0]+=dx;this.pan[1]+=dy;}else{this.yaw+=dx*.008;this.pitch=Math.max(-1.4,Math.min(1.4,this.pitch+dy*.008));}this.draw();};
    this.canvas.onwheel=e=>{e.preventDefault();this.zoom=Math.max(.2,Math.min(8,this.zoom*Math.exp(-e.deltaY*.001)));this.draw();};
    this.observer=new ResizeObserver(()=>this.draw());this.observer.observe(this.root);
  }
  publish(){if(this.setup)this.onSlices(this.slices,this.setup.config.detector_size_mm,this.el('scene').checked,Math.max(0,Math.min(1,Number(document.getElementById('sandwichBrightness').value))));}
  get wanted(){return this.active||this.el('scene').checked;}
  suspend(){clearTimeout(this.timer);this.serial++;for(const worker of [this.worker,this.cpuWorker])worker?.postMessage({type:'cancel',revision:this.serial});}
  show(){document.body.classList.add('path-mode');this.active=true;this.root.hidden=false;this.run();}
  hide(){document.body.classList.remove('path-mode');this.active=false;this.root.hidden=true;if(!this.wanted)this.suspend();}
  invalidate(immediate=false){if(!this.wanted){this.slices=[];this.publish();return;}this.serial++;for(const worker of [this.worker,this.cpuWorker])worker?.postMessage({type:'cancel',revision:this.serial});clearTimeout(this.timer);if(immediate)this.run();else this.timer=setTimeout(()=>this.run(),180);}
  refreshExposure(){if(!this.slices.length)return;for(const s of this.slices)s.image=this.image(s);this.publish();this.draw();}
  async run(){
    clearTimeout(this.timer);this.serial++;for(const worker of [this.worker,this.cpuWorker])worker?.postMessage({type:'cancel',revision:this.serial});
    try{
      this.setup=this.getSetup();const {config:c,slots}=this.setup;
      const last=Math.max(0,...slots.map(s=>s.back_mm));
      if(!this.el('from').value)this.el('from').value='0.1';
      if(!this.el('to').value)this.el('to').value=Math.max(c.detector_z_mm,last+10);
      this.distances=sliceDistances(+this.el('from').value,+this.el('to').value,+this.el('count').value);
      this.distances=this.distances.filter(z=>!slots.some(s=>s.layer.enabled&&z>=s.front_mm-.02&&z<=s.back_mm+.02));
      if(!this.distances.length)throw Error('Every slice intersects an optical layer. Change the distance range.');
      this.completed=false;this.reused=0;this.pendingSlices=[];this.queue=[];this.inFlight=new Map();this.hedged=new Set();const serial=this.serial;this.status.textContent='Loading complete slice frame…';
      const cached=await cachedBatch(this.distances.map(z=>this.sliceConfig(z)));if(serial!==this.serial)return;
      for(let i=0;i<cached.length;i++){if(cached[i])this.pendingSlices.push(this.makeSlice(cached[i]));else this.queue.push(this.distances[i]);}
      this.next(this.worker);if(this.setup.backend==='hybrid')this.next(this.cpuWorker);
    }catch(e){this.status.textContent=e.message;this.onError?.(e.message);}
  }
  next(worker=this.worker){
    const cpu=worker===this.cpuWorker;
    let z;
    if(!this.queue.length){
      const tail=this.inFlight.get(this.cpuWorker);
      if(!cpu&&this.setup.backend==='hybrid'&&tail!==undefined&&!this.hedged.has(tail)){
        z=tail;this.hedged.add(z);
      }else{
        if((this.pendingSlices||this.slices).length===this.distances.length&&!this.completed){this.completed=true;if(this.pendingSlices)this.commitSlices();this.status.textContent=`${this.slices.length} free-space slices · ${this.setup.backend} · ${this.reused||0} reused ray sets · additive · planes inside layers skipped.`;this.onComplete?.();}
        return;
      }
    }else z=cpu?this.queue.pop():this.queue.shift();
    this.inFlight.set(worker,z);
    this.status.textContent=`${(this.pendingSlices||this.slices).length}/${this.distances.length} slices ready · ${this.setup.backend==='hybrid'?'CPU + CUDA in parallel':this.setup.backend}…`;
    const backend=this.setup.backend==='hybrid'?(cpu?'cpu':'cuda'):this.setup.backend;
    worker.postMessage({revision:this.serial,backend,timelineTime:this.setup.timelineTime,timelineSignature:this.setup.timelineSignature,config:this.sliceConfig(z)});
  }
  receive(r,worker=this.worker){if(!this.wanted||r.revision!==this.serial||r.type==='busy')return;if(r.type==='error'){this.status.textContent=r.error;this.suspend();this.onError?.(r.error);return;}
    this.inFlight.delete(worker);
    if((this.pendingSlices||this.slices).some(s=>s.z===r.config.detector_z_mm))return;
    for(const [other,z] of this.inFlight)if(z===r.config.detector_z_mm){other.postMessage({type:'cancel',revision:this.serial});this.inFlight.delete(other);}
    if(r.metrics?.outgoing_reused)this.reused++;
    this.pendingSlices.push(this.makeSlice(r));this.next(worker);
  }
  sliceConfig(z){return {...this.setup.config,path_samples:true,resolution:Math.min(512,this.setup.config.resolution),detector_z_mm:z};}
  makeSlice(r){
    const s={rays:r.ray_samples||[],z:r.config.detector_z_mm,res:r.config.resolution,mono:new Float32Array(r.buffer),color:r.colorBuffer?new Float32Array(r.colorBuffer):null};const imageKey=JSON.stringify([r.config,this.getSetup().exposure]);s.image=this.previewCache.get(imageKey);if(!s.image){s.image=this.image(s);this.previewCache.set(imageKey,s.image);let bytes=0;for(const image of this.previewCache.values())bytes+=image.width*image.height*4;while(bytes>64*1024*1024){const key=this.previewCache.keys().next().value,image=this.previewCache.get(key);bytes-=image.width*image.height*4;this.previewCache.delete(key);}}else{this.previewCache.delete(imageKey);this.previewCache.set(imageKey,s.image);}return s;
  }
  commitSlices(){
    this.slices=this.pendingSlices.sort((a,b)=>a.z-b.z);this.publish();
    const selected=this.el('slice').value;this.el('slice').innerHTML='<option value="-1">Sandwich</option>';
    for(const slice of this.slices){const option=document.createElement('option');option.value=slice.z;option.textContent=`Inspect ${slice.z.toFixed(2)} mm`;this.el('slice').append(option);}
    this.el('slice').value=selected;this.draw();
  }
  image(s){
    const canvas=document.createElement('canvas');canvas.width=canvas.height=s.res;const ctx=canvas.getContext('2d'),im=ctx.createImageData(s.res,s.res),exposure=.08*2**this.getSetup().exposure;
    for(let y=0;y<s.res;y++)for(let x=0;x<s.res;x++){const i=y*s.res+x,j=((s.res-1-y)*s.res+x)*4,values=s.color?[s.color[i*4],s.color[i*4+1],s.color[i*4+2]]:[s.mono[i],s.mono[i],s.mono[i]],peak=Math.max(1e-12,...values),tone=1-Math.exp(-peak*exposure);for(let k=0;k<3;k++)im.data[j+k]=255*Math.pow(Math.max(0,values[k]/peak*tone),1/2.2);im.data[j+3]=255;}
    ctx.putImageData(im,0,0);return canvas;
  }
  draw(){
    if(!this.active||!this.setup)return;const c=this.canvas,ctx=this.ctx,w=c.clientWidth,h=c.clientHeight;if(!w||!h)return;c.width=w;c.height=h;ctx.fillStyle='#081111';ctx.fillRect(0,0,w,h);
    const selected=+this.el('slice').value;if(selected>=0&&this.slices.find(s=>s.z===selected)){const s=this.slices.find(s=>s.z===selected),side=Math.min(w,h)*.88;ctx.drawImage(s.image,(w-side)/2,(h-side)/2,side,side);ctx.fillStyle='#bcebdd';ctx.fillText(`${s.z.toFixed(2)} mm · ${this.setup.config.detector_size_mm} mm field · native ${s.res}² map`,12,20);return;}
    const end=this.distances?.at(-1)||1,field=this.setup.config.detector_size_mm,spacing=Math.max(.1,Math.min(10,+this.el('spacing').value||1)),scale=Math.min(w/2.5,h/1.9)*this.zoom;
    const project=(x,y,z)=>{x=x/field;y=y/field;z=(z/end-.5)*1.7*spacing;const a=x*Math.cos(this.yaw)+z*Math.sin(this.yaw),d=z*Math.cos(this.yaw)-x*Math.sin(this.yaw),b=y*Math.cos(this.pitch)-d*Math.sin(this.pitch);return [w/2+a*scale+this.pan[0],h/2-b*scale+this.pan[1],d*Math.cos(this.pitch)+y*Math.sin(this.pitch)];};
    const planes=this.slices.map((s,i)=>({z:s.z,size:field,image:s.image,label:`${s.z.toFixed(1)} mm`,slice:i}));
    planes.push({z:0,size:this.setup.config.source_radius_mm*2,label:'Source',color:'#e8bd6d'});
    for(const slot of this.setup.slots)planes.push({z:slot.z_mm,size:slot.layer.radius_mm*2,label:slot.layer.name+(slot.layer.enabled?'':' (muted)'),layer:slot.layer,color:slot.layer.type==='mask'?'#cc9b72':'#62c9b5'});
    if(this.el('rays').checked){ctx.strokeStyle='#e5cc8366';ctx.lineWidth=.7;for(let i=1;i<this.slices.length;i++){const a=this.slices[i-1],b=this.slices[i],lookup=new Map(a.rays.map(r=>[r[0],r]));if(this.setup.slots.some(s=>s.layer.enabled&&s.back_mm>a.z&&s.front_mm<b.z))continue;for(const ray of b.rays){const prev=lookup.get(ray[0]);if(!prev)continue;const p=project(prev[1],prev[2],a.z),q=project(ray[1],ray[2],b.z);ctx.beginPath();ctx.moveTo(p[0],p[1]);ctx.lineTo(q[0],q[1]);ctx.stroke();}}}
    planes.sort((a,b)=>project(0,0,b.z)[2]-project(0,0,a.z)[2]);
    for(const plane of planes){const r=plane.size/2,point=(x,y)=>{const l=plane.layer;if(!l)return project(x,y,plane.z);const a=(l.rotation||0)*Math.PI/180,t=(l.tilt||0)*Math.PI/180,u=x*Math.cos(a)-y*Math.sin(a),v=x*Math.sin(a)+y*Math.cos(a);return project(u+(l.x_mm||0),v*Math.cos(t)+(l.y_mm||0),plane.z+v*Math.sin(t));},a=point(-r,r),b=point(r,r),d=point(-r,-r),e=point(r,-r);ctx.save();ctx.globalAlpha=plane.image?Math.max(.05,Math.min(1,+this.el('opacity').value||.65)):1;
      if(plane.image){ctx.globalCompositeOperation='lighter';const n=plane.image.width;ctx.setTransform((b[0]-a[0])/n,(b[1]-a[1])/n,(d[0]-a[0])/n,(d[1]-a[1])/n,a[0],a[1]);ctx.drawImage(plane.image,0,0);ctx.resetTransform();ctx.globalCompositeOperation='source-over';}
      ctx.strokeStyle=plane.color||'#69978a';ctx.beginPath();ctx.moveTo(...a.slice(0,2));for(const p of [b,e,d,a])ctx.lineTo(...p.slice(0,2));ctx.stroke();ctx.globalAlpha=1;ctx.fillStyle=plane.color||'#b3d6cd';ctx.fillText(plane.label,plane.image?e[0]+4:b[0]+4,plane.image?e[1]+12+(plane.slice%3)*10:b[1]-4);ctx.restore();
    }
    ctx.fillStyle='#8eb4a8';ctx.fillText('Source + layer envelopes; traced free-space irradiance slices',12,h-12);
  }
}
