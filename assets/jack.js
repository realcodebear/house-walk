// Jack (Last Shepherd's woodsman, low-poly body) as a walking character.
// Locomotion = one phase shared by the walk / jog / run loops (all start on a left-foot plant), advanced by the
// body's real speed over the blended stride length, so the planted foot does not slide at any speed.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const smooth = (t) => t * t * (3 - 2 * t);

export async function loadJack(base, ver = '') {
  const [gltf, meta] = await Promise.all([
    new GLTFLoader().loadAsync(base + 'jack.glb' + ver),
    fetch(base + 'jack.json' + ver).then((r) => r.json()),
  ]);
  return new Jack(gltf, meta);
}

class Jack {
  constructor(gltf, meta) {
    this.root = new THREE.Group();            // sits at the feet; rotation.y = heading
    this.model = gltf.scene;
    this.root.add(this.model);
    this.model.traverse((o) => {
      if (o.isMesh) { o.frustumCulled = false; o.castShadow = false; o.receiveShadow = true; }
    });
    this.meta = meta;
    this.mixer = new THREE.AnimationMixer(this.model);
    this.act = {};
    for (const clip of gltf.animations) {
      const a = this.mixer.clipAction(clip);
      a.play();
      a.setEffectiveWeight(0);
      this.act[clip.name] = a;
    }
    this.cycles = ['K_Walk', 'K_Jog', 'K_Run'].filter((n) => this.act[n] && meta[n]?.speed_mps);
    for (const n of this.cycles) this.act[n].timeScale = 0;          // driven by the shared phase
    this.speeds = this.cycles.map((n) => meta[n].speed_mps);
    this.strides = this.cycles.map((n) => meta[n].speed_mps * meta[n].cycle_s);
    this.phase = 0;
    this.air = 0;
    this.airT = 0;
    this.heading = 0;
    this.shadow = blobShadow();
    this.root.add(this.shadow);
  }

  /** speed: horizontal m/s; move: world direction of travel (x, z) or null; floorY: ground under the feet */
  update(dt, speed, vx, vz, onGround) {
    // face the way he walks
    if (speed > 0.15) {
      const want = Math.atan2(vx, vz);
      let d = want - this.heading;
      d = Math.atan2(Math.sin(d), Math.cos(d));
      this.heading += d * Math.min(1, dt * 10);
    }
    this.root.rotation.y = this.heading;

    // locomotion weights: idle -> walk -> jog -> run, each clip at its own measured speed
    const w = this.cycles.map(() => 0);
    const sp = this.speeds;
    let idle = 0;
    if (speed <= sp[0]) { const t = smooth(Math.min(1, speed / sp[0])); idle = 1 - t; w[0] = t; }
    else if (speed >= sp[sp.length - 1]) w[w.length - 1] = 1;
    else {
      for (let i = 0; i < sp.length - 1; i++) {
        if (speed <= sp[i + 1]) { const t = (speed - sp[i]) / (sp[i + 1] - sp[i]); w[i] = 1 - t; w[i + 1] = t; break; }
      }
    }
    let wsum = 0, stride = 0;
    w.forEach((x, i) => { wsum += x; stride += x * this.strides[i]; });
    stride = wsum > 1e-4 ? stride / wsum : this.strides[0];
    this.phase = (this.phase + (dt * speed) / Math.max(0.05, stride)) % 1;

    // in the air (after a moment, so stair steps do not trigger it)
    this.airT = onGround ? 0 : this.airT + dt;
    const airWant = this.airT > 0.12 ? 1 : 0;
    this.air += (airWant - this.air) * Math.min(1, dt * (airWant ? 10 : 7));
    const ground = 1 - this.air;

    this.act.K_Idle.setEffectiveWeight(idle * ground);
    this.cycles.forEach((n, i) => {
      const a = this.act[n];
      a.setEffectiveWeight(w[i] * ground);
      a.time = this.phase * a.getClip().duration;
    });
    if (this.act.Jump_Air) this.act.Jump_Air.setEffectiveWeight(this.air);
    this.mixer.update(dt);
  }
}

function blobShadow() {
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d');
  const grd = g.createRadialGradient(32, 32, 2, 32, 32, 32);
  grd.addColorStop(0, 'rgba(0,0,0,0.42)');
  grd.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = grd;
  g.fillRect(0, 0, 64, 64);
  const m = new THREE.Mesh(new THREE.PlaneGeometry(0.95, 0.95),
    new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false }));
  m.rotation.x = -Math.PI / 2;
  m.position.y = 0.012;
  m.renderOrder = 1;
  return m;
}
