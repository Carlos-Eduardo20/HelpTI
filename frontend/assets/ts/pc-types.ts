import type * as THREE from 'three';

export type ComponentName = 'Gabinete' | 'Placa-mãe' | 'Processador' | 'Módulos de RAM' | 'Placa de vídeo' | 'Fonte de alimentação' | 'HD/SSD';

export type PcPart = THREE.Mesh<THREE.BufferGeometry, THREE.MeshStandardMaterial>;
