import { packLayers } from './layer-state.js';
const materialKeys=['n550','dispersion','absorption'];
export function captureOptics(project,name){
  name=name.trim();if(!name||name.length>80)throw Error('Use a preset name of 1–80 characters.');
  return {version:1,name,layers:structuredClone(project.layers),materials:Object.fromEntries(materialKeys.map(key=>[key,project.settings[key]]))};
}
export function applyOptics(project,preset){
  if(preset.version!==1||!Array.isArray(preset.layers))throw Error('Invalid optics preset.');
  const next=structuredClone(project);next.layers=structuredClone(preset.layers);
  for(const key of materialKeys){if(!Number.isFinite(preset.materials?.[key]))throw Error('Invalid preset material: '+key);next.settings[key]=preset.materials[key];}
  packLayers(next);
  if(!['source','screen','scene'].includes(next.selected)&&!next.layers.some(l=>l.id===next.selected))next.selected=next.layers[0]?.id||'source';
  return next;
}
export function toggleLayerMute(project,id){
  const next=structuredClone(project),layer=next.layers.find(l=>l.id===id);
  if(layer)layer.enabled=!layer.enabled;
  return next;
}
