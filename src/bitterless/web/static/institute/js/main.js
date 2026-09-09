/**
 * BitterLess 3D Institute — self-contained WebGL walkthrough (no CDN deps).
 * Zones: research desk / thread wall, model room, archive photo wall, Eastern Zhou materials.
 */
const canvas = document.getElementById("c");

function el(tag, attrs = {}, children = []) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "className") n.className = v;
    else if (k === "text") n.textContent = v;
    else if (k.startsWith("on") && typeof v === "function") n.addEventListener(k.slice(2).toLowerCase(), v);
    else if (v === true) n.setAttribute(k, "");
    else if (v !== false && v != null) n.setAttribute(k, v);
  }
  for (const c of children) n.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  return n;
}

function buildHUD() {
  const hud = el("div", { id: "hud" });
  hud.appendChild(
    el("header", {}, [
      el("div", { className: "brand", text: "BitterLess · 东周研究所" }),
      el("div", { className: "sub", text: "研究室 · 艺术工作室 · 档案 · 博物馆 — geek + artist" }),
    ])
  );
  const threadPanel = el("section", { id: "thread-panel", className: "panel" }, [
    el("h2", { text: "Research Thread" }),
    el("div", { id: "thread-meta", className: "meta", text: "加载中…" }),
    el("ol", { id: "thread-steps" }),
  ]);
  const inspectPanel = el("section", { id: "inspect-panel", className: "panel" }, [
    el("h2", { text: "检视" }),
    el("div", { id: "inspect-body", className: "meta", text: "走近物件，或点击标注查看 provenance。" }),
  ]);
  const footer = el("footer", { className: "controls" }, [
    el("button", { id: "btn-cycle", type: "button", text: "跑一轮研究循环" }),
    el("button", { id: "btn-reset", type: "button", className: "ghost", text: "重置实验室" }),
    el("a", { className: "ghost link", href: "/", text: "← 经典 Web" }),
    el("span", { className: "hint", text: "WASD 移动 · 鼠标拖曳环视 · 点击物件 · 滚轮无效(锁定视角)" }),
  ]);
  hud.appendChild(threadPanel);
  hud.appendChild(inspectPanel);
  hud.appendChild(footer);
  document.body.appendChild(hud);
  document.body.appendChild(el("div", { id: "zone-toast", hidden: true }));
}

buildHUD();

// -------------------- API --------------------
let state = null;

async function fetchState() {
  const r = await fetch("/api/state");
  state = await r.json();
  renderThread(state);
  syncLabels(state);
  return state;
}

async function runCycle() {
  const r = await fetch("/api/cycle", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  state = await r.json();
  renderThread(state);
  syncLabels(state);
  showToast("Research cycle #" + state.cycle_count + " · tick " + state.tick);
  return state;
}

async function resetLab() {
  const r = await fetch("/api/reset", { method: "POST" });
  state = await r.json();
  renderThread(state);
  syncLabels(state);
  showToast("实验室已重置");
}

function renderThread(s) {
  const t = s.research_thread || {};
  const meta = document.getElementById("thread-meta");
  const dims = (t.current_focus_dims || []).join(", ") || "—";
  meta.textContent = [
    "研究员: " + (t.researcher_name || "—"),
    "tick: " + s.tick + " · cycles: " + s.cycle_count,
    "问题: " + (t.current_problem || "—"),
    "模型: " + (t.current_model_summary || "—"),
    "假设: " + (t.current_hypothesis || "（尚未）"),
    "聚焦: " + dims,
    "时间线: " + ((s.timeline && s.timeline.mode) || "canonical"),
  ].join("\n");
  const ol = document.getElementById("thread-steps");
  ol.innerHTML = "";
  for (const step of (t.steps || []).slice(-8)) {
    const li = document.createElement("li");
    const ph = document.createElement("span");
    ph.className = "phase";
    ph.textContent = "[" + step.phase + "] ";
    li.appendChild(ph);
    li.appendChild(document.createTextNode((step.content || "").slice(0, 120)));
    ol.appendChild(li);
  }
}

function showInspect(text) {
  document.getElementById("inspect-body").textContent = text;
}

let toastTimer = null;
function showToast(msg) {
  const z = document.getElementById("zone-toast");
  z.hidden = false;
  z.textContent = msg;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { z.hidden = true; }, 2200);
}

document.getElementById("btn-cycle").addEventListener("click", () => runCycle().catch(console.error));
document.getElementById("btn-reset").addEventListener("click", () => resetLab().catch(console.error));

// -------------------- math --------------------
function mat4Identity() {
  return new Float32Array([1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]);
}
function mat4Multiply(a, b) {
  const o = new Float32Array(16);
  for (let c = 0; c < 4; c++) {
    for (let r = 0; r < 4; r++) {
      o[c*4+r] = a[r]*b[c*4] + a[4+r]*b[c*4+1] + a[8+r]*b[c*4+2] + a[12+r]*b[c*4+3];
    }
  }
  return o;
}
function mat4Perspective(fovy, aspect, near, far) {
  const f = 1 / Math.tan(fovy / 2);
  const nf = 1 / (near - far);
  const o = new Float32Array(16);
  o[0] = f / aspect; o[5] = f; o[10] = (far + near) * nf; o[11] = -1;
  o[14] = 2 * far * near * nf;
  return o;
}
function mat4Translate(x, y, z) {
  const o = mat4Identity(); o[12]=x; o[13]=y; o[14]=z; return o;
}
function mat4Scale(x, y, z) {
  const o = mat4Identity(); o[0]=x; o[5]=y; o[10]=z; return o;
}
function mat4LookAt(eye, target, up) {
  let zx = eye[0]-target[0], zy = eye[1]-target[1], zz = eye[2]-target[2];
  let len = Math.hypot(zx, zy, zz) || 1; zx/=len; zy/=len; zz/=len;
  let xx = up[1]*zz - up[2]*zy, xy = up[2]*zx - up[0]*zz, xz = up[0]*zy - up[1]*zx;
  len = Math.hypot(xx, xy, xz) || 1; xx/=len; xy/=len; xz/=len;
  const yx = zy*xz - zz*xy, yy = zz*xx - zx*xz, yz = zx*xy - zy*xx;
  const o = mat4Identity();
  o[0]=xx; o[1]=yx; o[2]=zx;
  o[4]=xy; o[5]=yy; o[6]=zy;
  o[8]=xz; o[9]=yz; o[10]=zz;
  o[12]=-(xx*eye[0]+xy*eye[1]+xz*eye[2]);
  o[13]=-(yx*eye[0]+yy*eye[1]+yz*eye[2]);
  o[14]=-(zx*eye[0]+zy*eye[1]+zz*eye[2]);
  return o;
}

const VS = `attribute vec3 aPos; attribute vec3 aCol;
uniform mat4 uMVP; varying vec3 vCol;
void main(){ vCol=aCol; gl_Position=uMVP*vec4(aPos,1.0); }`;
const FS = `precision mediump float; varying vec3 vCol;
void main(){ gl_FragColor=vec4(vCol,1.0); }`;

function compile(gl, type, src) {
  const s = gl.createShader(type);
  gl.shaderSource(s, src); gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
  return s;
}

function unitCube() {
  // 24 verts (unique normals/colors per face), positions + colors interleaved later
  const p = [
    // +x
    1,-1,-1, 1,1,-1, 1,1,1, 1,-1,-1, 1,1,1, 1,-1,1,
    // -x
    -1,-1,1, -1,1,1, -1,1,-1, -1,-1,1, -1,1,-1, -1,-1,-1,
    // +y
    -1,1,-1, -1,1,1, 1,1,1, -1,1,-1, 1,1,1, 1,1,-1,
    // -y
    -1,-1,1, -1,-1,-1, 1,-1,-1, -1,-1,1, 1,-1,-1, 1,-1,1,
    // +z
    -1,-1,1, 1,-1,1, 1,1,1, -1,-1,1, 1,1,1, -1,1,1,
    // -z
    1,-1,-1, -1,-1,-1, -1,1,-1, 1,-1,-1, -1,1,-1, 1,1,-1,
  ];
  return new Float32Array(p);
}

// -------------------- scene objects --------------------
/** @type {{id:string,kind:string,x:number,y:number,z:number,sx:number,sy:number,sz:number,color:[number,number,number],label:string,info:string,zone:string}[]} */
let objects = [];

function addBox(o) {
  objects.push({
    id: o.id, kind: o.kind || "prop",
    x: o.x, y: o.y ?? 0, z: o.z,
    sx: o.sx ?? 1, sy: o.sy ?? 1, sz: o.sz ?? 1,
    color: o.color || [0.55, 0.42, 0.28],
    label: o.label || o.id,
    info: o.info || o.label || o.id,
    zone: o.zone || "",
  });
}

function buildRoom() {
  objects = [];
  // Floor slabs as visual zones
  addBox({ id: "floor", x: 0, y: -0.05, z: 0, sx: 14, sy: 0.1, sz: 10, color: [0.28, 0.2, 0.14], label: "地板", zone: "hall", info: "研究所大厅 — extended mind" });
  // Walls
  addBox({ id: "wall-n", x: 0, y: 2, z: -5, sx: 14, sy: 4, sz: 0.2, color: [0.36, 0.28, 0.2], label: "北墙", zone: "hall" });
  addBox({ id: "wall-s", x: 0, y: 2, z: 5, sx: 14, sy: 4, sz: 0.2, color: [0.34, 0.26, 0.18], label: "南墙", zone: "hall" });
  addBox({ id: "wall-w", x: -7, y: 2, z: 0, sx: 0.2, sy: 4, sz: 10, color: [0.33, 0.25, 0.17], label: "西墙", zone: "hall" });
  addBox({ id: "wall-e", x: 7, y: 2, z: 0, sx: 0.2, sy: 4, sz: 10, color: [0.33, 0.25, 0.17], label: "东墙", zone: "hall" });

  // Research desk (SW)
  addBox({ id: "desk", x: -4.5, y: 0.45, z: 2.5, sx: 2.2, sy: 0.9, sz: 1.1, color: [0.42, 0.28, 0.16], label: "研究桌", zone: "research", info: "Research desk — 主研究员的连续线索落在这里" });
  addBox({ id: "lamp", x: -3.6, y: 1.15, z: 2.5, sx: 0.15, sy: 0.5, sz: 0.15, color: [0.85, 0.7, 0.4], label: "台灯", zone: "research" });
  // Thread wall panels
  for (let i = 0; i < 5; i++) {
    addBox({
      id: "thread-" + i, x: -6.6, y: 1.4 + (i % 2) * 0.15, z: -1.5 + i * 0.85,
      sx: 0.08, sy: 1.1, sz: 0.7,
      color: [0.72, 0.62, 0.42],
      label: "Thread 板 " + (i + 1),
      zone: "research",
      info: "Research Thread wall — 等待 live 状态填充",
      kind: "thread",
    });
  }

  // Model room (NE) — sealed failed models
  const sealedSeed = [
    { id: "M-003", title: "商人=贪婪", epitaph: "标签式自我验证；已封存为反面教材" },
    { id: "M-007", title: "统一全图精度", epitaph: "资源耗尽；多尺度被证明必要" },
    { id: "M-012", title: "死亡即删除", epitaph: "违背「人死媒介留」；封存" },
  ];
  sealedSeed.forEach((m, i) => {
    addBox({
      id: "model-" + m.id, x: 4.2 + (i % 2) * 1.4, y: 0.7, z: -2.8 + Math.floor(i / 2) * 1.5,
      sx: 0.55, sy: 1.4, sz: 0.55,
      color: [0.35, 0.38, 0.45],
      label: m.id + " 封存",
      zone: "models",
      kind: "sealed",
      info: "封存模型 " + m.id + "\n标题: " + m.title + "\n碑文: " + m.epitaph + "\nstatus: sealed",
    });
  });
  addBox({ id: "model-plinth", x: 4.8, y: 0.15, z: -2.2, sx: 3.2, sy: 0.3, sz: 2.8, color: [0.3, 0.24, 0.18], label: "模型室台座", zone: "models" });

  // Archive / photo wall (NW) — 显影
  for (let i = 0; i < 3; i++) {
    addBox({
      id: "photo-" + i, x: -5.5 + i * 1.3, y: 1.6, z: -4.7,
      sx: 0.95, sy: 1.1, sz: 0.08,
      color: [0.55, 0.48, 0.38],
      label: "显影 " + (i + 1),
      zone: "archive",
      kind: "xianying",
      info: "显影框 — provenance 待同步",
    });
  }

  // Eastern Zhou materials (center-east): bamboo slips + sand table
  for (let i = 0; i < 4; i++) {
    addBox({
      id: "slip-" + i, x: 1.2 + i * 0.35, y: 0.55, z: 2.8,
      sx: 0.12, sy: 0.08, sz: 0.9,
      color: [0.62, 0.5, 0.28],
      label: "简牍",
      zone: "materials",
      kind: "slip",
      info: "竹简 — 东周材料侵入研究所",
    });
  }
  addBox({
    id: "sand-table", x: 2.2, y: 0.55, z: 1.2, sx: 2.4, sy: 0.7, sz: 1.6,
    color: [0.48, 0.4, 0.28], label: "小邑沙盘", zone: "materials", kind: "sand",
    info: "沙盘 — 低分辨率空间近似；非全图精度",
  });
  // sand table nodes
  [[0.8, 0.2], [0.4, 0.5], [0.45, 0.65]].forEach((n, i) => {
    addBox({
      id: "node-" + i, x: 1.4 + n[0] * 1.6, y: 0.95, z: 0.6 + n[1] * 1.2,
      sx: 0.18, sy: 0.18, sz: 0.18, color: [0.7, 0.35, 0.25],
      label: "邑点", zone: "materials", kind: "sand-node",
      info: "沙盘节点",
    });
  });
}

function syncLabels(s) {
  if (!s) return;
  // Update thread panels
  const steps = (s.research_thread && s.research_thread.steps) || [];
  objects.filter((o) => o.kind === "thread").forEach((o, i) => {
    const step = steps[steps.length - 1 - i];
    if (step) {
      o.label = step.phase;
      o.info = "Research Thread\nphase: " + step.phase + "\n" + (step.content || "") + "\ntick: " + step.tick;
    } else {
      const t = s.research_thread || {};
      o.info = "问题: " + (t.current_problem || "—") + "\n模型: " + (t.current_model_summary || "—");
    }
  });
  // Sealed models from API
  (s.sealed_models || []).forEach((m) => {
    const o = objects.find((x) => x.id === "model-" + m.id);
    if (o) {
      o.info = "封存模型 " + m.id + "\n标题: " + m.title + "\n碑文: " + m.epitaph + "\nstatus: " + m.status;
    }
  });
  // Photo wall / 显影
  (s.photo_wall || []).slice(0, 3).forEach((p, i) => {
    const o = objects.find((x) => x.id === "photo-" + i);
    if (o) {
      o.label = p.title;
      o.info = [
        "显影: " + p.title,
        "caption: " + p.caption,
        "viewpoint: " + p.viewpoint,
        "tick: " + p.tick,
        "provenance: " + p.provenance,
        "model: " + (p.model_note || ""),
        "constraints: " + (p.constraints || []).join("; "),
        "（非穿越摄影：史料约束 + 模型 + 视点 + 时间 → 投影）",
      ].join("\n");
    }
  });
  // Slips
  const slips = (s.materials && s.materials.bamboo_slips) || [];
  objects.filter((o) => o.kind === "slip").forEach((o, i) => {
    const slip = slips[i % Math.max(slips.length, 1)];
    if (slip) o.info = "简牍 " + slip.id + "\n" + slip.text + "\nchannel: " + slip.channel;
  });
  const sand = s.materials && s.materials.sand_table;
  const sandObj = objects.find((o) => o.id === "sand-table");
  if (sand && sandObj) {
    sandObj.info = sand.title + "\n" + sand.note + "\nnodes: " + (sand.nodes || []).map((n) => n.label).join(", ");
  }
  // compression on desk
  const desk = objects.find((o) => o.id === "desk");
  if (desk && s.compression_snapshot) {
    const lines = Object.values(s.compression_snapshot).map((c) => c.name + ": " + JSON.stringify(c.tiers));
    desk.info = "研究桌 · 人物压缩快照\n" + (lines.join("\n") || "（跑一轮循环后可见）") + "\nfocus: " + JSON.stringify(s.focus || {});
  }
}

// -------------------- renderer + controls --------------------
const gl = canvas.getContext("webgl", { antialias: true });
if (!gl) {
  showInspect("WebGL unavailable in this browser.");
  throw new Error("no webgl");
}

const prog = gl.createProgram();
gl.attachShader(prog, compile(gl, gl.VERTEX_SHADER, VS));
gl.attachShader(prog, compile(gl, gl.FRAGMENT_SHADER, FS));
gl.linkProgram(prog);
if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog));
gl.useProgram(prog);

const aPos = gl.getAttribLocation(prog, "aPos");
const aCol = gl.getAttribLocation(prog, "aCol");
const uMVP = gl.getUniformLocation(prog, "uMVP");

const cubePos = unitCube();
const buf = gl.createBuffer();
gl.bindBuffer(gl.ARRAY_BUFFER, buf);

function meshForColor(rgb) {
  const n = cubePos.length / 3;
  const data = new Float32Array(n * 6);
  const shade = [1.0, 0.92, 0.85, 0.75, 0.95, 0.7];
  for (let i = 0; i < n; i++) {
    const face = Math.floor(i / 6);
    const s = shade[face] || 1;
    data[i*6] = cubePos[i*3];
    data[i*6+1] = cubePos[i*3+1];
    data[i*6+2] = cubePos[i*3+2];
    data[i*6+3] = rgb[0] * s;
    data[i*6+4] = rgb[1] * s;
    data[i*6+5] = rgb[2] * s;
  }
  return data;
}

gl.enable(gl.DEPTH_TEST);
gl.clearColor(0.12, 0.09, 0.07, 1);

const cam = { x: 0, y: 1.6, z: 3.5, yaw: 0, pitch: -0.12 };
const keys = {};
let dragging = false, lastX = 0, lastY = 0;
let lastZone = "";

window.addEventListener("keydown", (e) => { keys[e.code] = true; });
window.addEventListener("keyup", (e) => { keys[e.code] = false; });
canvas.addEventListener("mousedown", (e) => {
  if (e.button === 0) { dragging = true; lastX = e.clientX; lastY = e.clientY; }
});
window.addEventListener("mouseup", () => { dragging = false; });
window.addEventListener("mousemove", (e) => {
  if (!dragging) return;
  const dx = e.clientX - lastX, dy = e.clientY - lastY;
  lastX = e.clientX; lastY = e.clientY;
  cam.yaw -= dx * 0.005;
  cam.pitch -= dy * 0.005;
  cam.pitch = Math.max(-1.2, Math.min(1.2, cam.pitch));
});
canvas.addEventListener("click", (e) => {
  const hit = pickObject(e.clientX, e.clientY);
  if (hit) {
    showInspect(hit.info);
    showToast(hit.label);
  }
});

function resize() {
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = Math.floor(canvas.clientWidth * dpr);
  canvas.height = Math.floor(canvas.clientHeight * dpr);
  gl.viewport(0, 0, canvas.width, canvas.height);
}
window.addEventListener("resize", resize);
resize();

function forward() {
  return [Math.sin(cam.yaw) * Math.cos(cam.pitch), Math.sin(cam.pitch), Math.cos(cam.yaw) * Math.cos(cam.pitch)];
}

function updateCam(dt) {
  const speed = (keys.ShiftLeft || keys.ShiftRight ? 6 : 3) * dt;
  const f = forward();
  const flat = Math.hypot(f[0], f[2]) || 1;
  const fx = f[0] / flat, fz = f[2] / flat;
  const rx = fz, rz = -fx;
  if (keys.KeyW) { cam.x += fx * speed; cam.z += fz * speed; }
  if (keys.KeyS) { cam.x -= fx * speed; cam.z -= fz * speed; }
  if (keys.KeyA) { cam.x -= rx * speed; cam.z -= rz * speed; }
  if (keys.KeyD) { cam.x += rx * speed; cam.z += rz * speed; }
  cam.x = Math.max(-6.2, Math.min(6.2, cam.x));
  cam.z = Math.max(-4.2, Math.min(4.2, cam.z));
  // zone toast
  let zone = "hall";
  if (cam.x < -2.5 && cam.z > 0.5) zone = "research";
  else if (cam.x > 2.5 && cam.z < 0) zone = "models";
  else if (cam.z < -2.5) zone = "archive";
  else if (cam.x > 0 && cam.z > 0.8) zone = "materials";
  if (zone !== lastZone) {
    lastZone = zone;
    const names = {
      hall: "研究所大厅",
      research: "研究桌 / Research Thread 墙",
      models: "模型室 · 封存失败模型",
      archive: "档案 / 显影墙",
      materials: "东周材料 · 简牍与沙盘",
    };
    showToast(names[zone] || zone);
  }
}

function drawObject(o, viewProj) {
  const model = mat4Multiply(
    mat4Translate(o.x, o.y, o.z),
    mat4Scale(o.sx, o.sy, o.sz)
  );
  const mvp = mat4Multiply(viewProj, model);
  const data = meshForColor(o.color);
  gl.bufferData(gl.ARRAY_BUFFER, data, gl.DYNAMIC_DRAW);
  gl.enableVertexAttribArray(aPos);
  gl.vertexAttribPointer(aPos, 3, gl.FLOAT, false, 24, 0);
  gl.enableVertexAttribArray(aCol);
  gl.vertexAttribPointer(aCol, 3, gl.FLOAT, false, 24, 12);
  gl.uniformMatrix4fv(uMVP, false, mvp);
  gl.drawArrays(gl.TRIANGLES, 0, data.length / 6);
}

function pickObject(clientX, clientY) {
  // crude ray vs AABB
  const rect = canvas.getBoundingClientRect();
  const ndcX = ((clientX - rect.left) / rect.width) * 2 - 1;
  const ndcY = -(((clientY - rect.top) / rect.height) * 2 - 1);
  const f = forward();
  // approximate: cast from camera along look, bias by ndc
  const right = [Math.cos(cam.yaw), 0, -Math.sin(cam.yaw)];
  const up = [0, 1, 0];
  const dir = [
    f[0] + right[0] * ndcX * 0.6 + up[0] * ndcY * 0.4,
    f[1] + right[1] * ndcX * 0.6 + up[1] * ndcY * 0.4,
    f[2] + right[2] * ndcX * 0.6 + up[2] * ndcY * 0.4,
  ];
  const len = Math.hypot(dir[0], dir[1], dir[2]) || 1;
  dir[0]/=len; dir[1]/=len; dir[2]/=len;
  let best = null, bestT = 1e9;
  for (const o of objects) {
    if (o.id.startsWith("wall") || o.id === "floor") continue;
    const min = [o.x - o.sx, o.y - o.sy, o.z - o.sz];
    const max = [o.x + o.sx, o.y + o.sy, o.z + o.sz];
    let tmin = 0, tmax = 40;
    for (let a = 0; a < 3; a++) {
      const origin = a === 0 ? cam.x : a === 1 ? cam.y : cam.z;
      const d = dir[a];
      if (Math.abs(d) < 1e-6) {
        if (origin < min[a] || origin > max[a]) { tmin = 1e9; break; }
        continue;
      }
      let t1 = (min[a] - origin) / d, t2 = (max[a] - origin) / d;
      if (t1 > t2) { const tmp=t1; t1=t2; t2=tmp; }
      tmin = Math.max(tmin, t1); tmax = Math.min(tmax, t2);
      if (tmin > tmax) break;
    }
    if (tmin <= tmax && tmin < bestT && tmin > 0.1) { bestT = tmin; best = o; }
  }
  return best;
}

let lastT = performance.now();
function frame(now) {
  const dt = Math.min(0.05, (now - lastT) / 1000);
  lastT = now;
  updateCam(dt);
  gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
  const aspect = canvas.width / Math.max(canvas.height, 1);
  const proj = mat4Perspective(Math.PI / 3, aspect, 0.1, 80);
  const f = forward();
  const view = mat4LookAt(
    [cam.x, cam.y, cam.z],
    [cam.x + f[0], cam.y + f[1], cam.z + f[2]],
    [0, 1, 0]
  );
  const viewProj = mat4Multiply(proj, view);
  for (const o of objects) drawObject(o, viewProj);
  requestAnimationFrame(frame);
}

buildRoom();
fetchState()
  .then(() => showToast("进入东周研究所 · WASD 走动"))
  .catch((e) => showInspect("无法加载 /api/state: " + e));
requestAnimationFrame(frame);
