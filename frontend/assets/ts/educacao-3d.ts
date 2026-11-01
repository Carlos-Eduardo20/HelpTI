import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { createPcCase } from './pc-case.js';
import { createPcComponents } from './pc-components.js';
import type { ComponentName, PcPart } from './pc-types.js';

(() => {
  type Diagnosis = { erros: string[]; solucao: string[] };
  type Outline = THREE.LineSegments<THREE.BufferGeometry, THREE.LineBasicMaterial>;
  type ComponentAssembly = {
    group: THREE.Group;
    offset: THREE.Vector3;
    center: THREE.Vector3;
  };
  type RgbMaterialState = {
    material: THREE.MeshStandardMaterial;
    color: THREE.Color;
    emissive: THREE.Color;
    emissiveIntensity: number;
  };

  const container = document.getElementById('canvas-pc-3d');
  const componentList = document.getElementById('component-list');
  const diagnosisContent = document.getElementById('diagnosis-content');
  const modelStatus = document.getElementById('pc-model-status');
  const fallbackImage = document.getElementById('pc-model-fallback');
  if (
    !(container instanceof HTMLElement)
    || !(componentList instanceof HTMLElement)
    || !(diagnosisContent instanceof HTMLElement)
    || !(modelStatus instanceof HTMLElement)
    || !(fallbackImage instanceof HTMLImageElement)
  ) return;
  const pcContainer = container;
  const componentsElement = componentList;
  const diagnosisPanel = diagnosisContent;
  const statusElement = modelStatus;
  const fallbackElement = fallbackImage;

  const scene = new THREE.Scene();
  const clock = new THREE.Clock();
  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 80);
  camera.position.set(4.2, 3.1, 6.3);

  const renderer = new THREE.WebGLRenderer({
    antialias: true,
    alpha: true,
    powerPreference: 'high-performance',
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.22;
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
  controls.enablePan = true;
  controls.minDistance = 5.8;
  controls.maxDistance = 11.5;
  controls.minPolarAngle = 0.32;
  controls.maxPolarAngle = 1.48;
  controls.target.set(0, 2.02, 0);
  controls.update();

  scene.add(new THREE.HemisphereLight(0xe4fff8, 0x39444c, 1.55));

  const keyLight = new THREE.DirectionalLight(0xfff4e2, 4.6);
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

  const rimLight = new THREE.DirectionalLight(0x65f0d5, 3.2);
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

  const explodeOffsets: Record<ComponentName, THREE.Vector3> = {
    'Gabinete': new THREE.Vector3(0, 0.12, -0.52),
    'Placa-mãe': new THREE.Vector3(-0.08, 0.1, -0.58),
    'Processador': new THREE.Vector3(0, 0.56, 0.3),
    'Módulos de RAM': new THREE.Vector3(-0.55, 0.38, 0.2),
    'Placa de vídeo': new THREE.Vector3(0, -0.36, 0.75),
    'Fonte de alimentação': new THREE.Vector3(0.55, -0.52, -0.3),
    'HD/SSD': new THREE.Vector3(-0.76, 0.45, -0.12),
  };
  const componentGroups = new Map<ComponentName, ComponentAssembly>();
  const sceneMeshes = scene.children.filter(
    (child): child is THREE.Mesh => child instanceof THREE.Mesh && typeof child.userData.component === 'string',
  );
  const fanBlades = sceneMeshes.filter(mesh => mesh.userData.spin === true);
  sceneMeshes.forEach(mesh => {
    const component = mesh.userData.component as ComponentName;
    if (!componentNames.includes(component)) return;
    let assembly = componentGroups.get(component);
    if (!assembly) {
      const group = new THREE.Group();
      group.name = `componente-${component}`;
      scene.add(group);
      assembly = { group, offset: explodeOffsets[component].clone(), center: new THREE.Vector3() };
      componentGroups.set(component, assembly);
    }
    assembly.group.add(mesh);
  });

  componentGroups.forEach(assembly => {
    new THREE.Box3().setFromObject(assembly.group).getCenter(assembly.center);
  });

  const labelLayer = document.createElement('div');
  labelLayer.className = 'pc-label-layer';
  labelLayer.setAttribute('aria-hidden', 'true');
  pcContainer.appendChild(labelLayer);
  const labels = new Map<ComponentName, HTMLElement>();
  componentNames.forEach(name => {
    const label = document.createElement('span');
    label.className = 'pc-component-label';
    label.textContent = name;
    labelLayer.appendChild(label);
    labels.set(name, label);
  });

  const wireframeMaterials = new Map<THREE.MeshBasicMaterial | THREE.MeshStandardMaterial, boolean>();
  const rgbMaterials = new Map<THREE.MeshStandardMaterial, RgbMaterialState>();
  sceneMeshes.forEach(mesh => {
    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    materials.forEach(material => {
      if (material instanceof THREE.MeshBasicMaterial || material instanceof THREE.MeshStandardMaterial) {
        wireframeMaterials.set(material, material.wireframe);
      }
      if (material instanceof THREE.MeshStandardMaterial && material.userData.rgbAnimation && !rgbMaterials.has(material)) {
        rgbMaterials.set(material, {
          material,
          color: material.color.clone(),
          emissive: material.emissive.clone(),
          emissiveIntensity: material.emissiveIntensity,
        });
      }
    });
  });

  let diagnostics: Record<string, Diagnosis> = {};
  let selected: ComponentName | null = null;
  let hovered: ComponentName | null = null;
  let pointerStart: { x: number; y: number } | null = null;
  let dragged = false;
  let exploded = false;
  let caseHidden = false;
  let wireframeOn = false;
  let labelsOn = false;
  let rgbOn = false;
  let lastRgbRestore = false;
  let readyAnnounced = false;
  let contextLost = false;

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

  function setButtonState(button: HTMLElement | null, active: boolean): void {
    if (!(button instanceof HTMLButtonElement)) return;
    button.setAttribute('aria-pressed', String(active));
    button.classList.toggle('is-active', active);
  }

  function setWireframe(active: boolean): void {
    wireframeOn = active;
    wireframeMaterials.forEach((original, material) => {
      material.wireframe = active || original;
    });
    setButtonState(document.getElementById('pc-wireframe'), active);
  }

  function setCaseHidden(hidden: boolean): void {
    caseHidden = hidden;
    const caseGroup = componentGroups.get('Gabinete')?.group;
    if (caseGroup) caseGroup.visible = !hidden;
    const button = document.getElementById('pc-hide-case');
    setButtonState(button, hidden);
    if (button instanceof HTMLButtonElement) button.textContent = hidden ? 'Mostrar gabinete' : 'Ocultar gabinete';
    updateOutlines();
  }

  function resetCamera(): void {
    camera.position.set(4.2, 3.1, 6.3);
    controls.target.set(0, 2.02, 0);
    controls.autoRotate = false;
    controls.update();
    setButtonState(document.getElementById('pc-auto-rotate'), false);
  }

  const projectedLabelPosition = new THREE.Vector3();
  const placedLabels: Array<{ left: number; top: number; right: number; bottom: number }> = [];
  function updateLabels(): void {
    placedLabels.length = 0;
    labels.forEach((label, name) => {
      const assembly = componentGroups.get(name);
      const focused = selected === name || hovered === name;
      if ((!labelsOn && !focused) || !assembly || (caseHidden && name === 'Gabinete')) {
        label.hidden = true;
        return;
      }

      projectedLabelPosition.copy(assembly.center).add(assembly.group.position).project(camera);
      const x = (projectedLabelPosition.x * 0.5 + 0.5) * pcContainer.clientWidth;
      const y = (-projectedLabelPosition.y * 0.5 + 0.5) * pcContainer.clientHeight;
      const onScreen = projectedLabelPosition.z > -1 && projectedLabelPosition.z < 1
        && x >= 0 && x <= pcContainer.clientWidth && y >= 0 && y <= pcContainer.clientHeight;
      label.hidden = !onScreen;
      if (!onScreen) return;

      const width = label.offsetWidth;
      const height = label.offsetHeight;
      const padding = 5;
      const verticalOffsets = [0, -30, 30, -60, 60, -90, 90, -120, 120];
      const horizontalOffsets = [0, -42, 42, -84, 84];
      let placement: { x: number; y: number; left: number; top: number; right: number; bottom: number } | null = null;
      for (const verticalOffset of verticalOffsets) {
        for (const horizontalOffset of horizontalOffsets) {
          const candidateX = x + horizontalOffset;
          const candidateY = y + verticalOffset;
          const left = candidateX - width / 2;
          const top = candidateY - height / 2;
          const right = left + width;
          const bottom = top + height;
          const withinBounds = left >= 4 && right <= pcContainer.clientWidth - 4
            && top >= 4 && bottom <= pcContainer.clientHeight - 4;
          const overlaps = placedLabels.some(rect => left < rect.right + padding && right + padding > rect.left
            && top < rect.bottom + padding && bottom + padding > rect.top);
          if (withinBounds && !overlaps) {
            placement = { x: candidateX, y: candidateY, left, top, right, bottom };
            break;
          }
        }
        if (placement) break;
      }
      if (placement) {
        placedLabels.push(placement);
        label.style.transform = `translate(${placement.x}px, ${placement.y}px) translate(-50%, -50%)`;
      } else {
        label.style.transform = `translate(${x}px, ${y}px) translate(-50%, -50%)`;
      }
    });
  }

  function updateRgb(elapsed: number): void {
    if (!rgbOn) {
      if (lastRgbRestore) return;
      rgbMaterials.forEach(({ material, color, emissive, emissiveIntensity }) => {
        material.color.copy(color);
        material.emissive.copy(emissive);
        material.emissiveIntensity = emissiveIntensity;
        if (material.map) material.map.offset.x = 0;
        if (material.emissiveMap) material.emissiveMap.offset.x = 0;
      });
      lastRgbRestore = true;
      return;
    }

    lastRgbRestore = false;
    let index = 0;
    rgbMaterials.forEach(({ material }) => {
      const hue = (elapsed * 0.12 + index * 0.28) % 1;
      material.color.setHSL(hue, 0.78, 0.54);
      material.emissive.setHSL(hue, 0.82, 0.24);
      material.emissiveIntensity = 0.9;
      if (material.map) material.map.offset.x = (elapsed * 0.12) % 1;
      if (material.emissiveMap) material.emissiveMap.offset.x = (elapsed * 0.12) % 1;
      index += 1;
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

  document.getElementById('pc-reset-camera')?.addEventListener('click', () => {
    resetCamera();
    statusElement.textContent = 'Câmera restaurada.';
  });
  document.getElementById('pc-auto-rotate')?.addEventListener('click', event => {
    controls.autoRotate = !controls.autoRotate;
    setButtonState(event.currentTarget as HTMLElement, controls.autoRotate);
    statusElement.textContent = controls.autoRotate ? 'Rotação automática ativada.' : 'Rotação automática pausada.';
  });
  document.getElementById('pc-toggle-labels')?.addEventListener('click', event => {
    labelsOn = !labelsOn;
    setButtonState(event.currentTarget as HTMLElement, labelsOn);
    updateLabels();
    statusElement.textContent = labelsOn ? 'Rótulos dos componentes visíveis.' : 'Rótulos dos componentes ocultos.';
  });
  document.getElementById('pc-explode')?.addEventListener('click', event => {
    exploded = !exploded;
    setButtonState(event.currentTarget as HTMLElement, exploded);
    statusElement.textContent = exploded ? 'Componentes separados para inspeção.' : 'Componentes montados.';
  });
  document.getElementById('pc-hide-case')?.addEventListener('click', () => {
    setCaseHidden(!caseHidden);
    statusElement.textContent = caseHidden ? 'Gabinete oculto.' : 'Gabinete visível.';
  });
  document.getElementById('pc-wireframe')?.addEventListener('click', event => {
    setWireframe(!wireframeOn);
    statusElement.textContent = wireframeOn ? 'Modo aramado ativado.' : 'Modo aramado desativado.';
  });
  document.getElementById('pc-rgb')?.addEventListener('click', event => {
    rgbOn = !rgbOn;
    setButtonState(event.currentTarget as HTMLElement, rgbOn);
    lastRgbRestore = false;
    statusElement.textContent = rgbOn ? 'Iluminação RGB animada.' : 'Iluminação RGB pausada.';
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
  const explodeTarget = new THREE.Vector3();

  function componentAt(clientX: number, clientY: number): ComponentName | null {
    const bounds = renderer.domElement.getBoundingClientRect();
    if (!bounds.width || !bounds.height) return null;
    pointer.set(
      ((clientX - bounds.left) / bounds.width) * 2 - 1,
      -((clientY - bounds.top) / bounds.height) * 2 + 1,
    );
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObjects(parts, false).find(intersection => {
      const component = intersection.object.userData.component as ComponentName | undefined;
      return component !== 'Gabinete' || !caseHidden;
    });
    return (hit?.object.userData.component as ComponentName | undefined) ?? null;
  }

  renderer.domElement.addEventListener('webglcontextlost', event => {
    event.preventDefault();
    contextLost = true;
    fallbackElement.hidden = false;
    statusElement.textContent = 'A visualização 3D foi interrompida; exibindo o diagrama estático.';
  });
  renderer.domElement.addEventListener('webglcontextrestored', () => {
    contextLost = false;
    fallbackElement.hidden = true;
    statusElement.textContent = 'Visualização 3D restaurada.';
  });

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
    if (contextLost) return;
    const delta = clock.getDelta();
    controls.update(delta);
    fanBlades.forEach(blade => { blade.rotation.z += delta * 0.9; });
    const targetPosition = exploded ? 1 : 0;
    componentGroups.forEach(({ group, offset }) => {
      explodeTarget.copy(offset).multiplyScalar(targetPosition);
      group.position.lerp(explodeTarget, Math.min(1, delta * 4));
    });
    updateRgb(clock.elapsedTime);
    updateLabels();
    renderer.render(scene, camera);
    fallbackElement.hidden = true;
    if (!readyAnnounced) {
      pcContainer.dataset.modelReady = 'true';
      statusElement.textContent = 'Modelo 3D pronto. Arraste para girar e selecione uma peça.';
      readyAnnounced = true;
    }
  }
  animate();
})();
