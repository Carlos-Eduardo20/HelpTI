import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { createPcCase } from './pc-case.js';
import { createPcComponents } from './pc-components.js';
import type { ComponentName, PcPart } from './pc-types.js';

(() => {
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
  // Enquadramento frontal e ligeiramente lateral, como no modelo de referência.
  camera.position.set(6.4, 4.3, 9.5);
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

  const parts: PcPart[] = [...createPcCase(scene), ...createPcComponents(scene)];

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
  let hoverOutline: THREE.LineSegments | null = null;
  const clearHoverOutline = () => {
    if (!hoverOutline) return;
    scene.remove(hoverOutline);
    hoverOutline.geometry.dispose();
    (hoverOutline.material as THREE.Material).dispose();
    hoverOutline = null;
  };
  renderer.domElement.addEventListener('pointermove', event => {
    const bounds = renderer.domElement.getBoundingClientRect();
    pointer.set(((event.clientX - bounds.left) / bounds.width) * 2 - 1, -((event.clientY - bounds.top) / bounds.height) * 2 + 1);
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObjects(parts, false)[0];
    clearHoverOutline();
    if (!hit) return;
    const hoveredMesh = hit.object as THREE.Mesh;
    const edges = new THREE.EdgesGeometry(hoveredMesh.geometry, 12);
    hoverOutline = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: 0x76d9ff, transparent: true, opacity: 0.95, depthTest: false }));
    hoverOutline.position.copy(hoveredMesh.position);
    hoverOutline.rotation.copy(hoveredMesh.rotation);
    hoverOutline.scale.copy(hoveredMesh.scale);
    hoverOutline.renderOrder = 10;
    scene.add(hoverOutline);
  });
  renderer.domElement.addEventListener('pointerleave', clearHoverOutline);
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
