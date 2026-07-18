import * as THREE from "../../dashboard/assets/vendor/three.module.min.js";

globalThis.THREE = THREE;
await import("./prooflock_core.js");
await import("./prooflock_lattice.js");
await import("./app.js");
