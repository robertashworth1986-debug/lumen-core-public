import {generateGeometry} from './geometry.mjs';
self.onmessage=event=>{const {id,options}=event.data;try{const geometry=generateGeometry(options);self.postMessage({id,geometry},[geometry.positions.buffer,geometry.phases.buffer]);}catch(error){self.postMessage({id,error:error instanceof Error?error.message:'Geometry generation failed.'});}};
