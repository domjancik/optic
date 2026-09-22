let store=null,listener=()=>{},serial=0;const requests=new Map();
function getStore(){if(!store){store=new Worker('playback-store-worker.js');store.onmessage=({data})=>{if(data.id){requests.get(data.id)?.(data.values);requests.delete(data.id);}else listener(data);};}return store;}
export function onPlaybackCache(callback){listener=callback;}
export function setPlaybackBudget(mib){getStore().postMessage({type:'budget',bytes:mib*1024**2});}
export function simulationWorker(){
 const worker=new Worker('live-worker.js'),channel=new MessageChannel();
 getStore().postMessage({port:channel.port1},[channel.port1]);
 worker.postMessage({type:'cache-port',port:channel.port2},[channel.port2]);
 return worker;
}

export function cachedBatch(configs){return new Promise(resolve=>{const id=++serial;requests.set(id,resolve);getStore().postMessage({type:'batch',id,keys:configs.map(c=>JSON.stringify(c))});});}
