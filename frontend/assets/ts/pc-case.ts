import * as THREE from 'three';
import type { ComponentName, PcPart } from './pc-types.js';

export function createPcCase(scene: THREE.Scene): PcPart[] {
  const parts: PcPart[] = [];
  const darkMetal = new THREE.MeshStandardMaterial({ color: 0x111821, metalness: 0.62, roughness: 0.32 });
  const glass = new THREE.MeshStandardMaterial({ color: 0x27465a, metalness: 0.18, roughness: 0.2, transparent: true, opacity: 0.12, depthWrite: false });

  const add = (geometry: THREE.BufferGeometry, material: THREE.MeshStandardMaterial, position: [number, number, number], component: ComponentName = 'Gabinete') => {
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(...position);
    mesh.userData.component = component;
    scene.add(mesh);
    parts.push(mesh);
    return mesh;
  };
  const box = (size: [number, number, number], position: [number, number, number], material = darkMetal) =>
    add(new THREE.BoxGeometry(...size), material, position);

  // Chassi cúbico com interior aberto e painéis de vidro azulados.
  box([2.9, 3.65, 0.12], [0, 2, -0.82]); // fundo
  box([0.12, 3.85, 1.72], [-1.4, 2, 0]);
  box([0.12, 3.85, 1.72], [1.4, 2, 0]);
  box([2.9, 0.14, 1.72], [0, 0.12, 0]);
  box([2.9, 0.14, 1.72], [0, 3.88, 0]);
  add(new THREE.BoxGeometry(2.68, 3.65, 0.035), glass, [0, 2, 0.87]);
  add(new THREE.BoxGeometry(0.035, 3.65, 1.62), glass, [1.4, 2, 0]);

  // Colunas internas e trilhos visíveis na lateral do gabinete.
  [-0.95, 0.95].forEach(x => {
    for (let y = 0.55; y < 3.6; y += 0.58) {
      box([0.035, 0.025, 0.12], [x, y, 0.72], new THREE.MeshStandardMaterial({ color: 0x38516c, metalness: 0.3, roughness: 0.48 }));
    }
  });
  // Fita de luz violeta na base, como no print de referência.
  const led = new THREE.MeshStandardMaterial({ color: 0x9c68ff, emissive: 0x7035ff, emissiveIntensity: 1.5, metalness: 0.15, roughness: 0.3 });
  box([2.35, 0.035, 0.035], [0, 0.78, 0.76], led);
  return parts;
}
