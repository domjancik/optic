import test from 'node:test';
import assert from 'node:assert/strict';
import './playback-cache.js';
test('decoded frame cache survives transferred copies and evicts least recently used',()=>{
 const cache=new globalThis.PlaybackCache(8216);
 const frame={buffer:new Uint8Array([1,2,3,4,5,6,7,8]).buffer};
 cache.put('a',frame);cache.put('b',frame);
 const hit=cache.get('a');structuredClone(hit,{transfer:[hit.buffer]});
 assert.equal(cache.get('a').buffer.byteLength,8);
 cache.put('c',frame);assert.equal(cache.get('b'),null);
 assert.equal(cache.bytes,8216);
});
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
test('worker repeat frame bypasses HTTP and retains transferred maps',async()=>{
 let requests=0,done;
 const context=vm.createContext({performance,structuredClone,Uint8Array,atob,setTimeout,console,
 fetch:async url=>{requests++;return {ok:true,json:async()=>url==='/api/jobs'?{id:'job'}:{status:'complete',result:{config:{rays:100},map:btoa('abcd'),metrics:{backend:'cpu'},cache:{hit:true}}}};},
 postMessage:value=>{if(value.type==='result')done(value);}});
 context.importScripts=()=>vm.runInContext(readFileSync(new URL('./playback-cache.js',import.meta.url),'utf8'),context);
 vm.runInContext(readFileSync(new URL('./live-worker.js',import.meta.url),'utf8'),context);
 const send=revision=>new Promise(resolve=>{done=resolve;context.onmessage({data:{revision,config:{rays:100},backend:'cuda'}});});
 const first=await send(1);assert.equal(first.buffer.byteLength,4);
 await new Promise(resolve=>setTimeout(resolve,0));
 const second=await send(2);assert.equal(second.cache.memory,true);assert.equal(second.id,null);assert.equal(second.buffer.byteLength,4);assert.equal(requests,2);
});
test('reducing cache budget evicts immediately and increasing retains entries',()=>{
 const cache=new PlaybackCache(20000),frame={buffer:new ArrayBuffer(8)};
 cache.put('a',frame);cache.put('b',frame);cache.setLimit(4108);
 assert.equal(cache.get('a'),null);assert.ok(cache.get('b'));assert.equal(cache.bytes,4108);
 cache.setLimit(20000);assert.ok(cache.get('b'));
});
test('central store shares frames between worker ports and reports eviction',()=>{
 const updates=[],replies=[];
 const context=vm.createContext({structuredClone,console,postMessage:s=>updates.push(s)});
 context.importScripts=()=>vm.runInContext(readFileSync(new URL('./playback-cache.js',import.meta.url),'utf8'),context);
 vm.runInContext(readFileSync(new URL('./playback-store-worker.js',import.meta.url),'utf8'),context);
 const ports=[0,1].map(()=>({start(){},postMessage:r=>replies.push(r)}));
 for(const port of ports)context.onmessage({data:{port}});
 ports[0].onmessage({data:{type:'put',key:'frame',value:{buffer:new ArrayBuffer(8),config:{},timelineTime:.5,timelineSignature:'scene'}}});
 ports[1].onmessage({data:{type:'get',key:'frame',id:1}});
 assert.equal(replies[0].value.buffer.byteLength,8);
 assert.equal(updates.at(-1).frames[0].time,.5);
 context.onmessage({data:{type:'budget',bytes:0}});
 assert.equal(updates.at(-1).bytes,0);assert.equal(updates.at(-1).frames.length,0);
});
test('central batch fetch returns all resident slices and explicit misses together',()=>{
 const replies=[];const context=vm.createContext({structuredClone,console,postMessage:s=>replies.push(s)});
 context.importScripts=()=>vm.runInContext(readFileSync(new URL('./playback-cache.js',import.meta.url),'utf8'),context);
 vm.runInContext(readFileSync(new URL('./playback-store-worker.js',import.meta.url),'utf8'),context);
 const port={start(){},postMessage(){}};context.onmessage({data:{port}});
 port.onmessage({data:{type:'put',key:'a',value:{buffer:new ArrayBuffer(8),config:{}}}});
 context.onmessage({data:{type:'batch',id:42,keys:['a','missing']}});
 assert.equal(replies.at(-1).id,42);assert.equal(replies.at(-1).values[0].buffer.byteLength,8);assert.equal(replies.at(-1).values[1],null);
});
