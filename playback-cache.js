// Worker-local bounded decoded maps. Transfers always use copies of retained data.
globalThis.PlaybackCache=class {
 constructor(limit=128*1024*1024){this.limit=limit;this.bytes=0;this.entries=new Map();}
 setLimit(limit){this.limit=Math.max(0,limit);while(this.bytes>this.limit){const key=this.entries.keys().next().value;this.bytes-=this.entries.get(key).size;this.entries.delete(key);}}
 get(key){const entry=this.entries.get(key);if(!entry)return null;this.entries.delete(key);this.entries.set(key,entry);return structuredClone(entry.value);}
 put(key,value){const size=value.buffer.byteLength+(value.colorBuffer?.byteLength||0)+JSON.stringify(value.ray_samples||[]).length*2+4096;
  if(size>this.limit)return;
  if(this.entries.has(key)){this.bytes-=this.entries.get(key).size;this.entries.delete(key);}
  while(this.bytes+size>this.limit){const oldest=this.entries.keys().next().value;this.bytes-=this.entries.get(oldest).size;this.entries.delete(oldest);}
  this.entries.set(key,{size,value:structuredClone(value)});this.bytes+=size;
 }
};
