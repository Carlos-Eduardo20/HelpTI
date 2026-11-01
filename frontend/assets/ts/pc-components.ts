import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import type { ComponentName, PcPart } from './pc-types.js';

type Vec3 = [number, number, number];

export function createPcComponents(scene: THREE.Scene): PcPart[] {
  const parts: PcPart[] = [];
  const boardMaterial = new THREE.MeshPhysicalMaterial({
    color: 0x17604f,
    metalness: 0.24,
    roughness: 0.45,
    clearcoat: 0.42,
    clearcoatRoughness: 0.28,
  });
  const blackMetal = new THREE.MeshPhysicalMaterial({
    color: 0x202b32,
    metalness: 0.68,
    roughness: 0.24,
    clearcoat: 0.52,
    clearcoatRoughness: 0.18,
  });
  const graphite = new THREE.MeshStandardMaterial({ color: 0x465760, metalness: 0.72, roughness: 0.25 });
  const aluminum = new THREE.MeshPhysicalMaterial({
    color: 0xc1cdd0,
    metalness: 0.88,
    roughness: 0.2,
    clearcoat: 0.35,
  });
  const copper = new THREE.MeshStandardMaterial({ color: 0xd59a53, metalness: 0.82, roughness: 0.24 });
  const teal = new THREE.MeshStandardMaterial({
    color: 0x1b8e86,
    emissive: 0x0e766e,
    emissiveIntensity: 0.5,
    metalness: 0.48,
    roughness: 0.3,
  });
  teal.userData.rgbAnimation = true;
  const coolantHose = new THREE.MeshStandardMaterial({ color: 0x111a20, metalness: 0.48, roughness: 0.34 });
  const radiatorFin = new THREE.MeshStandardMaterial({ color: 0x73848a, metalness: 0.78, roughness: 0.3 });
  const fanBlade = new THREE.MeshPhysicalMaterial({
    color: 0x53646d,
    metalness: 0.55,
    roughness: 0.25,
    clearcoat: 0.5,
    side: THREE.DoubleSide,
  });
  const fanFrame = new THREE.MeshStandardMaterial({ color: 0x1c2a30, metalness: 0.78, roughness: 0.22 });
  const screwMaterial = new THREE.MeshStandardMaterial({ color: 0x89969c, metalness: 0.9, roughness: 0.25 });
  const rgbCanvas = document.createElement('canvas');
  rgbCanvas.width = 512;
  rgbCanvas.height = 32;
  const rgbContext = rgbCanvas.getContext('2d');
  if (rgbContext) {
    const gradient = rgbContext.createLinearGradient(0, 0, rgbCanvas.width, 0);
    [0, 0.17, 0.34, 0.51, 0.68, 0.85, 1].forEach((stop, index) => {
      gradient.addColorStop(stop, `hsl(${index * 60}, 100%, 58%)`);
    });
    rgbContext.fillStyle = gradient;
    rgbContext.fillRect(0, 0, rgbCanvas.width, rgbCanvas.height);
  }
  const rgbTexture = new THREE.CanvasTexture(rgbCanvas);
  rgbTexture.colorSpace = THREE.SRGBColorSpace;
  rgbTexture.wrapS = THREE.RepeatWrapping;
  const rgbFanFrame = new THREE.MeshStandardMaterial({
    map: rgbTexture,
    emissive: 0xffffff,
    emissiveMap: rgbTexture,
    emissiveIntensity: 0.7,
    metalness: 0.12,
    roughness: 0.3,
  });
  rgbFanFrame.userData.rgbAnimation = true;

  const add = (
    geometry: THREE.BufferGeometry,
    material: THREE.Material,
    position: Vec3,
    component: ComponentName,
    outline = false,
  ): PcPart => {
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(position[0], position[1], position[2] + 0.18);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    mesh.userData.component = component;
    mesh.userData.outline = outline;
    scene.add(mesh);
    parts.push(mesh);
    return mesh;
  };

  const box = (
    size: Vec3,
    position: Vec3,
    material: THREE.Material,
    component: ComponentName,
    outline = false,
  ) => {
    const radius = Math.min(0.035, Math.min(...size) * 0.24);
    return add(new RoundedBoxGeometry(...size, 3, radius), material, position, component, outline);
  };

  const cylinder = (
    radius: number,
    length: number,
    position: Vec3,
    material: THREE.Material,
    component: ComponentName,
    faceForward = false,
  ) => {
    const mesh = add(new THREE.CylinderGeometry(radius, radius, length, 28), material, position, component);
    if (faceForward) mesh.rotation.x = Math.PI / 2;
    return mesh;
  };

  function fan(
    cx: number,
    cy: number,
    cz: number,
    radius: number,
    component: ComponentName,
    hubAccent: THREE.Material = teal,
    ringMaterial: THREE.Material = fanFrame,
  ): void {
    const ring = add(new THREE.TorusGeometry(radius * 0.91, radius * 0.075, 10, 48), ringMaterial, [cx, cy, cz], component);
    ring.userData.outline = true;
    add(new THREE.TorusGeometry(radius * 0.74, radius * 0.025, 8, 40), graphite, [cx, cy, cz - 0.012], component);

    const bladeShape = new THREE.Shape();
    bladeShape.moveTo(radius * 0.08, -radius * 0.04);
    bladeShape.quadraticCurveTo(radius * 0.36, radius * 0.08, radius * 0.82, radius * 0.66);
    bladeShape.quadraticCurveTo(radius * 0.88, radius * 0.84, radius * 0.68, radius * 0.77);
    bladeShape.quadraticCurveTo(radius * 0.26, radius * 0.58, radius * 0.04, radius * 0.16);
    bladeShape.quadraticCurveTo(-radius * 0.01, radius * 0.03, radius * 0.08, -radius * 0.04);
    const bladeGeometry = new THREE.ExtrudeGeometry(bladeShape, {
      depth: radius * 0.075,
      bevelEnabled: false,
      steps: 1,
      curveSegments: 10,
    });

    for (let index = 0; index < 7; index += 1) {
      const blade = add(bladeGeometry, fanBlade, [cx, cy, cz - radius * 0.12], component);
      blade.userData.spin = true;
      blade.rotation.z = (index / 7) * Math.PI * 2;
    }

    cylinder(radius * 0.31, radius * 0.22, [cx, cy, cz + radius * 0.04], aluminum, component, true);
    cylinder(radius * 0.18, radius * 0.23, [cx, cy, cz + radius * 0.055], blackMetal, component, true);
    const hubMark = add(
      new THREE.TorusGeometry(radius * 0.095, radius * 0.014, 6, 24),
      hubAccent,
      [cx, cy, cz + radius * 0.18],
      component,
    );
    hubMark.userData.outline = false;

    const screwOffset = radius * 0.72;
    [-1, 1].forEach(sx => {
      [-1, 1].forEach(sy => {
        cylinder(radius * 0.045, radius * 0.1, [cx + sx * screwOffset, cy + sy * screwOffset, cz + radius * 0.01], screwMaterial, component, true);
      });
    });
  }

  function labelTexture(title: string, subtitle: string): THREE.MeshBasicMaterial {
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 112;
    const context = canvas.getContext('2d');
    if (context) {
      const gradient = context.createLinearGradient(0, 0, 512, 112);
      gradient.addColorStop(0, '#14242b');
      gradient.addColorStop(1, '#0c1117');
      context.fillStyle = gradient;
      context.fillRect(0, 0, 512, 112);
      context.fillStyle = '#59d6c2';
      context.fillRect(28, 24, 5, 64);
      context.fillStyle = '#f2f7f6';
      context.font = '700 36px Arial';
      context.fillText(title, 52, 58);
      context.fillStyle = '#9ab2b6';
      context.font = '500 17px Arial';
      context.fillText(subtitle, 54, 86);
    }
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    return new THREE.MeshBasicMaterial({ map: texture, transparent: true, toneMapped: false, side: THREE.DoubleSide });
  }

  function addCable(
    points: Vec3[],
    radius: number,
    material: THREE.Material,
    component: ComponentName = 'Fonte de alimentação',
  ): void {
    const curve = new THREE.CatmullRomCurve3(points.map(point => new THREE.Vector3(...point)));
    add(new THREE.TubeGeometry(curve, 36, radius, 8, false), material, [0, 0, 0], component);
  }

  // Placa-mãe: PCB, trilhas de cobre, dissipadores do VRM e conectores.
  box([2.32, 3.02, 0.09], [0, 2.25, -0.78], boardMaterial, 'Placa-mãe', true);

  const traceMaterial = new THREE.MeshStandardMaterial({ color: 0xd4a45f, metalness: 0.7, roughness: 0.34 });
  const tracePaths: Vec3[][] = [
    [[-0.88, 1.05, -0.72], [-0.7, 1.35, -0.72], [-0.7, 1.9, -0.72], [-0.36, 2.12, -0.72]],
    [[0.98, 1.0, -0.72], [0.82, 1.24, -0.72], [0.82, 2.0, -0.72], [0.72, 2.24, -0.72]],
    [[-0.94, 2.6, -0.72], [-0.82, 2.76, -0.72], [-0.82, 3.36, -0.72], [-0.64, 3.52, -0.72]],
    [[0.88, 2.62, -0.72], [0.72, 2.78, -0.72], [0.72, 3.48, -0.72], [0.5, 3.61, -0.72]],
    [[-0.2, 1.0, -0.72], [-0.2, 1.56, -0.72], [0.12, 1.86, -0.72], [0.42, 1.86, -0.72]],
  ];
  tracePaths.forEach(points => {
    const curve = new THREE.CatmullRomCurve3(points.map(point => new THREE.Vector3(...point)));
    add(new THREE.TubeGeometry(curve, 24, 0.008, 5, false), traceMaterial, [0, 0, 0], 'Placa-mãe');
  });

  // Dissipadores e capacitores do circuito de alimentação.
  box([0.2, 0.72, 0.28], [-0.91, 3.27, -0.56], blackMetal, 'Placa-mãe');
  box([0.2, 0.48, 0.28], [-0.65, 3.39, -0.56], graphite, 'Placa-mãe');
  for (let index = 0; index < 6; index += 1) {
    const y = 2.93 + index * 0.075;
    box([0.22, 0.025, 0.27], [-0.91, y, -0.405], aluminum, 'Placa-mãe');
  }
  for (let index = 0; index < 5; index += 1) {
    cylinder(0.055, 0.16, [-0.72 + (index % 2) * 0.12, 3.05 + Math.floor(index / 2) * 0.16, -0.59], blackMetal, 'Placa-mãe', true);
  }
  box([0.16, 0.92, 0.28], [-1.02, 3.35, -0.55], graphite, 'Placa-mãe');
  box([0.12, 0.7, 0.035], [-1.02, 3.35, -0.382], blackMetal, 'Placa-mãe');
  for (let index = 0; index < 4; index += 1) {
    box([0.09, 0.12, 0.1], [-1.03, 3.04 + index * 0.2, -0.32], edgeMetalMaterial(), 'Placa-mãe');
  }

  // Soquete metálico do processador e bloco de contato.
  box([0.68, 0.66, 0.12], [0.47, 2.78, -0.64], graphite, 'Processador');
  box([0.52, 0.5, 0.055], [0.47, 2.78, -0.545], aluminum, 'Processador', true);
  box([0.44, 0.42, 0.018], [0.47, 2.78, -0.508], blackMetal, 'Processador');
  box([0.32, 0.3, 0.025], [0.47, 2.78, -0.486], aluminum, 'Processador');
  for (let index = 0; index < 4; index += 1) {
    box([0.035, 0.025, 0.018], [0.26 + index * 0.14, 2.48, -0.49], copper, 'Processador');
  }

  // Waterblock iluminado no processador e radiador AIO de 360 mm junto às ventoinhas frontais.
  box([0.62, 0.62, 0.22], [0.47, 2.78, -0.12], blackMetal, 'Processador', true);
  box([0.54, 0.54, 0.045], [0.47, 2.78, 0.015], graphite, 'Processador');
  add(new THREE.TorusGeometry(0.235, 0.027, 10, 48), rgbFanFrame, [0.47, 2.78, 0.045], 'Processador');
  add(new THREE.TorusGeometry(0.178, 0.012, 8, 40), teal, [0.47, 2.78, 0.055], 'Processador');
  cylinder(0.145, 0.075, [0.47, 2.78, 0.09], blackMetal, 'Processador', true);
  box([0.36, 0.16, 0.024], [0.47, 2.78, 0.14], labelTexture('HELP TI', 'AIO  /  360 mm'), 'Processador');

  box([0.22, 2.88, 0.54], [1.2, 2.38, 0.2], blackMetal, 'Processador', true);
  for (let index = 0; index < 14; index += 1) {
    const x = 1.105 + index * 0.014;
    box([0.009, 2.68, 0.025], [x, 2.38, 0.46], radiatorFin, 'Processador');
  }
  addCable([[0.7, 2.98, 0.13], [0.92, 3.02, 0.13], [1.25, 3.18, 0.17], [1.36, 3.52, 0.22], [1.25, 3.68, 0.25]], 0.043, coolantHose, 'Processador');
  addCable([[0.7, 2.58, 0.13], [0.96, 2.48, 0.13], [1.34, 2.38, 0.17], [1.36, 1.2, 0.22], [1.25, 1.08, 0.25]], 0.043, coolantHose, 'Processador');
  addCable([[0.7, 2.9, 0.18], [0.92, 3.0, 0.18], [1.24, 3.18, 0.22], [1.34, 3.52, 0.25], [1.24, 3.68, 0.28]], 0.013, teal, 'Processador');

  // Dois módulos DDR com dissipador, contatos dourados e barra difusora.
  [-0.52, -0.27].forEach((x, index) => {
    box([0.17, 0.96, 0.13], [x, 2.68, -0.52], blackMetal, 'Módulos de RAM', true);
    box([0.135, 0.79, 0.035], [x, 2.69, -0.432], index === 0 ? graphite : blackMetal, 'Módulos de RAM');
    box([0.13, 0.035, 0.035], [x, 3.17, -0.43], rgbFanFrame, 'Módulos de RAM');
    for (let contact = 0; contact < 7; contact += 1) {
      box([0.012, 0.09, 0.012], [x - 0.06 + contact * 0.02, 2.18, -0.431], copper, 'Módulos de RAM');
    }
  });

  // Módulo M.2 NVMe com dissipador, parafusos e acabamento escovado.
  box([1.0, 0.17, 0.1], [-0.48, 2.03, -0.54], blackMetal, 'HD/SSD', true);
  box([0.64, 0.12, 0.045], [-0.52, 2.03, -0.465], aluminum, 'HD/SSD');
  box([0.46, 0.025, 0.012], [-0.52, 2.03, -0.435], teal, 'HD/SSD');
  [-0.92, -0.04].forEach(x => cylinder(0.025, 0.025, [x, 2.03, -0.455], screwMaterial, 'HD/SSD', true));

  // Chipset, bateria CMOS, conectores SATA e trilhos PCIe destacam as peças da placa.
  box([0.42, 0.16, 0.34], [0.9, 2.05, -0.54], blackMetal, 'Placa-mãe', true);
  box([0.26, 0.035, 0.2], [0.9, 2.05, -0.435], teal, 'Placa-mãe');
  cylinder(0.105, 0.055, [0.98, 2.38, -0.51], aluminum, 'Placa-mãe', true);
  [0, 1, 2, 3].forEach(index => {
    box([0.14, 0.09, 0.08], [0.98, 1.72 + index * 0.11, -0.56], index % 2 === 0 ? aluminum : graphite, 'Placa-mãe');
  });
  [0, 1, 2].forEach(index => {
    box([1.7, 0.035, 0.08], [-0.2, 0.96 + index * 0.14, -0.55], blackMetal, 'Placa-mãe');
    box([1.28, 0.012, 0.018], [-0.26, 0.96 + index * 0.14, -0.5], screwMaterial, 'Placa-mãe');
  });

  // SSD de 2,5 polegadas com tampa escovada e identificação, ao lado da fonte modular.
  box([0.9, 0.16, 0.58], [-1.03, 0.92, -0.23], blackMetal, 'HD/SSD', true);
  box([0.78, 0.035, 0.46], [-1.03, 1.025, -0.2], graphite, 'HD/SSD');
  box([0.48, 0.09, 0.014], [-1.03, 1.05, -0.2], labelTexture('HELP TI', 'SOLID STATE  /  SSD'), 'HD/SSD');
  [-1.32, -0.74].forEach(x => cylinder(0.025, 0.024, [x, 0.92, -0.23], screwMaterial, 'HD/SSD', true));

  // As três ventoinhas ARGB frontais fecham o fluxo de ar do gabinete panorâmico.
  [1.18, 2.38, 3.48].forEach(y => fan(1.2, y, 0.52, 0.22, 'Gabinete', aluminum, rgbFanFrame));

  // Placa de vídeo gamer: carcaça chanfrada, backplate e três ventoinhas ARGB.
  const gpuHousing = new THREE.Shape();
  gpuHousing.moveTo(-1.28, -0.27);
  gpuHousing.lineTo(-1.12, -0.38);
  gpuHousing.lineTo(0.9, -0.38);
  gpuHousing.lineTo(1.28, -0.25);
  gpuHousing.lineTo(1.28, 0.26);
  gpuHousing.lineTo(1.1, 0.38);
  gpuHousing.lineTo(-1.08, 0.38);
  gpuHousing.lineTo(-1.28, 0.22);
  gpuHousing.closePath();
  add(
    new THREE.ExtrudeGeometry(gpuHousing, {
      depth: 0.56,
      bevelEnabled: true,
      bevelSegments: 3,
      bevelSize: 0.025,
      bevelThickness: 0.025,
    }),
    blackMetal,
    [0, 1.43, -0.42],
    'Placa de vídeo',
  );
  box([2.36, 0.62, 0.035], [0, 1.43, -0.405], graphite, 'Placa de vídeo', true);
  for (let index = 0; index < 8; index += 1) {
    const x = -0.84 + index * 0.24;
    const backplateGroove = box([0.018, 0.38, 0.012], [x, 1.43, -0.415], blackMetal, 'Placa de vídeo');
    backplateGroove.rotation.z = index % 2 === 0 ? -0.42 : 0.42;
  }
  const gpuShroud = new THREE.Shape();
  gpuShroud.moveTo(-1.28, -0.27);
  gpuShroud.lineTo(-1.12, -0.38);
  gpuShroud.lineTo(0.9, -0.38);
  gpuShroud.lineTo(1.28, -0.25);
  gpuShroud.lineTo(1.28, 0.26);
  gpuShroud.lineTo(1.1, 0.38);
  gpuShroud.lineTo(-1.08, 0.38);
  gpuShroud.lineTo(-1.28, 0.22);
  gpuShroud.closePath();
  [-0.72, 0, 0.72].forEach(x => {
    const fanOpening = new THREE.Path();
    fanOpening.absellipse(x, 0, 0.251, 0.251, 0, Math.PI * 2, true, 0);
    gpuShroud.holes.push(fanOpening);
  });
  add(
    new THREE.ExtrudeGeometry(gpuShroud, {
      depth: 0.045,
      bevelEnabled: true,
      bevelSegments: 2,
      bevelSize: 0.008,
      bevelThickness: 0.008,
    }),
    graphite,
    [0, 1.43, 0.2],
    'Placa de vídeo',
    true,
  );
  [-0.72, 0, 0.72].forEach(x => fan(x, 1.43, 0.3, 0.24, 'Placa de vídeo', aluminum, rgbFanFrame));
  box([2.08, 0.035, 0.025], [0, 1.82, 0.46], teal, 'Placa de vídeo');
  box([0.45, 0.09, 0.014], [1.03, 1.74, 0.255], labelTexture('HELP TI', 'TRIPLE FAN  /  ARGB'), 'Placa de vídeo');
  [-1, 1].forEach(side => {
    box([2.24, 0.025, 0.025], [0, 1.43 + side * 0.34, 0.2], graphite, 'Placa de vídeo');
  });
  for (let index = 0; index < 14; index += 1) {
    const x = -0.9 + index * 0.14;
    box([0.022, 0.12, 0.34], [x, 1.015, -0.14], index % 2 === 0 ? aluminum : graphite, 'Placa de vídeo');
  }
  box([1.08, 0.035, 0.04], [0.02, 0.96, -0.05], copper, 'Placa de vídeo');
  box([0.12, 0.65, 0.08], [-1.29, 1.43, -0.11], aluminum, 'Placa de vídeo');
  for (let index = 0; index < 3; index += 1) {
    box([0.035, 0.13, 0.035], [-1.29, 1.19 + index * 0.22, -0.06], blackMetal, 'Placa de vídeo');
  }

  // Fonte modular no compartimento inferior e chicote roteado pela lateral.
  box([1.55, 0.5, 0.82], [0.34, 0.43, -0.13], blackMetal, 'Fonte de alimentação', true);
  box([1.38, 0.42, 0.045], [0.34, 0.43, 0.305], graphite, 'Fonte de alimentação');
  fan(0.02, 0.43, 0.34, 0.17, 'Fonte de alimentação', aluminum, rgbFanFrame);
  box([0.43, 0.13, 0.012], [0.79, 0.43, 0.34], labelTexture('HELPTI', 'MODULAR  /  80 PLUS'), 'Fonte de alimentação');
  const cableBlack = new THREE.MeshStandardMaterial({ color: 0x090d11, metalness: 0.28, roughness: 0.58 });
  const cableTeal = new THREE.MeshStandardMaterial({ color: 0x146e68, metalness: 0.46, roughness: 0.35 });
  addCable([[1.0, 0.48, 0.19], [1.21, 0.7, 0.16], [1.22, 1.05, 0.13], [1.1, 1.38, 0.12]], 0.035, cableBlack);
  addCable([[0.94, 0.45, 0.21], [1.13, 0.72, 0.19], [1.13, 1.04, 0.16], [0.88, 1.38, 0.13]], 0.012, cableTeal);

  return parts;
}

function edgeMetalMaterial(): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({ color: 0x586971, metalness: 0.82, roughness: 0.28 });
}
