(function () {
  const MODEL_UID = '1a24273417534f69afa0f7c62b643ffc';
  const iframe = document.getElementById('api-frame');
  const componentList = document.getElementById('component-list');
  const diagnosisContent = document.getElementById('diagnosis-content');
  if (!iframe || !componentList || !diagnosisContent || typeof Sketchfab === 'undefined') return;

  const COMPONENTS = {
    'Gabinete': ['case', 'gabinete'],
    'Placa-mãe': ['motherboard', 'mainboard', 'placa-mae', 'placa mãe'],
    'Processador': ['cpu', 'processor', 'processador'],
    'Módulos de RAM': ['ram', 'memory', 'memoria', 'dimm', 'ddr'],
    'Placa de vídeo': ['gpu', 'graphic', 'video', 'rtx', 'geforce', 'radeon'],
    'Fonte de alimentação': ['power supply', 'psu', 'fonte'],
    'HD/SSD': ['ssd', 'hard drive', 'storage', 'nvme']
  };
  const RED = [1, 0.1, 0.1];
  const originals = new Map();
  let api = null;
  let materials = [];
  let diagnostics = {};
  let selected = null;

  function findComponent(name) {
    const n = (name || '').toLowerCase();
    return Object.entries(COMPONENTS).find(([, aliases]) => aliases.some(alias => n.includes(alias)))?.[0] || null;
  }

  function materialsOf(key) {
    return materials.filter(material => findComponent(material.name) === key);
  }

  function tint(key, on) {
    materialsOf(key).forEach(material => {
      if (!originals.has(material.id)) originals.set(material.id, JSON.parse(JSON.stringify(material.channels)));
      const channels = JSON.parse(JSON.stringify(material.channels));
      if (on) {
        channels.EmitColor = channels.EmitColor || {};
        channels.EmitColor.enable = true;
        channels.EmitColor.color = RED;
        channels.EmitColor.factor = 0.35;
      } else {
        const original = originals.get(material.id);
        if (original) Object.assign(channels, original);
      }
      material.channels = channels;
      api.setMaterial(material, function () {});
    });
  }

  function showInfo(key) {
    const diagnosis = diagnostics[key];
    diagnosisContent.replaceChildren();
    [['Falhas comuns', diagnosis.erros], ['Possíveis soluções', diagnosis.solucao]].forEach(([heading, items]) => {
      const section = document.createElement('section');
      const title = document.createElement('h4');
      const list = document.createElement('ul');
      title.textContent = heading;
      if (heading === 'Possíveis soluções') title.classList.add('solution-title');
      items.forEach(item => {
        const entry = document.createElement('li');
        entry.textContent = item;
        list.append(entry);
      });
      section.append(title, list);
      diagnosisContent.append(section);
    });
    componentList.querySelectorAll('button').forEach(button => {
      button.setAttribute('aria-pressed', String(button.dataset.component === key));
    });
  }

  function select(key) {
    if (selected === key) return;
    if (selected) tint(selected, false);
    selected = key;
    if (key) {
      tint(key, true);
      showInfo(key);
    } else {
      diagnosisContent.replaceChildren();
    }
  }

  fetch('/api/educacao/diagnosticos')
    .then(response => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    })
    .then(data => {
      diagnostics = data;
      Object.keys(COMPONENTS).forEach(key => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'component-button';
        button.dataset.component = key;
        button.textContent = key;
        button.setAttribute('aria-pressed', 'false');
        button.addEventListener('click', () => select(key));
        componentList.append(button);
      });
    })
    .catch(error => {
      diagnosisContent.textContent = 'Não foi possível carregar os diagnósticos.';
      console.error('[HelpTI 3D] falha ao carregar diagnósticos', error);
    });

  new Sketchfab(iframe).init(MODEL_UID, {
    success: function (viewerApi) {
      api = viewerApi;
      api.start();
      api.addEventListener('viewerready', function () {
        api.getMaterialList(function (err, list) {
          if (err) return console.error('[HelpTI 3D] erro ao listar materiais', err);
          materials = list;
        });

        api.addEventListener('click', function (info) {
          if (!info || !info.material) return;
          const component = findComponent(info.material.name);
          if (component) select(component);
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
    max_texture_size: 1024,
    autostart: 1,
    preload: 1
  });
})();
