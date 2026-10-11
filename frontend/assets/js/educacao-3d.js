(function () {
  const MODEL_UID = '1a24273417534f69afa0f7c62b643ffc';
  const iframe = document.getElementById('api-frame');
  const infoCard = document.getElementById('info-card');
  if (!iframe || typeof Sketchfab === 'undefined') return;

  // Preencha com os nomes exatos exibidos no console (lista "[HelpTI 3D]").
  // A comparação é por substring, sem diferenciar maiúsculas/minúsculas.
  const COMPONENTS = {
    gpu: {
      match: ['gpu', 'graphic', 'video', 'rtx', 'geforce', 'radeon'],
      title: 'Placa de Vídeo (GPU)',
      problem: 'Tela preta, artefatos visuais, travamentos em jogos ou superaquecimento.',
      solution: 'Reinstale/atualize os drivers, limpe o cooler e a poeira, confira o encaixe PCIe e os cabos de energia, e monitore a temperatura.'
    },
    ram: {
      match: ['ram', 'memory', 'memoria', 'dimm', 'ddr'],
      title: 'Memória RAM',
      problem: 'Telas azuis, reinicializações aleatórias, lentidão e erros de memória.',
      solution: 'Reencaixe os pentes, limpe os contatos, teste com o MemTest86, teste um pente por vez e verifique XMP/frequência na BIOS.'
    }
  };

  const RED = [1, 0.1, 0.1];
  const originals = new Map();
  let api = null;
  let materials = [];
  let selected = null;

  function findComponent(name) {
    const n = (name || '').toLowerCase();
    return Object.keys(COMPONENTS).find(key => COMPONENTS[key].match.some(m => n.includes(m))) || null;
  }

  function materialsOf(key) {
    return materials.filter(m => findComponent(m.name) === key);
  }

  function tint(key, on) {
    materialsOf(key).forEach(mat => {
      if (!originals.has(mat.id)) originals.set(mat.id, JSON.parse(JSON.stringify(mat.channels)));
      const ch = JSON.parse(JSON.stringify(mat.channels));
      if (on) {
        ch.EmitColor = ch.EmitColor || {};
        ch.EmitColor.enable = true;
        ch.EmitColor.color = RED;
        ch.EmitColor.factor = 0.35;
      } else {
        const orig = originals.get(mat.id);
        if (orig) Object.assign(ch, orig);
      }
      mat.channels = ch;
      api.setMaterial(mat, function () {});
    });
  }

  function showInfo(key) {
    const c = COMPONENTS[key];
    infoCard.innerHTML =
      '<h3></h3><p><strong>Problema técnico:</strong> <span class="p"></span></p>' +
      '<p><strong>Solução:</strong> <span class="s"></span></p>';
    infoCard.querySelector('h3').textContent = c.title;
    infoCard.querySelector('.p').textContent = c.problem;
    infoCard.querySelector('.s').textContent = c.solution;
  }

  function select(key) {
    if (selected === key) return;
    if (selected) tint(selected, false);
    selected = key;
    if (key) {
      tint(key, true);
      showInfo(key);
    }
  }

  new Sketchfab(iframe).init(MODEL_UID, {
    success: function (a) {
      api = a;
      api.start();
      api.addEventListener('viewerready', function () {
        api.getMaterialList(function (err, list) {
          if (err) return console.error('[HelpTI 3D] erro ao listar materiais', err);
          materials = list;
          console.group('[HelpTI 3D] Materiais');
          list.forEach(m => console.log(m.name, m.id));
          console.groupEnd();
        });
        api.getNodeMap(function (err, nodes) {
          if (err) return console.error('[HelpTI 3D] erro ao listar nós', err);
          console.group('[HelpTI 3D] Nós');
          Object.values(nodes).forEach(n => console.log(n.type, '-', n.name, '(instanceID ' + n.instanceID + ')'));
          console.groupEnd();
          window.__helptiNodes = nodes;
        });

        api.addEventListener('click', function (info) {
          if (!info || !info.material) return select(null);
          select(findComponent(info.material.name));
        }, { pick: 'fast' });
      });
    },
    error: function () {
      console.error('[HelpTI 3D] falha ao iniciar o Sketchfab Viewer');
    },
    ui_infos: 0,
    ui_watermark: 0,
    ui_watermark_link: 0,
    ui_hint: 0,
    ui_help: 0,
    ui_ar: 0,
    ui_stop: 0,
    ui_annotations: 0,
    autostart: 1,
    preload: 1
  });
})();
