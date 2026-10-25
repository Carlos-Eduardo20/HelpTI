import * as THREE from 'three';
export function createPcComponents(scene) {
    const parts = [];
    const board = new THREE.MeshStandardMaterial({ color: 0x103b31, metalness: 0.2, roughness: 0.66 });
    const black = new THREE.MeshStandardMaterial({ color: 0x111720, metalness: 0.58, roughness: 0.34 });
    const silver = new THREE.MeshStandardMaterial({ color: 0x8297a7, metalness: 0.78, roughness: 0.28 });
    const copper = new THREE.MeshStandardMaterial({ color: 0xb97932, metalness: 0.72, roughness: 0.3 });
    const add = (component, geometry, material, position) => {
        const mesh = new THREE.Mesh(geometry, material);
        mesh.position.set(...position);
        mesh.userData.component = component;
        scene.add(mesh);
        parts.push(mesh);
        return mesh;
    };
    const box = (component, size, position, material) => add(component, new THREE.BoxGeometry(...size), material, position);
    // Placa-mãe plana ao fundo do gabinete.
    box('Placa-mãe', [2.15, 2.75, 0.1], [0, 2.22, 0.55], board);
    // Soquete e bloco do processador.
    box('Processador', [0.66, 0.56, 0.15], [0.44, 2.76, 0.66], black);
    box('Processador', [0.5, 0.42, 0.12], [0.44, 2.79, 0.78], silver);
    // Dissipador de torre com aletas horizontais, destaque visual do print.
    box('Processador', [0.68, 1.35, 0.52], [0.78, 3.05, 0.68], black);
    for (let i = 0; i < 11; i += 1) {
        const y = 2.43 + i * 0.12;
        box('Processador', [1.08, 0.055, 0.66], [0.8, y, 0.78], silver);
    }
    [0.48, 0.7, 0.92, 1.14].forEach(x => box('Processador', [0.045, 0.1, 0.1], [x, 2.3, 0.78], copper));
    // Memórias verticais ao lado do cooler.
    [-0.24, -0.02].forEach(x => box('Módulos de RAM', [0.12, 1.0, 0.16], [x, 2.58, 0.7], new THREE.MeshStandardMaterial({ color: 0x263d49, metalness: 0.5, roughness: 0.35 })));
    // Placa de vídeo longa e escura atravessando o centro do gabinete.
    box('Placa de vídeo', [2.18, 0.48, 0.62], [0, 1.72, 0.74], black);
    box('Placa de vídeo', [2.02, 0.12, 0.64], [0, 1.98, 0.76], new THREE.MeshStandardMaterial({ color: 0x073c4b, metalness: 0.45, roughness: 0.38 }));
    // Compartimento inferior da fonte e unidade de armazenamento.
    box('Gabinete', [2.5, 0.62, 1.38], [0, 0.48, -0.02], black);
    box('Fonte de alimentação', [1.58, 0.46, 0.88], [0.28, 0.49, -0.08], silver);
    box('HD/SSD', [0.8, 0.16, 0.55], [-0.72, 0.94, 0.6], black);
    return parts;
}
