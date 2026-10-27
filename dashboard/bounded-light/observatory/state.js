export const PALETTES = Object.freeze({duality:[[0.97,0.67,0.29],[0.32,0.85,1]],aurora:[[0.65,0.36,1],[0.4,1,0.74]],ember:[[1,0.27,0.11],[1,0.89,0.69]],ice:[[0.28,0.6,0.97],[0.89,1,1]]});
export const DEFAULT_STATE=Object.freeze({version:1,kind:'hopf',count:32000,complexity:3,deformation:.35,seed:42,palette:'duality',exposure:1,yaw:25,pitch:-15,zoom:1});
const kinds=['hopf','trefoil','gyroid','superformula'];
export function validateState(input){
 if(!input||typeof input!=='object'||Array.isArray(input))throw new TypeError('A setup must be a JSON object.');
 const keys=Object.keys(DEFAULT_STATE);if(Object.keys(input).some(k=>!keys.includes(k)))throw new TypeError('This setup contains unknown fields.');
 const state={...DEFAULT_STATE,...input};
 if(state.version!==1)throw new RangeError('Unsupported setup version.');
 if(!kinds.includes(state.kind)||!Object.hasOwn(PALETTES,state.palette))throw new RangeError('Unknown geometry or palette.');
 const rules={count:[12000,64000,true],complexity:[1,5,true],deformation:[0,1,false],seed:[0,99999,true],exposure:[.4,1.8,false],yaw:[-180,180,false],pitch:[-85,85,false],zoom:[.65,1.5,false]};
 for(const [key,[lo,hi,int]]of Object.entries(rules)){const v=state[key];if(typeof v!=='number'||!Number.isFinite(v)||v<lo||v>hi||(int&&!Number.isInteger(v)))throw new RangeError(`Invalid ${key}.`);}
 if(![12000,32000,64000].includes(state.count))throw new RangeError('Choose a supported point count.');
 return state;
}
export function encodeState(state){return '#view='+encodeURIComponent(JSON.stringify(validateState(state)));}
export function decodeState(hash){if(!hash.startsWith('#view='))return null;if(hash.length>2500)throw new RangeError('View link is too long.');return validateState(JSON.parse(decodeURIComponent(hash.slice(6))));}
export function projectPoint(x,y,z,state,width,height){const ya=state.yaw*Math.PI/180,pa=state.pitch*Math.PI/180;const xx=Math.cos(ya)*x+Math.sin(ya)*z,zz=-Math.sin(ya)*x+Math.cos(ya)*z;const yy=Math.cos(pa)*y-Math.sin(pa)*zz,depth=Math.sin(pa)*y+Math.cos(pa)*zz;const camera=5.5-depth;const scale=1.2*Math.min(width,height)*state.zoom/camera;return{x:width/2+xx*scale,y:height/2-yy*scale,depth,scale};}
export function colourAt(phase,palette){const [a,b]=PALETTES[palette];const t=.5+.5*Math.sin(phase*Math.PI*2);return a.map((v,i)=>Math.round(255*(v+(b[i]-v)*t)));}
export function svgSnapshot(geometry,state,width=3840,height=2160){
 state=validateState(state);if(!Number.isInteger(width)||!Number.isInteger(height)||width<100||height<100||width>30000||height>30000)throw new RangeError('Invalid export dimensions.');
 const count=geometry.phases.length;if(geometry.positions.length!==count*3)throw new Error('Geometry data mismatch.');
 const step=Math.max(1,Math.ceil(count/24000));const parts=[`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><title>LumenCore ${state.kind} geometric study</title><metadata>${JSON.stringify(state).replaceAll('&','&amp;').replaceAll('<','&lt;')}</metadata><rect width="100%" height="100%" fill="#050c13"/><g>`];
 for(let i=0;i<count;i+=step){const p=projectPoint(...geometry.positions.subarray(i*3,i*3+3),state,width,height);const rgb=colourAt(geometry.phases[i],state.palette);const radius=Math.max(.8,height/1100*(.8+.35*(p.depth+1.8)));const opacity=Math.min(.92,(.22+.12*(p.depth+1.8))*state.exposure);parts.push(`<circle cx="${p.x.toFixed(2)}" cy="${p.y.toFixed(2)}" r="${radius.toFixed(2)}" fill="rgb(${rgb.join(',')})" opacity="${opacity.toFixed(3)}"/>`);}
 parts.push('</g></svg>');return parts.join('');
}
