// House Walk v2 engine: walks Jack (or you, in first person) through one house design.
// Each design folder holds house.glb + house.json (written by blender/kit.py) and an index.html that sets
// window.HOUSE = { base: './' } before loading this file.
// Desktop: pointer-lock mouse look + WASD.  Phones: landscape, left-thumb joystick, right-thumb look, tap doors.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { MeshBVH, acceleratedRaycast } from 'three-mesh-bvh';
import { loadJack } from '../assets/jack.js';

THREE.Mesh.prototype.raycast = acceleratedRaycast;

const BASE = (window.HOUSE && window.HOUSE.base) || './';
const params = new URLSearchParams(location.search);
const TOUCH = matchMedia('(pointer: coarse)').matches || params.has('touch');   // ?touch forces phone controls
const P = { radius: 0.22, height: 1.75, eye: 1.62, step: 0.3, walk: 1.4, run: 3.8, accel: 11, airAccel: 2.5, jump: 4.0, gravity: 14 };
const SUBSTEPS = 4;
const REACH = 2.8;
const QUALITY = TOUCH ? { pr: 1.5, shadow: 1024, lights: 5, post: false } : { pr: 2, shadow: 2048, lights: 10, post: !params.has('lite') };

// ------------------------------------------------------------------ renderer / scene
const $ = (id) => document.getElementById(id);
const canvas = $('view');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
const maxPr = Math.min(devicePixelRatio, QUALITY.pr);
let pixelRatio = QUALITY.post ? Math.min(maxPr, 1.5) : maxPr;
renderer.setPixelRatio(pixelRatio);
renderer.setSize(innerWidth, innerHeight);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.shadowMap.autoUpdate = false;              // static scene: redraw shadows only when a door moves

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(70, innerWidth / innerHeight, 0.05, 500);
camera.rotation.order = 'YXZ';
function fitFov() {                                  // keep the view at least ~80° wide on narrow screens
  const a = innerWidth / innerHeight, minH = THREE.MathUtils.degToRad(80);
  camera.fov = Math.min(95, Math.max(68, THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(minH / 2) / a))));
  camera.aspect = a;
  camera.updateProjectionMatrix();
}
fitFov();
const hemi = new THREE.HemisphereLight(0xdbe9ff, 0x6f604c, 1.5);
const sun = new THREE.DirectionalLight(0xfff1dc, 2.6);
sun.castShadow = true;
sun.shadow.mapSize.set(QUALITY.shadow, QUALITY.shadow);
Object.assign(sun.shadow.camera, { left: -22, right: 22, top: 22, bottom: -22, near: 1, far: 120 });
sun.shadow.bias = -0.0004;
sun.shadow.normalBias = 0.025;
scene.add(hemi, sun, sun.target);

// post-processing (desktop): ambient occlusion in corners + a soft glow on lamps and cove LEDs
let composer = null, postOn = false;
let baked = false;
function buildComposer() {
  composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  if (!baked) {
    const ao = new GTAOPass(scene, camera, innerWidth, innerHeight);
    ao.updateGtaoMaterial({ radius: 0.45, distanceExponent: 1.4, thickness: 1.0, scale: 1.0, samples: 12 });
    ao.blendIntensity = 0.85;
    composer.addPass(ao);
  }
  composer.addPass(new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), 0.2, 0.4, 0.96));
  composer.addPass(new OutputPass());
  composer.setPixelRatio(pixelRatio);
  composer.setSize(innerWidth, innerHeight);
}

// ------------------------------------------------------------------ UI refs
const hud = $('hud'), promptEl = $('prompt'), overlay = $('overlay'), mapCanvas = $('map');
const mapCtx = mapCanvas.getContext('2d');
if (TOUCH) document.body.classList.add('touch');

// ------------------------------------------------------------------ state
const player = { pos: new THREE.Vector3(), vel: new THREE.Vector3(), vy: 0, yaw: 0, pitch: 0, eyeY: 0, onGround: true, bob: 0 };
const keys = new Set();
let playing = false, testMode = false, showMap = true, lightsOn = true, runToggle = false;
let data, FT = 0.3048, collider, LV = [];
let jack = null, view = 'first', viewChosen = false;
let spawnIdx = 0;
const cam = { zoom: 1, cur: 2 };
const doors = [], doorPick = [], fans = [], roomLights = [];
const raycaster = new THREE.Raycaster();
raycaster.firstHitOnly = true;

const toWorld = (xft, yft, zft = 0) => new THREE.Vector3(xft * FT, zft * FT, -yft * FT);
const toPlan = (v) => ({ x: v.x / FT, y: -v.z / FT });

// ------------------------------------------------------------------ load
const draco = new DRACOLoader().setDecoderPath('https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/libs/draco/gltf/');
const gltfLoader = new GLTFLoader().setDRACOLoader(draco);
const [json, gltf] = await Promise.all([
  fetch(BASE + 'house.json').then((r) => r.json()),
  gltfLoader.loadAsync(BASE + 'house.glb', (e) => {
    if (e.total) $('loading').textContent = `Loading house… ${Math.round((e.loaded / e.total) * 100)}%`;
  }),
]);
data = json; FT = data.ft;
LV = Object.entries(data.levels).map(([k, v]) => ({ key: k, ...v })).sort((a, b) => a.z - b.z);
document.title = `${data.title || 'House'} — House Walk`;
const titleEl = $('title'); if (titleEl) titleEl.textContent = data.title || 'House Walk';

// look of this design
const look = data.look || {};
const sky = new THREE.Color().setRGB(...(look.sky || [0.62, 0.76, 0.95]));
scene.background = sky;
scene.fog = new THREE.Fog(sky, ...(look.fog || [60, 220]));
if (look.hemi) { hemi.color.setRGB(...look.hemi[0]); hemi.groundColor.setRGB(...look.hemi[1]); hemi.intensity = look.hemi[2] * (TOUCH ? 1.15 : 1); }
if (look.sun) { sun.color.setRGB(...look.sun.color); sun.intensity = look.sun.intensity; }
renderer.toneMappingExposure = look.exposure || 1;
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = look.env ?? 0.35;

const house = gltf.scene;
scene.add(house);
house.traverse((o) => {
  if (o.userData.door_closed !== undefined) {
    const d = { mesh: o, closed: o.userData.door_closed, open: o.userData.door_open };
    d.angle = d.target = d.closed;
    o.rotation.set(0, d.closed, 0);
    o.geometry.boundsTree = new MeshBVH(o.geometry);
    o.traverse((c) => { if (c.isMesh) { c.userData.door = d; c.castShadow = true; doorPick.push(c); } });
    doors.push(d);
  }
  if (o.userData.spin) { fans.push(o); o.traverse((c) => { c.userData.dynamic = true; }); }
});
house.updateMatrixWorld(true);

// baked lighting: LM_* objects carry a second UV set; draw them unlit with their lightmap
const lmInfo = data.lightmaps || {};
const lmRoots = [];
house.traverse((o) => { if (lmInfo[o.name]) lmRoots.push([o, lmInfo[o.name]]); });
baked = lmRoots.length > 0;
const texLoader = new THREE.TextureLoader();
const bakedMats = new Map();
function toBaked(src, tex, scale) {
  const key = src.uuid + '|' + tex.uuid;
  if (bakedMats.has(key)) return bakedMats.get(key);
  const m = new THREE.MeshBasicMaterial({
    name: src.name, map: src.map || null, color: src.color ? src.color.clone() : new THREE.Color(1, 1, 1),
    lightMap: tex, lightMapIntensity: scale * Math.PI * (look.lm_exposure ?? 1.0),
    transparent: src.transparent, opacity: src.opacity, alphaTest: src.alphaTest, side: src.side,
  });
  if (src.userData?.tint && src.map) m.color.setRGB(...src.userData.tint);
  if ((src.roughness ?? 1) < 0.32 && !src.transparent) {      // polished marble / ceramic keeps a faint reflection
    m.envMap = scene.environment;
    m.combine = THREE.MixOperation;
    m.reflectivity = 0.1;
  }
  if (m.transparent) m.depthWrite = false;
  bakedMats.set(key, m);
  return m;
}
await Promise.all(lmRoots.map(async ([root, info]) => {
  const tex = await texLoader.loadAsync(BASE + info.file);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.flipY = false;
  tex.channel = 1;
  tex.anisotropy = 4;
  root.traverse((m) => {
    if (!m.isMesh) return;
    m.userData.lm = true;
    m.material = toBaked(m.material, tex, info.scale);
    m.castShadow = true;
    m.receiveShadow = false;
  });
}));

// materials: tint textures (glTF has no multiply node), lattice = cut-out, glass = no depth write
const fixedMats = new Set();
function fixMaterial(m) {
  if (fixedMats.has(m)) return;
  fixedMats.add(m);
  if (m.userData?.tint && m.map) m.color.setRGB(...m.userData.tint);
  if (/lattice/i.test(m.name)) { m.transparent = false; m.alphaTest = 0.5; m.side = THREE.DoubleSide; }
  else if (m.transparent) m.depthWrite = false;
  if (m.emissiveIntensity > 1 && TOUCH) m.emissiveIntensity *= 0.8;
}

// merge static meshes by material: thousands of objects -> a few dozen draw calls
const byMat = new Map(), collGeoms = [], statics = [];
house.traverse((o) => { if (o.isMesh && !o.userData.door && !o.userData.dynamic) statics.push(o); });
for (const o of statics) {
  if (o.userData.lm) {                              // keep in the scene; add its triangles to the collider
    const g = o.geometry.clone().applyMatrix4(o.matrixWorld);
    if (!g.index) g.setIndex([...Array(g.attributes.position.count).keys()]);
    if (!/glass|water|lattice|curtain|leaves|lampshade|led|downlight/i.test(o.material.name) || /glass/i.test(o.material.name)) {
      collGeoms.push(new THREE.BufferGeometry().setAttribute('position', g.attributes.position).setIndex(g.index).toNonIndexed());
    }
    continue;
  }
  fixMaterial(o.material);
  const g = o.geometry.clone().applyMatrix4(o.matrixWorld);
  if (!g.index) g.setIndex([...Array(g.attributes.position.count).keys()]);
  if (!byMat.has(o.material)) byMat.set(o.material, []);
  byMat.get(o.material).push(g);
  if (!/glass|water|lattice|curtain|leaves|lampshade|led|downlight/i.test(o.material.name) || /screen/i.test(o.name)) {
    const c = new THREE.BufferGeometry().setAttribute('position', g.attributes.position).setIndex(g.index);
    collGeoms.push(c.toNonIndexed());
  } else if (/glass/i.test(o.material.name)) {                   // windows and railings still block you
    const c = new THREE.BufferGeometry().setAttribute('position', g.attributes.position).setIndex(g.index);
    collGeoms.push(c.toNonIndexed());
  }
  o.removeFromParent();
}
for (const [m, list] of byMat) {
  const names = new Set(list.flatMap((g) => Object.keys(g.attributes)));
  for (const g of list) {
    for (const n of Object.keys(g.attributes)) if (!['position', 'normal', 'uv'].includes(n)) g.deleteAttribute(n);
    if (names.has('uv') && !g.attributes.uv) g.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(g.attributes.position.count * 2), 2));
    if (!g.attributes.normal) g.computeVertexNormals();
  }
  const mesh = new THREE.Mesh(mergeGeometries(list, false), m);
  const see = m.transparent || /lattice|led|downlight|lampshade/i.test(m.name);
  mesh.castShadow = !see && !/lawn|grass|street|asphalt/i.test(m.name);
  mesh.receiveShadow = true;
  mesh.name = 'merged ' + m.name;
  scene.add(mesh);
}
for (const d of doors) d.mesh.traverse((c) => c.isMesh && fixMaterial(c.material));
for (const f of fans) f.traverse((c) => c.isMesh && fixMaterial(c.material));
const collGeo = mergeGeometries(collGeoms, false);
collGeo.boundsTree = new MeshBVH(collGeo);
collider = new THREE.Mesh(collGeo, new THREE.MeshBasicMaterial({ side: THREE.DoubleSide }));
collider.visible = false;
collider.updateMatrixWorld(true);

// lights: a small pool of real point lights follows the player through the house's lamp spots
const spots = (data.lights || []).map((l) => ({ level: l.level, pos: toWorld(l.x, l.y, l.z), color: new THREE.Color().setRGB(...l.color), power: l.power }));
const interior = look.interior || { color: [1, 0.83, 0.62], intensity: 4.5 };
for (let i = 0; i < Math.min(QUALITY.lights, spots.length); i++) {
  const l = new THREE.PointLight(new THREE.Color().setRGB(...interior.color), interior.intensity, 8, 1.6);
  scene.add(l);
  roomLights.push(l);
}
function placeLights() {
  const lv = levelOf(player.pos.y);
  const near = spots.filter((s) => s.level === lv).sort((a, b) => a.pos.distanceToSquared(player.pos) - b.pos.distanceToSquared(player.pos));
  roomLights.forEach((l, i) => {
    const s = near[i];
    if (!s) { l.intensity = 0; return; }
    l.position.copy(s.pos);
    l.color.copy(s.color);
    l.intensity = lightsOn ? interior.intensity * s.power : 0;
  });
}

// sun over the middle of the house
const centre = toWorld(15.5, 17, 0);
const off = look.sun?.offset || [14, 24, 12];
sun.position.copy(centre).add(new THREE.Vector3(...off));
sun.target.position.copy(centre);
sun.target.updateMatrixWorld();
renderer.shadowMap.needsUpdate = true;
if (QUALITY.post) { buildComposer(); postOn = true; }

$('loading').remove();
overlay.hidden = false;
spawn(0);
loadJack('../../assets/').then((j) => {
  jack = j;
  jack.root.scale.setScalar(0.96);                   // 1.76 m: Jack's model is a tall 1.83 m
  scene.add(j.root);
  if (!viewChosen) view = 'third';
}).catch((e) => console.warn('Jack did not load:', e));

// ------------------------------------------------------------------ helpers
function spawn(i) {
  spawnIdx = i;
  const s = data.spawns[i];
  player.pos.copy(toWorld(s.x, s.y, s.z));
  player.vel.set(0, 0, 0); player.vy = 0; player.yaw = s.yaw || 0; player.pitch = 0;
  player.eyeY = player.pos.y + P.eye;
  player.onGround = true;
  placeLights();
}

function levelOf(y) {
  let lv = LV[0].key;
  for (const l of LV) if (y > l.z * FT - 0.6) lv = l.key;
  return lv;
}

function roomAt(pos) {
  const p = toPlan(pos), lv = levelOf(pos.y);
  for (const r of data.rooms) {
    if (r.level !== lv) continue;
    for (const [x0, x1, y0, y1] of r.rects) if (p.x >= x0 && p.x <= x1 && p.y >= y0 && p.y <= y1) return r.name;
  }
  return lv === LV[0].key ? 'Garden' : 'Upstairs';
}

const _hits = [];
function firstHit(obj) { _hits.length = 0; raycaster.intersectObject(obj, false, _hits); return _hits[0] || null; }
function castNearest(origin, dir, far) {
  raycaster.set(origin, dir);
  raycaster.near = 0; raycaster.far = far;
  let best = firstHit(collider);
  for (const m of doorPick) {
    const h = firstHit(m);
    if (h && (!best || h.distance < best.distance)) best = h;
  }
  return best;
}

// --- capsule collision (three-mesh-bvh shapecast). The capsule floats `step` above the feet,
//     so stair risers and thresholds are climbed by the floor probe instead of blocking you.
const seg = new THREE.Line3(), segL = new THREE.Line3();
const _box = new THREE.Box3(), _tri = new THREE.Vector3(), _cap = new THREE.Vector3(), _dir = new THREE.Vector3();
const _inv = new THREE.Matrix4(), _v = new THREE.Vector3(), _hp = new THREE.Vector3();
function capsulePush(bvh, s, r) {
  _box.makeEmpty().expandByPoint(s.start).expandByPoint(s.end);
  _box.min.addScalar(-r); _box.max.addScalar(r);
  bvh.shapecast({
    intersectsBounds: (b) => b.intersectsBox(_box),
    intersectsTriangle: (tri) => {
      const d = tri.closestPointToSegment(s, _tri, _cap);
      if (d < r) {
        _dir.subVectors(_cap, _tri);
        const len = _dir.length();
        if (len < 1e-7) return;
        _dir.multiplyScalar((r - d) / len);
        s.start.add(_dir); s.end.add(_dir);
      }
    },
  });
}
function collide() {
  const p = player.pos;
  seg.start.set(p.x, p.y + P.step + P.radius, p.z);
  seg.end.set(p.x, p.y + P.height - P.radius, p.z);
  const sx = seg.start.x, sy = seg.start.y, sz = seg.start.z;
  capsulePush(collider.geometry.boundsTree, seg, P.radius);
  for (const d of doors) {
    if (d.mesh.getWorldPosition(_hp).distanceToSquared(p) > 6) continue;
    _inv.copy(d.mesh.matrixWorld).invert();
    segL.start.copy(seg.start).applyMatrix4(_inv);
    segL.end.copy(seg.end).applyMatrix4(_inv);
    capsulePush(d.mesh.geometry.boundsTree, segL, P.radius);
    _v.copy(segL.start).applyMatrix4(d.mesh.matrixWorld).sub(seg.start);
    seg.start.add(_v); seg.end.add(_v);
  }
  const dx = seg.start.x - sx, dz = seg.start.z - sz;
  p.x += dx; p.z += dz;
  if (seg.start.y - sy < -1e-4 && player.vy > 0) player.vy = 0;
  const L = Math.hypot(dx, dz);
  if (L > 1e-6) {
    const nx = dx / L, nz = dz / L, vn = player.vel.x * nx + player.vel.z * nz;
    if (vn < 0) { player.vel.x -= vn * nx; player.vel.z -= vn * nz; }
  }
}
const DOWN = new THREE.Vector3(0, -1, 0), _o = new THREE.Vector3();
const FLOOR_PROBES = [[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1]];
function floorAt(p) {
  let best = -Infinity;
  for (const [ox, oz] of FLOOR_PROBES) {
    _o.set(p.x + ox * P.radius * 0.6, p.y + P.step + 0.05, p.z + oz * P.radius * 0.6);
    raycaster.set(_o, DOWN); raycaster.near = 0; raycaster.far = 40;
    const h = firstHit(collider);
    if (h && h.point.y > best) best = h.point.y;
  }
  return best;
}

// ------------------------------------------------------------------ input: desktop
let dragLook = false, dragging = false, downAt = null;
function start() {
  overlay.hidden = true;
  playing = true;
  document.body.classList.add('playing');
  keepAwake();
  if (TOUCH) {
    $('touch').hidden = false;
    const el = document.documentElement;
    if (!testMode && el.requestFullscreen && !document.fullscreenElement) {
      el.requestFullscreen({ navigationUI: 'hide' }).then(() => screen.orientation?.lock?.('landscape')).catch(() => {});
    } else screen.orientation?.lock?.('landscape')?.catch?.(() => {});
  } else if (!testMode && !dragLook) canvas.requestPointerLock?.()?.catch?.(() => { dragLook = true; });
}
function pause() {
  playing = false; overlay.hidden = false; keys.clear(); resetTouch();
  document.body.classList.remove('playing');
  if (document.pointerLockElement) document.exitPointerLock();
}
let wakeLock = null;                                 // keep the screen on while playing (the browser's "caffeinate")
async function keepAwake() {
  try {
    if (!('wakeLock' in navigator) || wakeLock) return;
    wakeLock = await navigator.wakeLock.request('screen');
    wakeLock.addEventListener('release', () => { wakeLock = null; });
  } catch (e) { /* not allowed right now: try again on the next start */ }
}
document.addEventListener('visibilitychange', () => { if (!document.hidden && playing) keepAwake(); });
overlay.addEventListener('click', (e) => { if (!e.target.closest('a')) start(); });
document.addEventListener('pointerlockerror', () => { dragLook = true; });
document.addEventListener('pointerlockchange', () => {
  if (document.pointerLockElement !== canvas && !testMode && !dragLook && !TOUCH && playing) pause();
});
canvas.addEventListener('mousedown', (e) => {
  if (!playing) return start();
  dragging = true; downAt = [e.clientX, e.clientY, performance.now()];
  if (document.pointerLockElement === canvas) toggleDoor();
});
addEventListener('mouseup', (e) => {
  dragging = false;
  if (downAt && document.pointerLockElement !== canvas && Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) < 6
      && performance.now() - downAt[2] < 350) useAt(e.clientX, e.clientY);
  downAt = null;
});
document.addEventListener('mousemove', (e) => {
  if (!playing) return;
  const locked = document.pointerLockElement === canvas;
  if (!locked && !dragging) return;
  const k = locked ? 0.0022 : 0.004;
  player.yaw -= e.movementX * k;
  player.pitch = THREE.MathUtils.clamp(player.pitch - e.movementY * k, -1.45, 1.45);
});
addEventListener('keydown', (e) => {
  if (e.code === 'Escape' && playing && dragLook) return pause();
  if (!playing) return;
  keys.add(e.code);
  if (e.repeat) return;
  if (e.code === 'KeyE') toggleDoor();
  if (e.code === 'KeyM') toggleMap();
  if (e.code === 'KeyL') toggleLights();
  if (e.code === 'KeyV') toggleView();
  if (e.code === 'KeyQ') togglePost();
  if (e.code === 'Space') jump();
  const dm = /^(?:Digit|Numpad)([1-9])$/.exec(e.code);       // 1 = outside, 2 = ground floor, 3 = second floor ...
  if (dm && data.spawns[+dm[1] - 1]) spawn(+dm[1] - 1);
});
addEventListener('keyup', (e) => keys.delete(e.code));
addEventListener('blur', () => keys.clear());
addEventListener('wheel', (e) => { if (playing) cam.zoom = THREE.MathUtils.clamp(cam.zoom + e.deltaY * 0.001, 0.6, 1.8); }, { passive: true });
addEventListener('resize', () => {
  fitFov();
  renderer.setSize(innerWidth, innerHeight);
  composer?.setSize(innerWidth, innerHeight);
});
function jump() { if (player.onGround) { player.vy = P.jump; player.onGround = false; } }
function toggleMap() { showMap = !showMap; mapCanvas.style.display = showMap ? '' : 'none'; }
function toggleLights() { lightsOn = !lightsOn; placeLights(); }
function toggleView() { viewChosen = true; view = view === 'third' && jack ? 'first' : jack ? 'third' : 'first'; }
function togglePost() { if (!composer) buildComposer(); postOn = !postOn; }
function cycleFloor() { spawn((spawnIdx + 1) % data.spawns.length); }

// ------------------------------------------------------------------ input: touch
const touchEl = $('touch'), joyBase = $('joyBase'), joyKnob = $('joyKnob');
const joy = { id: null, x0: 0, y0: 0, x: 0, y: 0 };
const lookT = { id: null, x: 0, y: 0, t: 0, moved: 0, ay: 0, ap: 0 };
function resetTouch() { joy.id = lookT.id = null; joy.x = joy.y = 0; joyBase.style.display = 'none'; }
touchEl.addEventListener('pointerdown', (e) => {
  if (e.target !== touchEl) return;
  e.preventDefault();
  try { touchEl.setPointerCapture(e.pointerId); } catch (err) { /* synthetic or already-ended pointer */ }
  if (e.clientX < innerWidth * 0.45 && joy.id === null) {
    joy.id = e.pointerId; joy.x0 = e.clientX; joy.y0 = e.clientY; joy.x = joy.y = 0;
    Object.assign(joyBase.style, { left: e.clientX + 'px', top: e.clientY + 'px', display: 'block' });
    joyKnob.style.transform = '';
    $('joyHint').style.display = 'none';
  } else if (lookT.id === null) {
    Object.assign(lookT, { id: e.pointerId, x: e.clientX, y: e.clientY, t: performance.now(), moved: 0 });
  }
});
touchEl.addEventListener('pointermove', (e) => {
  if (e.pointerId === joy.id) {
    let dx = e.clientX - joy.x0, dy = e.clientY - joy.y0;
    const R = 56, L = Math.hypot(dx, dy);
    if (L > R) { dx *= R / L; dy *= R / L; }
    const m = Math.hypot(dx, dy) / R, c = m < 0.12 ? 0 : Math.pow((m - 0.12) / 0.88, 1.3);
    joy.x = m > 0 ? (dx / R / m) * c : 0; joy.y = m > 0 ? (dy / R / m) * c : 0;
    joyKnob.style.transform = `translate(${dx}px, ${dy}px)`;
  } else if (e.pointerId === lookT.id) {
    const dx = e.clientX - lookT.x, dy = e.clientY - lookT.y;
    lookT.x = e.clientX; lookT.y = e.clientY; lookT.moved += Math.abs(dx) + Math.abs(dy);
    lookT.ay -= dx * 0.0058;
    lookT.ap -= dy * 0.0048;
  }
});
function endTouch(e) {
  if (e.pointerId === joy.id) { joy.id = null; joy.x = joy.y = 0; joyBase.style.display = 'none'; }
  if (e.pointerId === lookT.id) {
    if (lookT.moved < 12 && performance.now() - lookT.t < 350) useAt(e.clientX, e.clientY);
    lookT.id = null;
  }
}
touchEl.addEventListener('pointerup', endTouch);
touchEl.addEventListener('pointercancel', endTouch);
const press = (id, fn) => $(id)?.addEventListener('pointerdown', (e) => { e.preventDefault(); e.stopPropagation(); fn(); });
press('bUse', toggleDoor);
press('bJump', jump);
press('bRun', () => { runToggle = !runToggle; $('bRun').classList.toggle('on', runToggle); });
press('bMap', toggleMap);
press('bLights', toggleLights);
press('bView', toggleView);
press('bFloor', cycleFloor);
press('bMenu', pause);
document.addEventListener('visibilitychange', () => { if (document.hidden) { keys.clear(); resetTouch(); } });

// ------------------------------------------------------------------ doors
const _fwd = new THREE.Vector3(), _ndc = new THREE.Vector2(), _chest = new THREE.Vector3();
function nearBody(hit) {
  _chest.set(player.pos.x, player.pos.y + 1.2, player.pos.z);
  return hit && hit.point.distanceTo(_chest) < REACH ? hit : null;
}
function camExtra() { return view === 'third' && jack ? cam.cur : 0; }
function lookedDoor() {
  camera.getWorldDirection(_fwd);
  const hit = nearBody(castNearest(camera.position, _fwd, camExtra() + REACH));
  return hit?.object.userData.door || null;
}
function swing(d) { d.target = Math.abs(d.target - d.open) < 1e-3 ? d.closed : d.open; }
function toggleDoor() { const d = lookedDoor(); if (d) swing(d); }
function useAt(x, y) {
  _ndc.set((x / innerWidth) * 2 - 1, -(y / innerHeight) * 2 + 1);
  raycaster.setFromCamera(_ndc, camera);
  const hit = nearBody(castNearest(raycaster.ray.origin.clone(), raycaster.ray.direction.clone(), camExtra() + REACH + 0.6));
  if (hit?.object.userData.door) swing(hit.object.userData.door);
}

// ------------------------------------------------------------------ update
const want = new THREE.Vector3();
function update(dt) {
  let moving = false;
  for (const d of doors) {
    const diff = d.target - d.angle;
    if (Math.abs(diff) > 1e-4) {
      d.angle += Math.sign(diff) * Math.min(Math.abs(diff), dt * 2.6);
      d.mesh.rotation.y = d.angle;
      d.mesh.updateMatrixWorld(true);
      moving = true;
    }
  }
  if (moving) renderer.shadowMap.needsUpdate = true;
  for (const f of fans) f.rotation.y += f.userData.spin * dt;

  if (lookT.ay || lookT.ap) {
    const a = 1 - Math.exp(-dt * 28), dy = lookT.ay * a, dp = lookT.ap * a;
    player.yaw += dy; lookT.ay -= dy;
    player.pitch = THREE.MathUtils.clamp(player.pitch + dp, -1.3, 1.3); lookT.ap -= dp;
    if (Math.abs(lookT.ay) < 1e-5) lookT.ay = 0;
    if (Math.abs(lookT.ap) < 1e-5) lookT.ap = 0;
  }
  want.set(0, 0, 0);
  if (playing) {
    if (joy.id !== null) want.set(joy.x, 0, joy.y);
    else {
      const f = (keys.has('KeyW') || keys.has('ArrowUp') ? 1 : 0) - (keys.has('KeyS') || keys.has('ArrowDown') ? 1 : 0);
      const s = (keys.has('KeyD') || keys.has('ArrowRight') ? 1 : 0) - (keys.has('KeyA') || keys.has('ArrowLeft') ? 1 : 0);
      want.set(s, 0, -f);
    }
    const mag = Math.min(1, want.length());
    if (mag > 0.05) {
      want.normalize().applyAxisAngle(THREE.Object3D.DEFAULT_UP, player.yaw);
      const running = runToggle || keys.has('ShiftLeft') || keys.has('ShiftRight');
      want.multiplyScalar((running ? P.run : P.walk) * mag);
    } else want.set(0, 0, 0);
  }
  const k = 1 - Math.exp(-(player.onGround ? P.accel : P.airAccel) * dt);
  player.vel.x += (want.x - player.vel.x) * k;
  player.vel.z += (want.z - player.vel.z) * k;

  const h = dt / SUBSTEPS;
  for (let i = 0; i < SUBSTEPS; i++) {
    player.pos.x += player.vel.x * h;
    player.pos.z += player.vel.z * h;
    collide();
    const floor = floorAt(player.pos);
    if (player.onGround && player.vy <= 0 && floor > -Infinity && player.pos.y - floor <= P.step + 0.02) {
      player.pos.y = floor;
      player.vy = 0;
    } else {
      player.vy -= P.gravity * h;
      player.pos.y += player.vy * h;
      if (player.pos.y <= floor) { player.pos.y = floor; player.vy = 0; player.onGround = true; }
      else player.onGround = false;
    }
  }
  if (player.pos.y < -20) spawn(0);

  const speed = Math.hypot(player.vel.x, player.vel.z);
  player.eyeY += (player.pos.y + P.eye - player.eyeY) * (1 - Math.exp(-dt * 14));
  if (Math.abs(player.pos.y + P.eye - player.eyeY) > 0.8) player.eyeY = player.pos.y + P.eye;
  camera.rotation.set(player.pitch, player.yaw, 0);
  if (jack) {
    jack.root.position.set(player.pos.x, player.eyeY - P.eye, player.pos.z);
    jack.update(dt, speed, player.vel.x, player.vel.z, player.onGround);
  }
  if (view === 'third' && jack) thirdPerson(dt);
  else {
    if (player.onGround && speed > 0.3) player.bob += dt * speed * 3.2;
    const bob = Math.sin(player.bob) * 0.02 * Math.min(1, speed / P.walk);
    camera.position.set(player.pos.x, player.eyeY + bob, player.pos.z);
    if (jack) jack.root.visible = false;
  }
}

const _tgt = new THREE.Vector3(), _back = new THREE.Vector3(), _want = new THREE.Vector3(), _cd = new THREE.Vector3();
function thirdPerson(dt) {
  const cy = Math.cos(player.yaw), sy = Math.sin(player.yaw), cp = Math.cos(player.pitch), spp = Math.sin(player.pitch);
  const indoor = !/Garden|Porch|Terrace/.test(roomAt(player.pos));
  const dist = (indoor ? 1.7 : 3.0) * cam.zoom;
  _tgt.set(player.pos.x, player.eyeY + 0.05, player.pos.z);
  _back.set(sy * cp, -spp, cy * cp);
  _want.copy(_back).multiplyScalar(dist).add(_tgt);
  _want.x += cy * 0.26; _want.z -= sy * 0.26;
  _cd.subVectors(_want, _tgt);
  const len = _cd.length();
  _cd.divideScalar(len);
  const hit = castNearest(_tgt, _cd, len + 0.25);
  const d = hit ? Math.max(0.2, hit.distance - 0.25) : len;
  cam.cur = d < cam.cur ? d : cam.cur + (d - cam.cur) * (1 - Math.exp(-dt * 3));
  camera.position.copy(_tgt).addScaledVector(_cd, cam.cur);
  jack.root.visible = cam.cur > 0.55;
}

// ------------------------------------------------------------------ HUD + minimap
let hudText = '', useShown = null;
function drawHud() {
  const lv = levelOf(player.pos.y);
  const t = `<b>${data.levels[lv].label}</b> · ${roomAt(player.pos)}`;
  if (t !== hudText) { hud.innerHTML = t; hudText = t; }
  const d = playing ? lookedDoor() : null;
  const label = d ? (Math.abs(d.target - d.open) < 1e-3 ? 'Close' : 'Open') : '';
  if (TOUCH) {
    if (label !== useShown) { $('bUse').style.display = label ? 'block' : 'none'; $('bUse').textContent = label; useShown = label; }
  } else if (d) {
    promptEl.textContent = `E / click — ${label.toLowerCase()} door`;
    promptEl.style.display = 'block';
  } else promptEl.style.display = 'none';
  if (showMap) drawMap(lv);
}
function drawMap(lv) {
  const W = mapCanvas.width, Hh = mapCanvas.height, pad = 12;
  const minX = -2, maxX = 33, minY = -6, maxY = 41;
  const k = Math.min((W - pad * 2) / (maxX - minX), (Hh - pad * 2) / (maxY - minY));
  const mx = (x) => pad + (x - minX) * k, my = (y) => Hh - pad - (y - minY) * k;
  const c = mapCtx;
  c.clearRect(0, 0, W, Hh);
  c.fillStyle = 'rgba(255,255,255,0.08)';
  c.beginPath();
  data.footprint.forEach(([x, y], i) => (i ? c.lineTo(mx(x), my(y)) : c.moveTo(mx(x), my(y))));
  c.closePath(); c.fill();
  const here = roomAt(player.pos);
  for (const r of data.rooms) {
    if (r.level !== lv) continue;
    c.fillStyle = r.name === here ? 'rgba(232,178,92,0.35)' : 'rgba(255,255,255,0.10)';
    for (const [x0, x1, y0, y1] of r.rects) c.fillRect(mx(x0), my(y1), (x1 - x0) * k, (y1 - y0) * k);
  }
  c.fillStyle = '#f4efe6';
  for (const [x0, x1, y0, y1] of data.walls[lv] || []) c.fillRect(mx(x0), my(y1), Math.max(1.5, (x1 - x0) * k), Math.max(1.5, (y1 - y0) * k));
  if (!TOUCH) {
    c.font = '9px system-ui'; c.textAlign = 'center'; c.fillStyle = 'rgba(244,239,230,0.75)';
    for (const r of data.rooms) {
      if (r.level !== lv || /Corridor|Porch|Hall$/.test(r.name)) continue;
      const [x0, x1, y0, y1] = r.rects[0];
      c.fillText(r.name.replace(' Washroom', ' WR'), mx((x0 + x1) / 2), my((y0 + y1) / 2) + 3);
    }
  }
  const p = toPlan(player.pos);
  c.save();
  c.translate(mx(p.x), my(p.y));
  c.rotate(-player.yaw);
  c.fillStyle = '#e8b25c';
  c.beginPath(); c.moveTo(0, -9); c.lineTo(6, 6); c.lineTo(0, 2); c.lineTo(-6, 6); c.closePath(); c.fill();
  c.restore();
  c.fillStyle = 'rgba(244,239,230,0.85)'; c.textAlign = 'left'; c.font = '600 11px system-ui';
  c.fillText(data.levels[lv].label.toUpperCase(), pad, 13);
}

// ------------------------------------------------------------------ loop (+ automatic quality)
const clock = new THREE.Clock();
let hudTimer = 0, lightTimer = 0, frames = 0, fpsAcc = 0, goodFor = 0, fps = 60;
function setPr(v) { pixelRatio = v; renderer.setPixelRatio(v); composer?.setPixelRatio(v); }
function adaptQuality(dt) {
  frames++; fpsAcc += dt;
  if (fpsAcc < 2) return;
  fps = frames / fpsAcc; frames = 0; fpsAcc = 0;
  if (document.hidden || !playing) return;
  if (fps < 45) {
    goodFor = 0;
    if (postOn) postOn = false;                         // drop the effects first, then resolution
    else if (pixelRatio > 0.75) setPr(Math.max(0.75, pixelRatio - 0.25));
  } else if (fps > 58 && pixelRatio < maxPr && (goodFor += 2) >= 8) { setPr(Math.min(maxPr, pixelRatio + 0.25)); goodFor = 0; }
}
renderer.setAnimationLoop(() => {
  const dt = Math.min(clock.getDelta(), 0.05);
  update(dt);
  adaptQuality(dt);
  if ((hudTimer += dt) > 0.1) { hudTimer = 0; drawHud(); }
  if ((lightTimer += dt) > 0.4) { lightTimer = 0; placeLights(); }
  if (postOn && composer) composer.render(); else renderer.render(scene, camera);
});

// ------------------------------------------------------------------ hooks for automated checks
window.game = {
  start() { testMode = true; start(); },
  hold(code, ms) { keys.add(code); return new Promise((r) => setTimeout(() => { keys.delete(code); r(this.state()); }, ms)); },
  key(code, key) { dispatchEvent(new KeyboardEvent('keydown', { code, key })); dispatchEvent(new KeyboardEvent('keyup', { code, key })); },
  look(yaw, pitch = 0) { player.yaw = yaw; player.pitch = pitch; },
  view(v) { viewChosen = true; view = v; },
  post(on) { if (on && !composer) buildComposer(); postOn = on; },
  spawn(i) { spawn(i); },
  step(seconds) { for (let i = 0, n = Math.round(seconds * 60); i < n; i++) update(1 / 60); return this.state(); },
  teleport(xft, yft, zft) { player.pos.copy(toWorld(xft, yft, zft)); player.vel.set(0, 0, 0); player.vy = 0; player.eyeY = player.pos.y + P.eye; placeLights(); },
  state() {
    const p = toPlan(player.pos);
    return { x: +p.x.toFixed(2), y: +p.y.toFixed(2), z: +(player.pos.y / FT).toFixed(2), room: roomAt(player.pos), level: levelOf(player.pos.y),
      fps: Math.round(fps), pr: pixelRatio, post: postOn, calls: renderer.info.render.calls, doors: doors.length, fans: fans.length,
      looking: !!lookedDoor(), view, jack: !!jack };
  },
};
