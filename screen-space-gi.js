/** Single-bounce screen-space gather. Linear HDR input; no temporal feedback. */
export class ScreenSpaceGI{
 constructor(gl,make){this.gl=gl;this.supported=!!gl.getExtension('EXT_color_buffer_float');this.vao=gl.createVertexArray();
 this.program=make(`#version 300 es
 precision highp float;out vec2 uv;void main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);uv=p;gl_Position=vec4(p*2.-1.,0.,1.);}`,`#version 300 es
 precision highp float;in vec2 uv;out vec4 color;
 uniform sampler2D radiance,normals,depthMap;uniform vec2 viewport;uniform vec3 cameraRight,cameraUp,cameraForward;uniform float exposure,ambient,intensity,reach;
 float viewZ(float d){return 1./(500.001-(d*2.-1.)*499.999);}
 vec3 position(vec2 t,float d){float z=viewZ(d);return vec3((t*2.-1.)*vec2(viewport.x/viewport.y,1.)*z/1.6,z);}
 vec3 normalAt(vec2 t){vec3 n=normalize(texture(normals,t).xyz*2.-1.);return vec3(dot(n,cameraRight),dot(n,cameraUp),dot(n,cameraForward));}
 vec3 directAt(vec2 t){vec3 n=normalize(texture(normals,t).xyz*2.-1.);vec3 fill=ambient*vec3(.018,.024,.026)*(.25+.75*abs(dot(n,normalize(vec3(.4,.8,-.5)))))/.08;return max(vec3(0.),texture(radiance,t).rgb-fill);}
 vec3 tone(vec3 c){float peak=max(.000001,max(c.r,max(c.g,c.b)));return pow(c/peak*(1.-exp(-peak*exposure)),vec3(1./2.2));}
 // Integer pixel hashing avoids a repeating screen-space sampling lattice.
 uint hashPixel(uvec2 p){uint h=p.x*1597334677u^p.y*3812015801u;h=(h^(h>>16))*2246822519u;h=(h^(h>>13))*3266489917u;return h^(h>>16);}
 void main(){float d=texture(depthMap,uv).r;if(d>=1.){color=vec4(0.);return;}vec3 p=position(uv,d),n=normalAt(uv),bounce=vec3(0.);float pixelRadius=min(96.,reach*viewport.y*.8/max(.001,p.z));
 uint seed=hashPixel(uvec2(gl_FragCoord.xy));float phase=float(seed&65535u)/65536.*6.2831853,jitter=(float(seed>>16)+.5)/65536.;
 for(int i=0;i<48;i++){float a=float(i)*2.39996323+phase,r=sqrt((float(i)+jitter)/48.);vec2 t=uv+vec2(cos(a),sin(a))*r*pixelRadius/viewport;if(any(lessThan(t,vec2(0.)))||any(greaterThan(t,vec2(1.))))continue;float sd=texture(depthMap,t).r;if(sd>=1.)continue;vec3 q=position(t,sd),delta=q-p;float dist=length(delta);if(dist<.002||dist>reach)continue;vec3 direction=delta/dist,sn=normalAt(t);float form=abs(dot(n,direction))*abs(dot(sn,-direction));if(form<.0001)continue;
 // Reject links hidden by foreground depth along the segment. Hidden geometry is unavailable.
 float visible=1.;for(int j=1;j<5;j++){float f=float(j)/5.;vec3 v=mix(p,q,f);vec2 screen=v.xy/v.z*1.6/vec2(viewport.x/viewport.y,1.)*.5+.5;float zd=texture(depthMap,screen).r;if(zd<1.&&viewZ(zd)<v.z-max(.01,dist*.025)){visible=0.;break;}}
 float pixelArea=pow(2.*q.z/(1.6*viewport.y),2.)/max(.2,abs(sn.z));float area=pixelArea*pixelRadius*pixelRadius/48.;bounce+=directAt(t)*form*area/max(.0001,dist*dist)*visible*(1.-dist/reach);
 }color=vec4(bounce*.6,1.);
 }`);
 this.filterProgram=make(`#version 300 es
 precision highp float;out vec2 uv;void main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);uv=p;gl_Position=vec4(p*2.-1.,0.,1.);}`,`#version 300 es
 precision highp float;in vec2 uv;out vec4 color;uniform sampler2D bounceMap,radiance,normals,depthMap;uniform vec2 viewport;uniform float softness,exposure,intensity;
 float viewZ(float d){return 1./(500.001-(d*2.-1.)*499.999);}
 vec3 tone(vec3 c){float peak=max(.000001,max(c.r,max(c.g,c.b)));return pow(c/peak*(1.-exp(-peak*exposure)),vec3(1./2.2));}
 void main(){float d=texture(depthMap,uv).r;if(d>=1.){color=vec4(0.);return;}float z=viewZ(d),total=0.;vec3 n=normalize(texture(normals,uv).xyz*2.-1.),sum=vec3(0.);
 for(int y=-2;y<=2;y++)for(int x=-2;x<=2;x++){vec2 offset=vec2(float(x),float(y));vec2 t=uv+offset*softness*.5/viewport;if(any(lessThan(t,vec2(0.)))||any(greaterThan(t,vec2(1.))))continue;float sd=texture(depthMap,t).r;if(sd>=1.)continue;vec3 sn=normalize(texture(normals,t).xyz*2.-1.);float dz=abs(viewZ(sd)-z)/max(.005,z*.01);float weight=exp(-dot(offset,offset)*.4-dz*dz)*pow(max(0.,dot(n,sn)),16.);sum+=texture(bounceMap,t).rgb*weight;total+=weight;}
 vec3 base=texture(radiance,uv).rgb;vec3 indirect=sum/max(.00001,total)*intensity;color=vec4(max(vec3(0.),tone(base+indirect)-tone(base)),1.);
 }`);}
 ensureBounce(){const gl=this.gl;if(this.bounceWidth===this.width&&this.bounceHeight===this.height)return;this.bounceWidth=this.width;this.bounceHeight=this.height;if(this.bounceTexture)gl.deleteTexture(this.bounceTexture);if(this.bounceFbo)gl.deleteFramebuffer(this.bounceFbo);this.bounceTexture=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,this.bounceTexture);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA16F,this.width,this.height,0,gl.RGBA,gl.HALF_FLOAT,null);this.bounceFbo=gl.createFramebuffer();gl.bindFramebuffer(gl.FRAMEBUFFER,this.bounceFbo);gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.TEXTURE_2D,this.bounceTexture,0);if(gl.checkFramebufferStatus(gl.FRAMEBUFFER)!==gl.FRAMEBUFFER_COMPLETE)throw Error('Indirect-light framebuffer unavailable');}

 begin(w,h){if(!this.supported)return false;const gl=this.gl;if(this.width!==w||this.height!==h){this.width=w;this.height=h;if(this.textures)for(const t of this.textures)gl.deleteTexture(t);if(this.fbo)gl.deleteFramebuffer(this.fbo);this.fbo=gl.createFramebuffer();gl.bindFramebuffer(gl.FRAMEBUFFER,this.fbo);this.textures=[];
 for(let i=0;i<3;i++){const t=gl.createTexture();this.textures.push(t);gl.bindTexture(gl.TEXTURE_2D,t);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);gl.texImage2D(gl.TEXTURE_2D,0,i===0?gl.RGBA16F:i===1?gl.RGBA8:gl.DEPTH_COMPONENT24,w,h,0,i===2?gl.DEPTH_COMPONENT:gl.RGBA,i===0?gl.HALF_FLOAT:i===1?gl.UNSIGNED_BYTE:gl.UNSIGNED_INT,null);gl.framebufferTexture2D(gl.FRAMEBUFFER,i===2?gl.DEPTH_ATTACHMENT:gl.COLOR_ATTACHMENT0+i,gl.TEXTURE_2D,t,0);}
 gl.drawBuffers([gl.COLOR_ATTACHMENT0,gl.COLOR_ATTACHMENT1]);if(gl.checkFramebufferStatus(gl.FRAMEBUFFER)!==gl.FRAMEBUFFER_COMPLETE){this.supported=false;gl.bindFramebuffer(gl.FRAMEBUFFER,null);return false;}}
 gl.bindFramebuffer(gl.FRAMEBUFFER,this.fbo);return true;}
 finish(camera,params){const gl=this.gl,loc=k=>gl.getUniformLocation(this.program,k);this.ensureBounce();gl.bindFramebuffer(gl.FRAMEBUFFER,this.bounceFbo);gl.disable(gl.BLEND);gl.viewport(0,0,this.width,this.height);gl.disable(gl.DEPTH_TEST);gl.useProgram(this.program);gl.bindVertexArray(this.vao);
 this.textures.forEach((t,i)=>{gl.activeTexture(gl.TEXTURE0+i);gl.bindTexture(gl.TEXTURE_2D,t);gl.uniform1i(loc(['radiance','normals','depthMap'][i]),i);});gl.uniform2f(loc('viewport'),this.width,this.height);for(const [key,value]of Object.entries(camera))gl.uniform3fv(loc('camera'+key[0].toUpperCase()+key.slice(1)),value);for(const [key,value]of Object.entries({exposure:params.exposure,ambient:params.ambient,intensity:params.ssgiIntensity??1,reach:Math.max(.01,params.ssgiRadius??1)}))gl.uniform1f(loc(key),value);gl.drawArrays(gl.TRIANGLES,0,3);
 gl.bindFramebuffer(gl.FRAMEBUFFER,null);gl.enable(gl.BLEND);gl.blendFunc(gl.ONE,gl.ONE);gl.useProgram(this.filterProgram);const f=k=>gl.getUniformLocation(this.filterProgram,k);for(const [i,key]of ['radiance','normals','depthMap'].entries())gl.uniform1i(f(key),i);gl.activeTexture(gl.TEXTURE3);gl.bindTexture(gl.TEXTURE_2D,this.bounceTexture);gl.uniform1i(f('bounceMap'),3);gl.uniform2f(f('viewport'),this.width,this.height);gl.uniform1f(f('softness'),Math.max(0,params.ssgiSoftness??4));gl.uniform1f(f('exposure'),params.exposure);gl.uniform1f(f('intensity'),params.ssgiIntensity??1);gl.drawArrays(gl.TRIANGLES,0,3);gl.disable(gl.BLEND);gl.enable(gl.DEPTH_TEST);gl.activeTexture(gl.TEXTURE0);
 }
}
