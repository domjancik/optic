importScripts('playback-cache.js');
const frames=new PlaybackCache();
let cachePort=null,cacheSerial=0;const cacheRequests=new Map();
function cachedFrame(key){if(!cachePort)return Promise.resolve(frames.get(key));return new Promise(resolve=>{const id=++cacheSerial;cacheRequests.set(id,resolve);cachePort.postMessage({type:'get',id,key});});}
function storeFrame(key,value){if(cachePort)cachePort.postMessage({type:'put',key,value});else frames.put(key,value);}
function decodeMap(text){const raw=atob(text),bytes=new Uint8Array(raw.length);for(let i=0;i<raw.length;i++)bytes[i]=raw.charCodeAt(i);return bytes;}
// HTTP and decoding stay off the UI thread. Cancellation also reaches transport.
let pending=null,running=false,latest=0,activeId=null;
async function cancelActive(){if(activeId)try{await fetch('/api/cancel',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:activeId})});}catch{/* Polling will report connection failures. */}}
onmessage=({data})=>{if(data.type==='cache-port'){cachePort=data.port;cachePort.onmessage=({data:r})=>{cacheRequests.get(r.id)?.(r.value);cacheRequests.delete(r.id);};cachePort.start();return;}latest=data.revision;if(data.type==='cancel'){pending=null;cancelActive();return;}pending=data;if(running)cancelActive();drain();};
async function drain(){
 if(running)return;running=true;
 while(pending){const job=pending;pending=null;
  try{
   const started=performance.now(),key=JSON.stringify(job.config),cached=await cachedFrame(key);
   if(job.revision!==latest)continue;
   if(cached){cached.cache={...cached.cache,hit:true,memory:true,lookup_ms:0};cached.delivery_ms=performance.now()-started;postMessage({type:'result',...cached,id:null,revision:job.revision},cached.colorBuffer?[cached.buffer,cached.colorBuffer]:[cached.buffer]);continue;}
   postMessage({type:'busy',revision:job.revision});
   let response,data;
   for(let attempt=0;attempt<300;attempt++){
    if(job.revision!==latest)break;
    response=await fetch('/api/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(job)});
    data=await response.json();
    if(response.ok||!String(data.error).includes('Compute queue full'))break;
    await new Promise(r=>setTimeout(r,100));
   }
   if(job.revision!==latest)continue;
   if(!response.ok)throw Error(data.error);
   activeId=data.id;if(job.revision!==latest)await cancelActive();
   let state;
   do{state=await(await fetch('/api/jobs/'+data.id)).json();if(state.status==='running')await new Promise(r=>setTimeout(r,20));}while(state.status==='running');
   if(state.status==='cancelled'||job.revision!==latest)continue;
   if(state.status==='error')throw Error(state.error);
   const bytes=decodeMap(state.result.map);delete state.result.map;
   const color=state.result.color_map?decodeMap(state.result.color_map):null;delete state.result.color_map;
   const result={...state.result,timelineTime:job.timelineTime,timelineSignature:job.timelineSignature,buffer:bytes.buffer,colorBuffer:color?.buffer};storeFrame(key,result);result.delivery_ms=performance.now()-started;
   postMessage({type:'result',revision:job.revision,id:data.id,...result},color?[bytes.buffer,color.buffer]:[bytes.buffer]);
  }catch(e){if(job.revision===latest)postMessage({type:'error',revision:job.revision,error:e.message});}
  finally{activeId=null;}
 }
 running=false;
}
