import {sliceInfill} from './slice-infill.js';
/** Transparent measured planes in projector coordinates, in metres. */
export class SceneSlices {
  constructor(gl){
    this.gl=gl;this.planes=[];
    const shader=(type,text)=>{const s=gl.createShader(type);gl.shaderSource(s,text);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;};
    this.program=gl.createProgram();
    gl.attachShader(this.program,shader(gl.VERTEX_SHADER,`#version 300 es
    precision highp float;layout(location=0)in vec2 corner;uniform vec3 eye,right,up,forward,source,sourceRight,sourceUp,sourceForward;uniform float aspect,field,z;out vec2 uv;out vec3 worldPoint;
    void main(){vec3 p=source+sourceRight*corner.x*field+sourceUp*corner.y*field+sourceForward*z;worldPoint=p;vec3 q=p-eye;float depth=dot(q,forward);gl_Position=vec4(dot(q,right)*1.6/aspect,dot(q,up)*1.6,(500.001*depth-1.)/499.999,depth);uv=vec2(corner.x+.5,.5-corner.y);}`));
    gl.attachShader(this.program,shader(gl.FRAGMENT_SHADER,`#version 300 es
    precision highp float;uniform sampler2D map,mapNext;uniform float blendAmount;uniform float opacity,shadowNear,shadowFar,gain;uniform bool shadows;uniform sampler2D shadowMap;uniform vec4 shadowRect;uniform mat4 lightVP;in vec3 worldPoint;in vec2 uv;out vec4 color;
    float visibility(){if(!shadows)return 1.;vec4 q=lightVP*vec4(worldPoint,1.);if(q.w<=0.)return 1.;vec3 uvz=q.xyz/q.w*.5+.5;if(any(lessThan(uvz,vec3(0.)))||any(greaterThan(uvz,vec3(1.))))return 1.;float stored=texture(shadowMap,shadowRect.xy+uvz.xy*shadowRect.zw).r;float current=shadowNear*shadowFar/(shadowFar-uvz.z*(shadowFar-shadowNear));float nearest=shadowNear*shadowFar/(shadowFar-stored*(shadowFar-shadowNear));return current-.002<=nearest?1.:0.;}
    void main(){vec3 c=mix(texture(map,uv).rgb,texture(mapNext,uv).rgb,blendAmount);color=vec4(c*visibility()*gain,opacity);}`));
    gl.linkProgram(this.program);if(!gl.getProgramParameter(this.program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(this.program));
    this.vao=gl.createVertexArray();gl.bindVertexArray(this.vao);const vbo=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,vbo);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-.5,-.5,.5,-.5,.5,.5,-.5,-.5,.5,.5,-.5,.5]),gl.STATIC_DRAW);gl.enableVertexAttribArray(0);gl.vertexAttribPointer(0,2,gl.FLOAT,false,0,0);
  }
  set(slices,field){const gl=this.gl;for(const p of this.planes)gl.deleteTexture(p.texture);this.field=field/1000;this.planes=[...slices].sort((a,b)=>a.z-b.z).map(s=>{const texture=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,texture);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,s.image);for(const k of [gl.TEXTURE_MIN_FILTER,gl.TEXTURE_MAG_FILTER])gl.texParameteri(gl.TEXTURE_2D,k,gl.LINEAR);for(const k of [gl.TEXTURE_WRAP_S,gl.TEXTURE_WRAP_T])gl.texParameteri(gl.TEXTURE_2D,k,gl.CLAMP_TO_EDGE);return {z:s.z/1000,texture};});}
  draw(camera,source,opacity,shadow,infill=1){
    const gl=this.gl,p=this.program,loc=k=>gl.getUniformLocation(p,k);gl.useProgram(p);gl.bindVertexArray(this.vao);
    for(const [k,v]of Object.entries({...camera,source:source.position,sourceRight:source.right,sourceUp:source.up,sourceForward:source.forward}))if(Array.isArray(v))gl.uniform3fv(loc(k),v);
    gl.uniform1i(loc('shadows'),shadow?.enabled?1:0);if(shadow){gl.uniform4fv(loc('shadowRect'),shadow.rect||[0,0,1,1]);gl.uniformMatrix4fv(loc('lightVP'),false,shadow.matrix);gl.uniform1f(loc('shadowNear'),shadow.near);gl.uniform1f(loc('shadowFar'),shadow.far);gl.activeTexture(gl.TEXTURE1);gl.bindTexture(gl.TEXTURE_2D,shadow.texture);gl.uniform1i(loc('shadowMap'),1);}
    gl.uniform1f(loc('aspect'),camera.aspect);gl.uniform1f(loc('field'),this.field);gl.uniform1f(loc('opacity'),opacity);gl.uniform1f(loc('gain'),source.gain??1);gl.uniform1i(loc('map'),0);gl.uniform1i(loc('mapNext'),2);gl.activeTexture(gl.TEXTURE0);
    gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE);gl.depthMask(false);
    const depth=z=>source.position.reduce((s,v,i)=>s+(v+source.forward[i]*z-camera.eye[i])*camera.forward[i],0);
    for(const plane of sliceInfill(this.planes.map(p=>p.z),infill).sort((a,b)=>depth(b.z)-depth(a.z))){gl.uniform1f(loc('z'),plane.z);gl.uniform1f(loc('opacity'),opacity*plane.weight);gl.uniform1f(loc('blendAmount'),plane.mix);gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,this.planes[plane.a].texture);gl.activeTexture(gl.TEXTURE2);gl.bindTexture(gl.TEXTURE_2D,this.planes[plane.b].texture);gl.drawArrays(gl.TRIANGLES,0,6);}gl.activeTexture(gl.TEXTURE0);
    gl.depthMask(true);gl.disable(gl.BLEND);
  }
}
