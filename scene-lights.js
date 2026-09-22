import {waveform} from './layer-state.js';
import {projectorBasis} from './scene-math.js';
export const lightPoseKeys=['lightX','lightY','lightZ','lightYaw','lightPitch'];
export function ensureSceneSources(project){
 if(!project.sceneSources?.length)project.sceneSources=[{name:'Projector 1',enabled:true,exposure:0,...Object.fromEntries(lightPoseKeys.map(k=>[k,project.settings[k]||0])),modulation:{exposure:{enabled:false,waveform:'sine',base:0,depth:1,rate:.25,phase:0}}}];
 return project.sceneSources;
}
export function sceneExposureAt(source,time){const m=source.modulation.exposure;return Math.max(-24,Math.min(12,m.enabled?m.base+m.depth*waveform(m.waveform,time*m.rate+m.phase/360):source.exposure));}
export function sceneLightsAt(project,time){return ensureSceneSources(project).slice(0,8).map((source,index)=>{
 const pose=index===0?{...source,...Object.fromEntries(lightPoseKeys.map(k=>[k,project.settings[k]??source[k]]))}:source;
 return {...projectorBasis(pose.lightYaw,pose.lightPitch),position:[pose.lightX,pose.lightY,pose.lightZ],gain:source.enabled?2**sceneExposureAt(source,time):0};
});}
