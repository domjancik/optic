importScripts('playback-cache.js');
const cache=new PlaybackCache(1024**3);
function stats(){postMessage({bytes:cache.bytes,frames:[...cache.entries.values()].map(e=>({time:e.value.timelineTime,key:e.value.timelineSignature,slice:e.value.config.path_samples?e.value.config.detector_z_mm:null}))});}
onmessage=({data})=>{
 if(data.type==='batch'){const values=data.keys.map(key=>cache.get(key)),transfer=values.flatMap(v=>v?(v.colorBuffer?[v.buffer,v.colorBuffer]:[v.buffer]):[]);postMessage({id:data.id,values},transfer);return;}
 if(data.type==='budget'){cache.setLimit(data.bytes);stats();return;}
 const port=data.port;
 port.onmessage=({data:m})=>{
  if(m.type==='get'){const value=cache.get(m.key);port.postMessage({id:m.id,value},value?(value.colorBuffer?[value.buffer,value.colorBuffer]:[value.buffer]):[]);}
  else if(m.type==='put'){cache.put(m.key,m.value);stats();}
 };port.start();
};
