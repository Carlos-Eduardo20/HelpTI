import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

(() => {
  type ComponentName = 'Gabinete' | 'Placa-mãe' | 'Processador' | 'Módulos de RAM' | 'Placa de vídeo' | 'Fonte de alimentação' | 'HD/SSD';
  type Diagnosis = { erros: string[]; solucao: string[] };
  const container = document.getElementById('canvas-pc-3d') as HTMLElement | null;
  const componentList = document.getElementById('component-list') as HTMLElement | null;
  const diagnosisContent = document.getElementById('diagnosis-content') as HTMLElement | null;
  if (!container || !componentList || !diagnosisContent) return;
  const pcContainer = container;
  const componentsElement = componentList;
  const diagnosisPanel = diagnosisContent;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#101720');
  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
  camera.position.set(6, 5, 7);
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.setSize(pcContainer.clientWidth, pcContainer.clientHeight);
  pcContainer.appendChild(renderer.domElement);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.target.set(0, 1.9, 0);
  controls.minDistance = 4;
  controls.maxDistance = 11;
  scene.add(new THREE.HemisphereLight(0xffffff, 0x667477, 2));
  const keyLight = new THREE.DirectionalLight(0xffffff, 2.4);
  keyLight.position.set(5, 8, 6);
  scene.add(keyLight);
  const fillLight = new THREE.DirectionalLight(0x61d7c6, 1.2);
  fillLight.position.set(-5, 3, -4);
  scene.add(fillLight);

  const materials = {
    case: new THREE.MeshStandardMaterial({ color: 0x161d25, metalness: 0.72, roughness: 0.26 }),
    panel: new THREE.MeshStandardMaterial({ color: 0x101923, metalness: 0.25, roughness: 0.18, transparent: true, opacity: 0.12, depthWrite: false }),
    board: new THREE.MeshStandardMaterial({ color: 0x147d70, metalness: 0.28, roughness: 0.5 }),
    cpu: new THREE.MeshStandardMaterial({ color: 0xf1a944, metalness: 0.65, roughness: 0.28 }),
    ram: new THREE.MeshStandardMaterial({ color: 0x53b9a7, metalness: 0.35, roughness: 0.3 }),
    gpu: new THREE.MeshStandardMaterial({ color: 0x527de0, metalness: 0.5, roughness: 0.28 }),
    psu: new THREE.MeshStandardMaterial({ color: 0xa8b7b8, metalness: 0.65, roughness: 0.3 }),
    storage: new THREE.MeshStandardMaterial({ color: 0xd16b53, metalness: 0.4, roughness: 0.35 })
  };
  const fanHubMaterial = new THREE.MeshStandardMaterial({ color: 0x222d38, metalness: 0.7, roughness: 0.26 });
  const parts: THREE.Mesh<THREE.BufferGeometry, THREE.MeshStandardMaterial>[] = [];
  const addPart = (
    name: ComponentName,
    geometry: THREE.BufferGeometry,
    material: THREE.MeshStandardMaterial,
    position: [number, number, number]
  ) => {
    const mesh = new THREE.Mesh<THREE.BufferGeometry, THREE.MeshStandardMaterial>(geometry, material);
    mesh.position.set(...position);
    mesh.userData.component = name;
    scene.add(mesh);
    parts.push(mesh);
    return mesh;
  };
  const box = (
    name: ComponentName,
    size: [number, number, number],
    material: THREE.MeshStandardMaterial,
    position: [number, number, number]
  ) => addPart(name, new THREE.BoxGeometry(...size), material, position);

  // Gabinete aberto para deixar os componentes internos visíveis e selecionáveis.
  box('Gabinete', [2.5, 3.65, 0.12], materials.case, [0, 2, -0.78]);
  box('Gabinete', [0.16, 4, 1.65], materials.case, [-1.17, 2, 0]);
  box('Gabinete', [0.16, 4, 1.65], materials.case, [1.17, 2, 0]);
  box('Gabinete', [2.5, 0.16, 1.65], materials.case, [0, 0.08, 0]);
  box('Gabinete', [2.5, 0.16, 1.65], materials.case, [0, 3.92, 0]);
  const sideGlass = new THREE.Mesh(new THREE.BoxGeometry(2.18, 3.66, 0.045), materials.panel);
  sideGlass.position.set(0, 2, 0.85);
  scene.add(sideGlass);
  const frontGlass = new THREE.Mesh(new THREE.BoxGeometry(0.045, 3.66, 1.55), materials.panel);
  frontGlass.position.set(1.17, 2, 0);
  scene.add(frontGlass);
  // Moldura de vidro e acabamento frontal do gabinete.
  box('Gabinete', [0.055, 3.68, 0.06], materials.case, [-1.09, 2, 0.9]);
  box('Gabinete', [0.055, 3.68, 0.06], materials.case, [1.09, 2, 0.9]);
  box('Gabinete', [2.18, 0.055, 0.06], materials.case, [0, 0.18, 0.9]);
  box('Gabinete', [2.18, 0.055, 0.06], materials.case, [0, 3.82, 0.9]);
  box('Placa-mãe', [1.72, 2.65, 0.12], materials.board, [-0.25, 2.35, 0.54]);
  box('Processador', [0.68, 0.2, 0.68], materials.cpu, [-0.2, 2.8, 0.68]);
  const cpuCooler = addPart('Processador', new THREE.CylinderGeometry(0.39, 0.39, 0.17, 48), materials.case, [-0.2, 2.96, 0.72]);
  cpuCooler.rotation.x = Math.PI / 2;
  const cpuRingMaterial = new THREE.MeshStandardMaterial({ color: 0x63f2d0, emissive: 0x20b99e, emissiveIntensity: 1.5, metalness: 0.3, roughness: 0.24 });
  addPart('Processador', new THREE.TorusGeometry(0.31, 0.035, 12, 48), cpuRingMaterial, [-0.2, 2.96, 0.82]);
  // Bloco e mangueiras do water cooler DeepCool Castle 240.
  const tubeMaterial = new THREE.MeshStandardMaterial({ color: 0x151b22, metalness: 0.42, roughness: 0.36 });
  const tubes = [
    new THREE.CatmullRomCurve3([new THREE.Vector3(-0.48, 2.96, 0.72), new THREE.Vector3(-0.76, 3.1, 0.5), new THREE.Vector3(-0.78, 3.52, 0.3)]),
    new THREE.CatmullRomCurve3([new THREE.Vector3(0.08, 2.96, 0.72), new THREE.Vector3(0.22, 3.12, 0.52), new THREE.Vector3(0.3, 3.52, 0.3)])
  ];
  tubes.forEach(curve => addPart('Processador', new THREE.TubeGeometry(curve, 24, 0.045, 8, false), tubeMaterial, [0, 0, 0]));
  box('Processador', [1.55, 0.13, 0.62], materials.case, [-0.2, 3.65, 0.3]);
  [-0.65, 0.25].forEach(x => {
    addPart('Processador', new THREE.TorusGeometry(0.25, 0.028, 10, 36), cpuRingMaterial, [x, 3.53, 0.63]);
    const radiatorFan = addPart('Processador', new THREE.CylinderGeometry(0.19, 0.19, 0.07, 32), fanHubMaterial, [x, 3.53, 0.61]);
    radiatorFan.rotation.x = Math.PI / 2;
  });
  box('Módulos de RAM', [0.19, 1.48, 0.2], materials.ram, [0.38, 2.55, 0.67]);
  box('Módulos de RAM', [0.19, 1.48, 0.2], materials.ram, [0.64, 2.55, 0.67]);
  box('Placa-mãe', [0.12, 0.46, 0.26], materials.case, [-0.88, 3.15, 0.65]);
  box('Placa-mãe', [0.12, 0.46, 0.26], materials.case, [-0.88, 2.58, 0.65]);
  box('Placa de vídeo', [1.82, 0.48, 0.72], materials.gpu, [-0.05, 1.55, 0.48]);
  const gpuFanMaterial = new THREE.MeshStandardMaterial({ color: 0x17212b, metalness: 0.6, roughness: 0.3 });
  const gpuRingMaterial = new THREE.MeshStandardMaterial({ color: 0x7f9cff, emissive: 0x304fbd, emissiveIntensity: 0.75, metalness: 0.4, roughness: 0.25 });
  [-0.55, 0.32].forEach(x => {
    const fan = addPart('Placa de vídeo', new THREE.CylinderGeometry(0.2, 0.2, 0.08, 32), gpuFanMaterial, [x, 1.55, 0.89]);
    fan.rotation.x = Math.PI / 2;
    addPart('Placa de vídeo', new THREE.TorusGeometry(0.2, 0.025, 10, 32), gpuRingMaterial, [x, 1.55, 0.95]);
  });
  box('Gabinete', [2.2, 0.62, 1.45], materials.case, [0, 0.48, 0]);
  box('Fonte de alimentação', [1.65, 0.5, 0.9], materials.psu, [0.25, 0.48, -0.12]);
  box('HD/SSD', [0.85, 0.18, 0.62], materials.storage, [-0.65, 0.9, 0.55]);
  const fanMaterial = new THREE.MeshStandardMaterial({ color: 0x63f2d0, emissive: 0x168d7c, emissiveIntensity: 1.15, metalness: 0.24, roughness: 0.34 });
  [0.82, 1.92, 3.02].forEach(y => {
    const fanRing = addPart('Gabinete', new THREE.TorusGeometry(0.42, 0.045, 12, 48), fanMaterial, [1.02, y, 0]);
    fanRing.rotation.y = Math.PI / 2;
    const innerRing = addPart('Gabinete', new THREE.TorusGeometry(0.34, 0.012, 8, 40), gpuRingMaterial, [1.01, y, 0]);
    innerRing.rotation.y = Math.PI / 2;
    const hub = addPart('Gabinete', new THREE.CylinderGeometry(0.11, 0.11, 0.08, 24), fanHubMaterial, [0.98, y, 0]);
    hub.rotation.z = Math.PI / 2;
  });
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(200, 200), new THREE.MeshStandardMaterial({ color: 0x101720, metalness: 0.15, roughness: 0.85 }));
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -0.03;
  scene.add(floor);

  const componentNames: ComponentName[] = ['Gabinete', 'Placa-mãe', 'Processador', 'Módulos de RAM', 'Placa de vídeo', 'Fonte de alimentação', 'HD/SSD'];
  let diagnostics: Record<string, Diagnosis> = {};
  let selected: ComponentName | null = null;
  let highlighted: THREE.Mesh<THREE.BufferGeometry, THREE.MeshStandardMaterial>[] = [];
  const originalMaterials = new Map<THREE.Mesh<THREE.BufferGeometry, THREE.MeshStandardMaterial>, THREE.MeshStandardMaterial>();

  function selectComponent(name: ComponentName | null) {
    highlighted.forEach(mesh => {
      const originalMaterial = originalMaterials.get(mesh);
      if (originalMaterial) mesh.material = originalMaterial;
    });
    highlighted = [];
    selected = name;
    if (name) {
      highlighted = parts.filter(mesh => mesh.userData.component === name);
      highlighted.forEach(mesh => {
        if (!originalMaterials.has(mesh)) originalMaterials.set(mesh, mesh.material);
        mesh.material = mesh.material.clone();
        mesh.material.emissive = new THREE.Color(0x0f766e);
        mesh.material.emissiveIntensity = 0.65;
      });
      showDiagnosis(name);
    } else diagnosisPanel.replaceChildren();
    componentsElement.querySelectorAll('button').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.component === name)));
  }

  function showDiagnosis(name: ComponentName) {
    const data = diagnostics[name];
    if (!data) return;
    diagnosisPanel.replaceChildren();
    const sections: [string, string[]][] = [['Falhas comuns', data.erros], ['Possíveis soluções', data.solucao]];
    sections.forEach(([heading, entries]) => {
      const section = document.createElement('section');
      const title = document.createElement('h4');
      const list = document.createElement('ul');
      title.textContent = heading;
      if (heading === 'Possíveis soluções') title.classList.add('solution-title');
      entries.forEach(entry => { const item = document.createElement('li'); item.textContent = entry; list.append(item); });
      section.append(title, list);
      diagnosisPanel.append(section);
    });
  }

  componentNames.forEach(name => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'component-button';
    button.dataset.component = name;
    button.textContent = name;
    button.setAttribute('aria-pressed', 'false');
    button.addEventListener('click', () => selectComponent(name));
    componentsElement.append(button);
  });

  fetch('/api/educacao/diagnosticos')
    .then(response => { if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.json(); })
    .then(data => { diagnostics = data; if (selected) showDiagnosis(selected); })
    .catch(error => { diagnosisPanel.textContent = 'Não foi possível carregar os diagnósticos.'; console.error('[HelpTI] falha ao carregar diagnósticos', error); });

  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();
  renderer.domElement.addEventListener('click', event => {
    const bounds = renderer.domElement.getBoundingClientRect();
    pointer.set(((event.clientX - bounds.left) / bounds.width) * 2 - 1, -((event.clientY - bounds.top) / bounds.height) * 2 + 1);
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObjects(parts, false)[0];
    if (hit) selectComponent(hit.object.userData.component);
  });

  function resize() {
    const width = pcContainer.clientWidth;
    const height = pcContainer.clientHeight;
    if (!width || !height) return;
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
  }
  new ResizeObserver(resize).observe(pcContainer);
  function animate() { requestAnimationFrame(animate); controls.update(); renderer.render(scene, camera); }
  animate();

})();
