import {projectPoint,dot} from './scene-math.js';
export function glareSample(eye,light,distance,field){
 if(light.gain<=0)return null;
 const uv=projectPoint(eye,light,distance,field);
 if(!uv)return null;
 const range=Math.hypot(...eye.map((v,i)=>v-light.position[i]));
 return {uv:uv.some(v=>v<0||v>1)?null:uv,strength:light.gain*(distance/Math.max(.01,range))**2,facing:dot(eye.map((v,i)=>v-light.position[i]),light.forward)/Math.max(.000001,range)};
}
export class SceneGlare{
 constructor(gl,make){this.gl=gl;this.vao=gl.createVertexArray();this.program=make(`#version 300 es
 precision highp float;
 uniform vec3 position,eye,right,up,forward;uniform vec2 viewport;out vec2 q;
 void main(){vec2 corners[6]=vec2[6](vec2(-1,-1),vec2(1,-1),vec2(1,1),vec2(-1,-1),vec2(1,1),vec2(-1,1));q=corners[gl_VertexID];vec3 rel=position-eye;float z=dot(rel,forward);gl_Position=vec4(dot(rel,right)*1.6/(viewport.x/viewport.y),dot(rel,up)*1.6,(500.001*z-1.)/499.999,z);gl_Position.xy+=q*80./viewport*z;}`,`#version 300 es
 precision highp float;in vec2 q;out vec4 color;uniform sampler2D field;uniform vec2 sampleUV;uniform float strength,exposure,lensGlow,glareStrength;uniform vec3 lensTint;uniform bool hasColor,inBeam;
 void main(){float r=length(q);if(r>1.)discard;vec4 t=texture(field,sampleUV);vec3 beam=hasColor?t.rgb:vec3(t.r);vec3 c=(inBeam?beam*strength*20.:vec3(0.))+lensTint*lensGlow*100.;float peak=max(c.r,max(c.g,c.b));if(peak<=0.)discard;float halo=exp(-r*r*12.)*.22+exp(-r*r*230.);float brightness=1.-exp(-peak*exposure*glareStrength);color=vec4(pow(c/max(peak,.000001),vec3(1./2.2))*brightness,halo);}`);}
 draw(camera,lights,params,texture){const gl=this.gl,p=this.program,loc=k=>gl.getUniformLocation(p,k);if(!params.glare||!params.hasMap)return;
 gl.useProgram(p);gl.bindVertexArray(this.vao);gl.enable(gl.DEPTH_TEST);gl.depthMask(false);gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE);gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,texture);gl.uniform1i(loc('field'),0);gl.uniform1i(loc('hasColor'),params.hasColor?1:0);gl.uniform1f(loc('exposure'),params.exposure);gl.uniform1f(loc('glareStrength'),params.glareStrength??1);gl.uniform3fv(loc('lensTint'),params.glareTint||[0,0,0]);
 for(const key of ['eye','right','up','forward'])gl.uniform3fv(loc(key),camera[key]);gl.uniform2f(loc('viewport'),camera.width,camera.height);
 for(const light of lights){const sample=glareSample(camera.eye,light,params.distanceM,params.fieldM);if(!sample)continue;gl.uniform3fv(loc('position'),light.position);gl.uniform2fv(loc('sampleUV'),sample.uv||[.5,.5]);gl.uniform1i(loc('inBeam'),sample.uv?1:0);gl.uniform1f(loc('lensGlow'),sample.facing*light.gain);gl.uniform1f(loc('strength'),sample.strength);gl.drawArrays(gl.TRIANGLES,0,6);}
 gl.disable(gl.BLEND);gl.depthMask(true);
 }
}
