let sequence = 0;
const id = () => `layer-${globalThis.crypto?.randomUUID?.() || ++sequence}`;
const clone = value => structuredClone(value);

export function createProject() {
  return { version: 2, name: 'Untitled optical stack', layers: [makeLayer('optic')], selected: 'source', timeline: { duration: 8, loop: true } };
}

export function makeLayer(type = 'optic') {
  const optic = type === 'optic';
  return {
    id: id(), type, name: optic ? 'Prism ridges' : 'Dot mask', enabled: true, gapBeforeMm: 6,
    kind: optic ? 'prism' : 'multiple', radius_mm: optic ? 13 : 1, thickness_mm: optic ? 2 : .1,
    pitch_mm: optic ? 2 : 4, depth_mm: optic ? .35 : 0, count: 3, angle_deg: 0, x_mm: 0, y_mm: 0,
    rotation: 0, tilt: 0, modulation: {
      rotation: { enabled: false, waveform: 'sine', base: 0, depth: 20, rate: .25, phase: 0 },
      tilt: { enabled: false, waveform: 'sine', base: 0, depth: 2, rate: .25, phase: 0 },
      x: { enabled: false, waveform: 'sine', base: 0, depth: 2, rate: .25, phase: 0 },
      y: { enabled: false, waveform: 'sine', base: 0, depth: 2, rate: .25, phase: 0 },
      radius: { enabled: false, waveform: 'sine', base: optic ? 13 : 1, depth: 1, rate: .25, phase: 0 }
    }
  };
}

export function addLayer(project, type, at = project.layers.length) {
  const next = clone(project); next.layers.splice(Math.max(0, Math.min(at, next.layers.length)), 0, makeLayer(type)); next.selected = next.layers[Math.max(0, Math.min(at, next.layers.length - 1))].id; return next;
}
export function removeLayer(project, layerId) { const next = clone(project); next.layers = next.layers.filter(layer => layer.id !== layerId); next.selected = next.layers[0]?.id || 'source'; return next; }
export function moveLayer(project, layerId, delta) { const next = clone(project), i = next.layers.findIndex(layer => layer.id === layerId), target = i + delta; if (i < 0 || target < 0 || target >= next.layers.length) return next; [next.layers[i], next.layers[target]] = [next.layers[target], next.layers[i]]; return next; }

export function waveform(kind, phase) { const x = ((phase % 1) + 1) % 1; if (kind === 'triangle') return 1 - 4 * Math.abs(x - .5); if (kind === 'ramp') return 2 * x - 1; if (kind === 'noise') { const q = x * 32, i = Math.floor(q), t = q - i, hash = n => Math.sin(n * 12.9898 + 78.233) * .5 + .5, smooth = t * t * (3 - 2 * t); return (hash(i) * (1 - smooth) + hash((i + 1) % 32) * smooth) * 2 - 1; } return Math.sin(x * Math.PI * 2); }
export function poseAt(layer, seconds) { const result = { rotation: layer.rotation, tilt: layer.tilt, x: layer.x_mm, y: layer.y_mm, radius: layer.radius_mm }; for (const [key, mod] of Object.entries(layer.modulation || {})) if (mod.enabled) result[key] = mod.base + mod.depth * waveform(mod.waveform, seconds * mod.rate + mod.phase / 360); return result; }

export function duplicateLayer(project, layerId) {
  const next=clone(project), index=next.layers.findIndex(l=>l.id===layerId);
  if(index<0)return next;
  const copy=clone(next.layers[index]);copy.id=id();copy.name+=' copy';
  next.layers.splice(index+1,0,copy);next.selected=copy.id;return next;
}

export function packLayers(project) {
  let cursor=0;
  return project.layers.map(layer=>{
    const gap=Number(layer.gapBeforeMm);
    if(!Number.isFinite(gap)||gap<.01)throw Error('Layer gaps must be at least 0.01 mm');
    const radiusMod=layer.modulation?.radius, tiltMod=layer.modulation?.tilt;
    const radius=radiusMod?.enabled?Math.abs(radiusMod.base)+Math.abs(radiusMod.depth):layer.radius_mm;
    const tilt=tiltMod?.enabled?Math.abs(tiltMod.base)+Math.abs(tiltMod.depth):Math.abs(layer.tilt);
    let lower=0,upper=0;
    if(layer.type==='optic'){
      if(!Number.isFinite(tilt)||tilt>90)throw Error('Tilt, including modulation depth, must stay within ±90°');
      const sweep=radius*Math.sin(Math.min(90,tilt)*Math.PI/180);
      const low=layer.kind==='shard'?.5:0;
      const high=layer.thickness_mm+(layer.kind==='flat'?0:layer.kind==='shard'?Math.max(.5,layer.depth_mm):layer.depth_mm);
      lower=low+sweep;upper=high+sweep;
    }
    const front=cursor+gap,z=front+lower,back=z+upper;cursor=back;
    return {id:layer.id,layer,z_mm:z,front_mm:front,back_mm:back,gapBeforeMm:gap};
  });
}

export function toEngineConfig(project, base, seconds = 0) {
  const config=clone(base);config.optics=[];config.masks=[];
  for(const slot of packLayers(project)){
    const layer=slot.layer,p=poseAt(layer,seconds);
    if(!layer.enabled)continue;
    if(!Object.values(p).every(Number.isFinite)||p.radius<=0)throw Error('Layer pose must be finite and radius positive');
    if(layer.type==='optic')config.optics.push({kind:layer.kind,radius_mm:p.radius,z_mm:slot.z_mm,thickness_mm:layer.thickness_mm,pitch_mm:layer.pitch_mm,depth_mm:layer.depth_mm,angle_deg:p.rotation,tilt_deg:p.tilt,x_mm:p.x,y_mm:p.y,...(layer.kind==='linear_fresnel'?{focal_mm:layer.focal_mm??300,design_index:layer.design_index??1.49}:{})});
    else config.masks.push({kind:layer.kind,z_mm:slot.z_mm,radius_mm:p.radius,pitch_mm:layer.pitch_mm,count:layer.count,angle_deg:p.rotation+(layer.angle_deg||0),x_mm:p.x,y_mm:p.y});
  }
  delete config.mask;return config;
}
