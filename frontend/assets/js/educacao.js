// Base de Conhecimento / Diagnósticos por Componente
const DIAGNOSTICOS = {
    "Gabinete": {
        erros: "Botão Power com mau contato ou acúmulo de poeira nos filtros de ar.",
        solucao: "Verifique os cabos do Painel Frontal conectados à placa-mãe e realize a limpeza periódica das saídas de ar."
    },
    "Placa-mãe": {
        erros: "Curto-circuito, BIOS corrompida ou capacitores estufados.",
        solucao: "Faça o reset da BIOS (Clear CMOS), verifique os espaçadores do gabinete e teste com outra fonte de alimentação."
    },
    "Processador": {
        erros: "Superaquecimento (Overheating) ou pinos dobrados.",
        solucao: "Substitua a pasta térmica, limpe o cooler e certifique-se de que o sistema de refrigeração está firmemente instalado."
    },
    "Módulos de RAM": {
        erros: "Tela azul (BSOD), apitos de erro na inicialização ou memória não reconhecida.",
        solucao: "Limpe os contatos dourados com uma borracha escolar macia e teste os módulos em slots diferentes."
    },
    "Placa de vídeo": {
        erros: "Artefatos visuais na tela, ausência de vídeo ou ventoinhas paradas.",
        solucao: "Verifique se os cabos de alimentação PCIe estão bem conectados e atualize os drivers de vídeo."
    },
    "Fonte de alimentação": {
        erros: "Computador desliga sozinho em carga alta ou não liga.",
        solucao: "Utilize um testador de fonte para verificar as tensões de 12V, 5V e 3.3V antes de substituir a unidade."
    },
    "HD/SSD": {
        erros: "Lentidão extrema, erros de I/O ou sistema operacional não encontrado.",
        solucao: "Verifique a saúde do disco com diagnósticos S.M.A.R.T. e troque o cabo Sata ou o slot M.2."
    }
};

const BODY = "#DCE3EE", DARK = "#2E3A4E", ACCENT = "#2563EB", PCB = "#1E3A5F", GOLD = "#D4A73C", FRAME = "#3A4860";

function makeMat(color, disposables, emissive) {
  const mat = new THREE.MeshStandardMaterial({ color, roughness: 0.45, metalness: 0.15 });
  if (emissive) {
    mat.emissive = new THREE.Color(emissive);
    mat.emissiveIntensity = 0.55;
  }
  disposables.push(mat);
  return mat;
}
function makeBox(w, h, d, color, disposables, emissive) {
  const geo = new THREE.BoxGeometry(w, h, d);
  disposables.push(geo);
  return new THREE.Mesh(geo, makeMat(color, disposables, emissive));
}
function makeCyl(r, h, color, disposables, axis) {
  const geo = new THREE.CylinderGeometry(r, r, h, 18);
  disposables.push(geo);
  const mesh = new THREE.Mesh(geo, makeMat(color, disposables));
  if (axis === "z") mesh.rotation.x = Math.PI / 2;
  return mesh;
}

function buildCase(p) {
  const g = new THREE.Group();
  const bottom = makeBox(2.3, 0.1, 2.7, DARK, p); bottom.position.y = 0.05; g.add(bottom);
  const back = makeBox(2.3, 2.5, 0.08, FRAME, p); back.position.set(0, 1.3, -1.32); g.add(back);
  [-1.12, 1.12].forEach((x) => {
    const rail = makeBox(0.07, 2.5, 0.07, FRAME, p);
    rail.position.set(x, 1.3, 1.32);
    g.add(rail);
  });
  return g;
}

function buildMobo(p) {
  const g = new THREE.Group();
  const board = makeBox(1.9, 1.9, 0.07, PCB, p); g.add(board);
  const io = makeBox(0.5, 0.35, 0.16, BODY, p); io.position.set(-0.55, 0.7, 0.1); g.add(io);
  const chipset = makeBox(0.45, 0.45, 0.05, DARK, p); chipset.position.set(0.55, -0.45, 0.06); g.add(chipset);
  [[0.15, 0.2], [0.4, 0.2], [0.27, -0.1]].forEach(([x, y]) => {
    const cap = makeCyl(0.06, 0.14, DARK, p, "z"); cap.position.set(x, y, 0.1); g.add(cap);
  });
  return g;
}

function buildCpu(p) {
  const g = new THREE.Group();
  const chip = makeBox(0.42, 0.42, 0.1, ACCENT, p, ACCENT); g.add(chip);
  const cooler = makeCyl(0.32, 0.16, BODY, p, "z"); cooler.position.z = 0.14; g.add(cooler);
  const hub = makeCyl(0.09, 0.06, DARK, p, "z"); hub.position.z = 0.24; g.add(hub);
  for (let i = 0; i < 3; i++) {
    const blade = makeBox(0.52, 0.05, 0.05, ACCENT, p);
    blade.rotation.z = (i * Math.PI) / 3;
    blade.position.z = 0.24;
    g.add(blade);
  }
  return g;
}

function buildRam(p) {
  const g = new THREE.Group();
  [0, 0.24].forEach((x) => {
    const stick = makeBox(0.1, 0.95, 0.3, PCB, p); stick.position.set(x, 0, 0); g.add(stick);
    const spreader = makeBox(0.12, 0.5, 0.34, BODY, p); spreader.position.set(x, 0.18, 0); g.add(spreader);
    const pins = makeBox(0.08, 0.1, 0.26, GOLD, p); pins.position.set(x, -0.4, 0); g.add(pins);
  });
  return g;
}

function buildGpu(p) {
  const g = new THREE.Group();
  const shroud = makeBox(1.35, 0.45, 0.85, DARK, p); g.add(shroud);
  const plate = makeBox(1.39, 0.06, 0.89, BODY, p); plate.position.y = 0.28; g.add(plate);
  [-0.32, 0.32].forEach((x) => {
    const fan = makeCyl(0.24, 0.05, ACCENT, p, "y"); fan.position.set(x, 0.33, 0); g.add(fan);
    const hub = makeCyl(0.08, 0.06, BODY, p, "y"); hub.position.set(x, 0.34, 0); g.add(hub);
  });
  const pcb = makeBox(1.25, 0.32, 0.08, PCB, p); pcb.position.set(0, -0.05, -0.45); g.add(pcb);
  return g;
}

function buildPsu(p) {
  const g = new THREE.Group();
  const box = makeBox(0.75, 0.65, 1.0, DARK, p); g.add(box);
  const label = makeBox(0.5, 0.38, 0.03, BODY, p); label.position.set(0, 0, 0.52); g.add(label);
  const fan = makeCyl(0.24, 0.05, BODY, p, "y"); fan.position.y = 0.35; g.add(fan);
  const led = makeBox(0.08, 0.05, 0.04, ACCENT, p, ACCENT); led.position.set(0.25, -0.18, 0.52); g.add(led);
  return g;
}

function buildSsd(p) {
  const g = new THREE.Group();
  const box = makeBox(0.6, 0.14, 0.95, DARK, p); g.add(box);
  const label = makeBox(0.42, 0.05, 0.62, BODY, p); label.position.y = 0.09; g.add(label);
  const trim = makeBox(0.6, 0.05, 0.95, ACCENT, p, ACCENT); trim.position.y = -0.09; g.add(trim);
  return g;
}

const PART_DEFS = [
  { key: "Gabinete", build: buildCase, pos: [0, 0, 0], label: [0, 2.95, -0.5] },
  { key: "Placa-mãe", build: buildMobo, pos: [0, 1.25, -1.2], label: [0, 2.55, -1.1] },
  { key: "Processador", build: buildCpu, pos: [-0.35, 1.7, -1.05], label: [-0.35, 2.4, -0.85] },
  { key: "Módulos de RAM", build: buildRam, pos: [0.55, 1.5, -0.9], label: [0.55, 2.25, -0.8] },
  { key: "Placa de vídeo", build: buildGpu, pos: [0.35, 0.72, -0.3], label: [0.35, 1.4, -0.2] },
  { key: "Fonte de alimentação", build: buildPsu, pos: [-0.62, 0.45, 0.65], label: [-0.62, 1.05, 0.65] },
  { key: "HD/SSD", build: buildSsd, pos: [0.68, 0.15, 0.6], label: [0.68, 0.65, 0.6] },
];

function makeLabelSprite(name, disposables) {
  const canvas = document.createElement("canvas");
  canvas.width = 384;
  canvas.height = 88;
  const ctx = canvas.getContext("2d");
  ctx.textAlign = "center";
  ctx.fillStyle = "#1E1B18";
  ctx.font = "700 24px Inter, sans-serif";
  ctx.fillText(name, 192, 40);
  const tex = new THREE.CanvasTexture(canvas);
  const mat = new THREE.SpriteMaterial({ map: tex, transparent: true });
  disposables.push(tex, mat);
  const sprite = new THREE.Sprite(mat);
  sprite.scale.set(1.55, 0.35, 1);
  return sprite;
}

// Atualizar o painel lateral de diagnósticos
function renderDiagnostico(key) {
  const container = document.getElementById("painelDiagnostico");
  if (!key || !DIAGNOSTICOS[key]) return;

  const data = DIAGNOSTICOS[key];
  container.innerHTML = `
    <div class="diagnostico-info">
      <h4>${key}</h4>
      <h5>Falhas Comuns:</h5>
      <p>${data.erros}</p>
      <h5 style="color: #2563EB;">Solução Recomendada:</h5>
      <p>${data.solucao}</p>
    </div>
  `;
}

// Inicializador da Cena 3D
function initPcExplorer3D() {
  const mount = document.getElementById("pcExplorer3D");
  if (!mount) return;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  mount.appendChild(renderer.domElement);

  scene.add(new THREE.AmbientLight(0xffffff, 0.9));
  const keyLight = new THREE.DirectionalLight(0xffffff, 1.2);
  keyLight.position.set(3, 6, 5);
  scene.add(keyLight);
  const fillLight = new THREE.DirectionalLight(0xcfe0ff, 0.5);
  fillLight.position.set(-5, 2, -4);
  scene.add(fillLight);

  const group = new THREE.Group();
  scene.add(group);

  const disposables = [];
  const meshesByKey = {};
  const rayTargets = [];

  PART_DEFS.forEach(({ key, build, pos, label }) => {
    const part = build(disposables);
    part.position.set(...pos);
    const meshes = [];
    part.traverse((o) => {
      if (o.isMesh) {
        o.userData.partKey = key;
        meshes.push(o);
        rayTargets.push(o);
      }
    });
    meshesByKey[key] = meshes;
    group.add(part);

    const sprite = makeLabelSprite(key, disposables);
    sprite.position.set(...label);
    group.add(sprite);
  });

  const originals = new Map();
  let highlighted = null;

  const setHighlight = (next) => {
    if (next === highlighted) return;
    if (highlighted) {
      meshesByKey[highlighted].forEach((m) => {
        const o = originals.get(m);
        m.material.emissive.setHex(o.em);
        m.material.emissiveIntensity = o.int;
      });
    }
    if (next) {
      meshesByKey[next].forEach((m) => {
        if (!originals.has(m)) originals.set(m, { em: m.material.emissive.getHex(), int: m.material.emissiveIntensity });
        m.material.emissive.setHex(0xef4444);
        m.material.emissiveIntensity = 0.85;
      });
      renderDiagnostico(next); // Atualiza o painel ao passar o mouse
    }
    highlighted = next;
  };

  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();

  const pick = (e) => {
    const rect = mount.getBoundingClientRect();
    pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(pointer, camera);
    const hits = raycaster.intersectObjects(rayTargets, false);
    return hits.length ? hits[0].object.userData.partKey : null;
  };

  let tiltY = 0, targetY = 0;
  mount.addEventListener("pointermove", (e) => {
    const rect = mount.getBoundingClientRect();
    targetY = ((e.clientX - rect.left) / rect.width - 0.5) * 0.35;
    const partKey = pick(e);
    setHighlight(partKey);
    mount.style.cursor = partKey ? "pointer" : "default";
  });

  mount.addEventListener("pointerleave", () => {
    targetY = 0;
    mount.style.cursor = "default";
    setHighlight(null);
  });

  const resize = () => {
    const w = mount.clientWidth || 1;
    const h = mount.clientHeight || 520;
    renderer.setSize(w, h);
    const aspect = w / h;
    camera.aspect = aspect;
    const fitZ = 1.6 / (Math.tan((21 * Math.PI) / 180) * Math.max(aspect, 0.1));
    camera.position.set(0, 3.4, Math.max(7, fitZ));
    camera.lookAt(0, 1.2, 0);
    camera.updateProjectionMatrix();
  };
  window.addEventListener("resize", resize);
  resize();

  const clock = new THREE.Clock();
  function animate() {
    requestAnimationFrame(animate);
    const t = clock.getElapsedTime();
    tiltY += (targetY - tiltY) * 0.06;
    group.rotation.y = Math.sin(t * 0.3) * 0.1 + tiltY;
    renderer.render(scene, camera);
  }
  animate();
}

// Inicializar quando o documento carregar
document.addEventListener("DOMContentLoaded", initPcExplorer3D);