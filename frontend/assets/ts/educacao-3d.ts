import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { createPcCase } from './pc-case.js';
import { createPcComponents } from './pc-components.js';
import type { ComponentName, PcPart } from './pc-types.js';

(() => {
  type Diagnosis = { erros: string[]; solucao: string[] };
  type Outline = THREE.LineSegments<THREE.BufferGeometry, THREE.LineBasicMaterial>;

  const container = document.getElementById('canvas-pc-3d');
  const componentList = document.getElementById('component-list');
  const diagnosisContent = document.getElementById('diagnosis-content');
  if (!(container instanceof HTMLElement) || !(componentList instanceof HTMLElement) || !(diagnosisContent instanceof HTMLElement)) return;
  const pcContainer = container;
  const componentsElement = componentList;
  const diagnosisPanel = diagnosisContent;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 80);
  camera.position.set(5.7, 4.1, 8.5);

  const renderer = new THREE.WebGLRenderer({
    antialias: true,
    alpha: true,
    powerPreference: 'high-performance',
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.14;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.setSize(pcContainer.clientWidth, pcContainer.clientHeight);
  renderer.domElement.setAttribute('aria-hidden', 'true');
  renderer.domElement.className = 'pc-3d-canvas';
  pcContainer.appendChild(renderer.domElement);

  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

  pmrem.dispose();

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.055;
  controls.enablePan = false;
  controls.minDistance = 6.4;
  controls.maxDistance = 12.5;
  controls.minPolarAngle = 0.32;
  controls.maxPolarAngle = 1.48;
  controls.target.set(0, 1.93, 0);
  controls.update();

  scene.add(new THREE.HemisphereLight(0xd8f5f1, 0x28323b, 1.35));

  const keyLight = new THREE.DirectionalLight(0xfff4df, 4.1);
  keyLight.position.set(4.5, 7.5, 5.5);
  keyLight.castShadow = true;
  keyLight.shadow.mapSize.set(2048, 2048);
  keyLight.shadow.camera.left = -5;
  keyLight.shadow.camera.right = 5;
  keyLight.shadow.camera.top = 7;
  keyLight.shadow.camera.bottom = -3;
  keyLight.shadow.camera.near = 0.5;
  keyLight.shadow.camera.far = 20;
  keyLight.shadow.bias = -0.0002;
  keyLight.shadow.radius = 5;
  scene.add(keyLight);

  const rimLight = new THREE.DirectionalLight(0x71daca, 2.8);
  rimLight.position.set(-4.5, 3.5, -4);
  scene.add(rimLight);

  const frontFill = new THREE.PointLight(0x8ab9ff, 34, 12, 2);
  frontFill.position.set(2.5, 3.1, 4.5);
  scene.add(frontFill);

  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(200, 200),
    new THREE.MeshStandardMaterial({ color: 0x111a20, roughness: 0.78, metalness: 0.22 }),
  );
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -0.065;
  floor.receiveShadow = true;
  scene.add(floor);

  const parts: PcPart[] = [...createPcCase(scene), ...createPcComponents(scene)];
  const componentNames: ComponentName[] = [
    'Gabinete',
    'Placa-mãe',
    'Processador',
    'Módulos de RAM',
    'Placa de vídeo',
    'Fonte de alimentação',
    'HD/SSD',
  ];

  let diagnostics: Record<string, Diagnosis> = {};
  let selected: ComponentName | null = null;
  let hovered: ComponentName | null = null;
  let pointerStart: { x: number; y: number } | null = null;
  let dragged = false;

  const outlines = new Map<ComponentName, Outline[]>();
  parts.forEach(mesh => {
    const component = mesh.userData.component as ComponentName | undefined;
    if (!component || !mesh.userData.outline) return;

    const material = new THREE.LineBasicMaterial({
      color: 0x53e3d0,
      transparent: true,
      opacity: 0.98,
      depthTest: true,
      toneMapped: false,
    });
    const outline: Outline = new THREE.LineSegments(new THREE.EdgesGeometry(mesh.geometry, 22), material);
    outline.scale.setScalar(1.014);
    outline.renderOrder = 20;
    outline.visible = false;
    mesh.add(outline);

    const group = outlines.get(component) ?? [];
    group.push(outline);
    outlines.set(component, group);
  });

  function updateOutlines(): void {
    outlines.forEach((group, name) => {
      const isHovered = hovered === name;
      const isSelected = selected === name;
      group.forEach(outline => {
        outline.visible = isHovered || isSelected;
        outline.material.color.setHex(isHovered ? 0x9cf8ff : 0x48d8b7);
        outline.material.opacity = isHovered ? 1 : 0.9;
      });
    });
  }

  function setHovered(name: ComponentName | null): void {
    if (hovered === name) return;
    hovered = name;
    updateOutlines();
  }

  function showDiagnosis(name: ComponentName): void {
    diagnosisPanel.replaceChildren();
    const data = diagnostics[name];
    if (!data) return;

    const sections: [string, string[]][] = [
      ['Falhas comuns', data.erros],
      ['Possíveis soluções', data.solucao],
    ];
    sections.forEach(([heading, entries]) => {
      const section = document.createElement('section');
      const title = document.createElement('h4');
      const list = document.createElement('ul');
      title.textContent = heading;
      if (heading === 'Possíveis soluções') title.classList.add('solution-title');
      entries.forEach(entry => {
        const item = document.createElement('li');
        item.textContent = entry;
        list.append(item);
      });
      section.append(title, list);
      diagnosisPanel.append(section);
    });

    const form = document.createElement('form');
    form.className = 'diagnosis-ticket-form';
    form.innerHTML = `
      <div class="diagnosis-ticket-heading">
        <span class="diagnosis-step">PRÓXIMO PASSO</span>
        <h4>O problema continua?</h4>
        <p>Registre o sintoma e o que já verificou. Essas informações seguem para a triagem do suporte.</p>
      </div>
      <label for="diagnosis-symptom">O que está acontecendo?</label>
      <textarea id="diagnosis-symptom" name="sintoma" rows="3" required maxlength="1200" placeholder="Ex.: o computador reinicia quando abro um programa pesado"></textarea>
      <label for="diagnosis-attempts">O que você já tentou? <span>(opcional)</span></label>
      <textarea id="diagnosis-attempts" name="etapasTentadas" rows="2" maxlength="1200" placeholder="Ex.: conferi os cabos e reiniciei o computador"></textarea>
      <button type="submit" class="diagnosis-ticket-button">Continuar em um chamado <span aria-hidden="true">→</span></button>
    `;
    form.addEventListener('submit', event => {
      event.preventDefault();
      if (!form.reportValidity()) return;
      const dados = new FormData(form);
      const pacote = {
        componente: name,
        sintoma: String(dados.get('sintoma') || '').trim(),
        etapasTentadas: String(dados.get('etapasTentadas') || '').trim(),
        verificacoes: data.erros,
        solucoes: data.solucao,
      };
      try {
        sessionStorage.setItem('helpti:diagnosticoChamado', JSON.stringify(pacote));
        const destino = new URL('./chamados.html', window.location.href);
        destino.searchParams.set('diagnostico', '1');
        window.location.href = destino.toString();
      } catch (error) {
        diagnosisPanel.querySelector('.diagnosis-ticket-error')?.remove();
        const aviso = document.createElement('p');
        aviso.className = 'diagnosis-ticket-error';
        aviso.setAttribute('role', 'alert');
        aviso.textContent = 'Não foi possível preparar o chamado. Copie as informações e tente novamente.';
        form.append(aviso);
      }
    });
    diagnosisPanel.append(form);
  }

  function selectComponent(name: ComponentName): void {
    selected = name;
    updateOutlines();
    showDiagnosis(name);
    componentsElement.querySelectorAll<HTMLButtonElement>('button').forEach(button => {
      button.setAttribute('aria-pressed', String(button.dataset.component === name));
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
    button.addEventListener('pointerenter', () => setHovered(name));
    button.addEventListener('pointerleave', () => setHovered(null));
    button.addEventListener('focus', () => setHovered(name));
    button.addEventListener('blur', () => setHovered(null));
    componentsElement.append(button);
  });

  fetch('/api/educacao/diagnosticos')
    .then(response => {
      if (!response.ok) throw new Error('HTTP ' + response.status);
      return response.json();
    })
    .then((data: Record<string, Diagnosis>) => {
      diagnostics = data;
      if (selected) showDiagnosis(selected);
    })
    .catch(error => {
      diagnosisPanel.textContent = 'Não foi possível carregar os diagnósticos.';
      console.error('[HelpTI] falha ao carregar diagnósticos', error);
    });

  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();

  function componentAt(clientX: number, clientY: number): ComponentName | null {
    const bounds = renderer.domElement.getBoundingClientRect();
    if (!bounds.width || !bounds.height) return null;
    pointer.set(
      ((clientX - bounds.left) / bounds.width) * 2 - 1,
      -((clientY - bounds.top) / bounds.height) * 2 + 1,
    );
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObjects(parts, false)[0];
    return (hit?.object.userData.component as ComponentName | undefined) ?? null;
  }

  renderer.domElement.addEventListener('pointerdown', event => {
    pointerStart = { x: event.clientX, y: event.clientY };
    dragged = false;
  });

  renderer.domElement.addEventListener('pointermove', event => {
    if (pointerStart) {
      const dx = event.clientX - pointerStart.x;
      const dy = event.clientY - pointerStart.y;
      if (Math.hypot(dx, dy) > 6) {
        dragged = true;
        renderer.domElement.style.cursor = 'grabbing';
        setHovered(null);
        return;
      }
    }

    const component = componentAt(event.clientX, event.clientY);
    setHovered(component);
    renderer.domElement.style.cursor = component ? 'pointer' : 'grab';
  });

  renderer.domElement.addEventListener('pointerup', () => {
    pointerStart = null;
    if (!dragged) renderer.domElement.style.cursor = 'grab';
  });

  renderer.domElement.addEventListener('pointercancel', () => {
    pointerStart = null;
    dragged = false;
    setHovered(null);
  });

  renderer.domElement.addEventListener('pointerleave', () => {
    pointerStart = null;
    renderer.domElement.style.cursor = 'grab';
    setHovered(null);
  });

  renderer.domElement.addEventListener('click', event => {
    if (dragged) {
      dragged = false;
      return;
    }
    const component = componentAt(event.clientX, event.clientY);
    if (component) selectComponent(component);
  });

  function resize(): void {
    const width = pcContainer.clientWidth;
    const height = pcContainer.clientHeight;
    if (!width || !height) return;
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
  }

  new ResizeObserver(resize).observe(pcContainer);

  function animate(): void {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  }
  animate();
})();
