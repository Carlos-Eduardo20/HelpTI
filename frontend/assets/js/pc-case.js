import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
export function createPcCase(scene) {
    const parts = [];
    const chassis = new THREE.MeshPhysicalMaterial({
        color: 0x202a31,
        metalness: 0.72,
        roughness: 0.24,
        clearcoat: 0.58,
        clearcoatRoughness: 0.18,
    });
    const edgeMetal = new THREE.MeshStandardMaterial({
        color: 0x71838b,
        metalness: 0.82,
        roughness: 0.22,
    });
    const rubber = new THREE.MeshStandardMaterial({ color: 0x080b0e, roughness: 0.88 });
    const glass = new THREE.MeshPhysicalMaterial({
        color: 0xc8e2e2,
        metalness: 0.08,
        roughness: 0.12,
        transparent: true,
        opacity: 0.075,
        depthWrite: false,
        clearcoat: 1,
        clearcoatRoughness: 0.08,
        side: THREE.DoubleSide,
    });
    const accent = new THREE.MeshStandardMaterial({
        color: 0x32d5bb,
        emissive: 0x0b8d79,
        emissiveIntensity: 0.85,
        metalness: 0.48,
        roughness: 0.34,
    });
    const black = new THREE.MeshStandardMaterial({ color: 0x080d12, metalness: 0.28, roughness: 0.46 });
    const add = (geometry, material, position, component = 'Gabinete', outline = false, selectable = true) => {
        const mesh = new THREE.Mesh(geometry, material);
        mesh.position.set(...position);
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        mesh.userData.component = component;
        mesh.userData.outline = outline;
        scene.add(mesh);
        if (selectable)
            parts.push(mesh);
        return mesh;
    };
    const box = (size, position, material = chassis, outline = false, component = 'Gabinete') => {
        const radius = Math.min(0.035, Math.min(...size) * 0.24);
        return add(new RoundedBoxGeometry(...size, 3, radius), material, position, component, outline);
    };
    const frontButton = (radius, length, position, material) => {
        const mesh = add(new THREE.CylinderGeometry(radius, radius, length, 28), material, position);
        mesh.rotation.x = Math.PI / 2;
        return mesh;
    };
    // Chassi aberto com estrutura de alumínio, parede traseira e vidro fumê frontal.
    box([3.02, 3.9, 0.12], [0, 2.02, -0.96], chassis, true);
    box([3.06, 0.14, 1.98], [0, 0.12, 0], chassis, true);
    box([3.06, 0.14, 1.98], [0, 3.92, 0], chassis, true);
    box([0.1, 3.76, 0.11], [-1.49, 2.02, 0.9], edgeMetal, true);
    box([0.1, 3.76, 0.11], [1.49, 2.02, 0.9], edgeMetal, true);
    box([0.1, 3.76, 0.11], [-1.49, 2.02, -0.9], edgeMetal, true);
    box([0.1, 3.76, 0.11], [1.49, 2.02, -0.9], edgeMetal, true);
    box([2.92, 0.08, 0.11], [0, 0.2, 0.9], edgeMetal, true);
    box([2.92, 0.08, 0.11], [0, 3.84, 0.9], edgeMetal, true);
    // Acabamento frontal em alumínio para destacar o formato panorâmico do gabinete.
    box([0.045, 3.42, 0.045], [-1.405, 2.02, 0.925], edgeMetal, true);
    box([0.045, 3.42, 0.045], [1.405, 2.02, 0.925], edgeMetal, true);
    box([2.72, 0.035, 0.045], [0, 3.765, 0.925], edgeMetal);
    const glassPanel = new THREE.Mesh(new RoundedBoxGeometry(2.86, 3.56, 0.035, 4, 0.035), glass);
    glassPanel.position.set(0, 2.02, 0.88);
    glassPanel.userData.component = 'Gabinete';
    glassPanel.userData.casePanel = true;
    glassPanel.renderOrder = 2;
    glassPanel.castShadow = false;
    glassPanel.receiveShadow = false;
    scene.add(glassPanel);
    // Trilhos internos e cobertura da fonte deixam o conjunto com uma montagem real.
    box([2.86, 0.08, 1.52], [0, 0.78, -0.02], chassis, true);
    [-1.18, 1.18].forEach(x => {
        box([0.045, 2.95, 0.06], [x, 2.18, -0.36], edgeMetal);
        [1.02, 1.74, 2.46, 3.18].forEach(y => {
            box([0.1, 0.035, 0.12], [x, y, 0.46], edgeMetal);
        });
    });
    // Fendas de ventilação na parte superior do gabinete.
    for (let index = 0; index < 9; index += 1) {
        const x = -0.68 + index * 0.17;
        box([0.025, 0.018, 0.8], [x, 4.0, -0.05], black);
    }
    // Painel frontal discreto: botão de energia, USB e acabamento anodizado.
    box([0.28, 0.58, 0.08], [1.27, 3.44, 0.91], black, true);
    frontButton(0.075, 0.035, [1.27, 3.62, 0.96], accent);
    frontButton(0.035, 0.03, [1.2, 3.28, 0.96], edgeMetal);
    frontButton(0.035, 0.03, [1.34, 3.28, 0.96], edgeMetal);
    box([0.035, 0.15, 0.02], [1.27, 2.98, 0.96], accent);
    // Pés de borracha isolam o gabinete da bancada.
    [-1.08, 1.08].forEach(x => {
        [-0.63, 0.63].forEach(z => {
            add(new THREE.CylinderGeometry(0.13, 0.15, 0.12, 24), rubber, [x, 0.005, z]);
            add(new THREE.CylinderGeometry(0.095, 0.095, 0.025, 24), edgeMetal, [x, 0.071, z]);
        });
    });
    return parts;
}
