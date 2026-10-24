from html import escape
from urllib.parse import quote


SKETCHFAB_MODEL_UID = "1a24273417534f69afa0f7c62b643ffc"
_DEFAULT_AZIMUTH = 18.0
_DEFAULT_ELEVATION = 18.0

DIAGNOSTICOS = {
    "Gabinete": {
        "erros": (
            "O botão Power não responde.",
            "Ventoinhas fazem ruído ou não giram.",
            "Poeira bloqueia entradas e saídas de ar.",
            "Portas USB frontais não reconhecem dispositivos.",
        ),
        "solucao": (
            "Confira os conectores do painel frontal na placa-mãe.",
            "Limpe filtros e ventoinhas com o computador desligado e desconectado da tomada.",
            "Verifique se os cabos USB frontais estão conectados corretamente.",
            "Organize os cabos para não bloquear o fluxo de ar.",
        ),
    },
    "Placa-mãe": {
        "erros": (
            "O computador liga, mas não conclui o POST.",
            "Bipes ou LEDs de diagnóstico indicam falha de componente.",
            "Portas ou slots deixam de reconhecer dispositivos.",
            "A BIOS perde configurações ou não inicia após uma atualização.",
        ),
        "solucao": (
            "Consulte o código de bipes ou o LED de diagnóstico no manual da placa.",
            "Confira os conectores ATX de 24 pinos e EPS do processador.",
            "Reencaixe os componentes e teste um dispositivo por vez.",
            "Se necessário, restaure a BIOS pelo procedimento Clear CMOS do fabricante.",
        ),
    },
    "Processador": {
        "erros": (
            "Temperatura elevada mesmo com pouca carga.",
            "Desligamentos ou redução de desempenho durante tarefas pesadas.",
            "Falha no POST após a troca do processador.",
            "Uso do processador permanece alto sem aplicativos em execução.",
        ),
        "solucao": (
            "Confira a fixação do cooler e se a ventoinha está ligada ao CPU_FAN.",
            "Verifique a circulação de ar e remova poeira do dissipador.",
            "Confirme compatibilidade e versão da BIOS antes de trocar o processador.",
            "Monitore temperaturas e processos; troque a pasta térmica se necessário.",
        ),
    },
    "Módulos de RAM": {
        "erros": (
            "Telas azuis, travamentos ou reinicializações aleatórias.",
            "Bipes de memória ou ausência de imagem durante a inicialização.",
            "Menos memória disponível do que a instalada.",
            "Erros aparecem somente com XMP/EXPO ativado.",
        ),
        "solucao": (
            "Desligue e desconecte o computador antes de reencaixar os módulos.",
            "Teste um módulo por vez e use os slots indicados no manual da placa-mãe.",
            "Execute um teste de memória e confirme capacidade e frequência na BIOS.",
            "Se houver instabilidade, desative XMP/EXPO e teste a configuração padrão.",
        ),
    },
    "Placa de vídeo": {
        "erros": (
            "Sem imagem ou sinal de vídeo intermitente.",
            "Pontos, linhas ou cores incorretas aparecem na tela.",
            "Jogos e aplicativos 3D travam ou fecham inesperadamente.",
            "Temperatura alta, ruído excessivo ou queda de desempenho sob carga.",
        ),
        "solucao": (
            "Confira o cabo do monitor, a entrada selecionada e os conectores PCIe de energia.",
            "Reencaixe a placa com o computador desligado e verifique se está firme no slot.",
            "Reinstale o driver oficial e teste outro cabo ou monitor para isolar a causa.",
            "Limpe as entradas de ar e monitore a temperatura durante o uso.",
        ),
    },
    "Fonte de alimentação": {
        "erros": (
            "O computador não liga ou desliga logo após pressionar Power.",
            "Reinicializações acontecem quando CPU ou GPU entram em carga.",
            "Ventoinha, cheiro ou ruído da fonte parecem anormais.",
            "Conectores ou cabos apresentam aquecimento ou dano visível.",
        ),
        "solucao": (
            "Confira o cabo de energia, o interruptor traseiro e as conexões ATX/EPS/PCIe.",
            "Verifique se a fonte atende à potência recomendada para os componentes.",
            "Interrompa o uso se houver cheiro de queimado, cabos danificados ou estalos.",
            "Não abra a fonte: capacitores internos podem manter carga perigosa.",
        ),
    },
    "HD/SSD": {
        "erros": (
            "Inicialização e carregamento de arquivos ficam muito lentos.",
            "Arquivos apresentam erros de leitura ou gravação.",
            "A unidade desaparece da BIOS ou do sistema operacional.",
            "A ferramenta S.M.A.R.T. indica alerta de saúde.",
        ),
        "solucao": (
            "Faça backup dos arquivos importantes antes de investigar a unidade.",
            "Confira cabos SATA e alimentação, ou reencaixe o SSD M.2 com o equipamento desligado.",
            "Consulte a saúde S.M.A.R.T. com a ferramenta do fabricante.",
            "Atualize firmware e substitua a unidade se o diagnóstico indicar falha física.",
        ),
    },
}


def _normalizar_orientacao(value, default, minimum=None, maximum=None):
    try:
        angle = float(value)
    except (TypeError, ValueError):
        return default
    if minimum is None:
        return angle % 360
    return min(maximum, max(minimum, angle))


def _build_parts(azimuth, elevation):
    return [(name, {"color": "#29313B"}) for name in DIAGNOSTICOS]


def render_pc_svg(selected_part=None, azimuth=_DEFAULT_AZIMUTH, elevation=_DEFAULT_ELEVATION):
    selected = selected_part if selected_part in DIAGNOSTICOS else None
    azimuth = _normalizar_orientacao(azimuth, _DEFAULT_AZIMUTH)
    elevation = _normalizar_orientacao(elevation, _DEFAULT_ELEVATION, 8, 65)
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" class="model" viewBox="0 0 760 560" role="img" aria-label="Modelo 3D interativo de um computador">',
        '<defs><linearGradient id="scene" x2="0" y2="1"><stop stop-color="#17212d"/><stop offset="1" stop-color="#0d131c"/></linearGradient></defs>',
        '<rect width="760" height="560" rx="18" fill="url(#scene)"/>',
        '<path d="M205 145 493 110 570 155 570 420 282 455 205 410Z" fill="#687586" stroke="#c1cbd3" stroke-width="8"/>',
        '<path d="M222 162 482 132 482 390 222 420Z" fill="#173d38" stroke="#111923" stroke-width="5"/>',
        '<path d="M493 126 555 160 555 405 493 390Z" fill="#29313b" fill-opacity=".8" stroke="#c1cbd3" stroke-width="5"/>',
        '<rect x="300" y="195" width="75" height="70" rx="5" fill="#7f8d9a"/>',
        '<rect x="390" y="165" width="18" height="150" rx="3" fill="#2c6255"/>',
        '<rect x="420" y="165" width="18" height="150" rx="3" fill="#2c6255"/>',
        '<rect x="285" y="320" width="220" height="48" rx="8" fill="#111923" stroke="#7f8d9a" stroke-width="5"/>',
    ]
    positions = ((285, 105), (275, 145), (300, 190), (440, 180), (405, 340), (260, 390), (480, 420))
    for (key, (x, y)) in zip(DIAGNOSTICOS, positions):
        fill = "#5eead4" if key == selected else "#101923"
        svg.append(
            f'<a class="component component-{quote(key, safe="")}" '
            f'href="/educacao/pc-explorer?componente={quote(key, safe="")}'
            f'&amp;azimute={azimuth:.1f}&amp;elevacao={elevation:.1f}" '
            f'aria-label="Selecionar {escape(key, quote=True)}">'
            f'<rect x="{x}" y="{y}" width="145" height="25" rx="12" fill="{fill}" stroke="#536472"/>'
            f'<text x="{x + 72}" y="{y + 17}" text-anchor="middle" font-family="Arial,sans-serif" '
            f'font-size="11" font-weight="700" fill="#ffffff">{escape(key)}</text></a>'
        )
    svg.append("</svg>")
    return "".join(svg)


_SKETCHFAB_SCRIPT = f"""
(() => {{
  const status = document.getElementById("modelStatus");
  const iframe = document.getElementById("modelViewer");
  if (typeof Sketchfab === "undefined") {{
    status.textContent = "Não foi possível carregar o visualizador 3D.";
    return;
  }}
  const componentNames = {{
    "Gabinete": ["case", "gabinete"],
    "Placa-mãe": ["motherboard", "mainboard", "placa-mae", "placa mãe"],
    "Processador": ["cpu", "processor", "processador"],
    "Módulos de RAM": ["ram", "memory", "memoria", "dimm", "ddr"],
    "Placa de vídeo": ["gpu", "graphic", "video", "rtx", "geforce", "radeon"],
    "Fonte de alimentação": ["power supply", "psu", "fonte"],
    "HD/SSD": ["ssd", "hard drive", "storage", "nvme"]
  }};
  new Sketchfab(iframe).init("{SKETCHFAB_MODEL_UID}", {{
    success: (api) => {{
      api.start();
      api.addEventListener("viewerready", () => api.addEventListener("click", (info) => {{
        const name = (info && info.material && info.material.name || "").toLowerCase();
        const match = Object.entries(componentNames).find(([, aliases]) => aliases.some((alias) => name.includes(alias)));
        if (match) location.href = `/educacao/pc-explorer?componente=${{encodeURIComponent(match[0])}}`;
      }}, {{ pick: "fast" }}));
    }},
    error: () => {{ status.textContent = "Não foi possível carregar o modelo 3D."; }},
    ui_infos: 0, ui_watermark: 0, ui_watermark_link: 0, ui_hint: 0,
    ui_help: 0, ui_ar: 0, ui_stop: 0, ui_annotations: 0, autostart: 1, preload: 1
  }});
}})();
"""


def render_pc_explorer(selected_part=None, azimuth=_DEFAULT_AZIMUTH, elevation=_DEFAULT_ELEVATION):
    selected = selected_part if selected_part in DIAGNOSTICOS else None
    azimuth = _normalizar_orientacao(azimuth, _DEFAULT_AZIMUTH)
    elevation = _normalizar_orientacao(elevation, _DEFAULT_ELEVATION, 8, 65)
    button_parts = []
    for key in DIAGNOSTICOS:
        selected_class = " selected" if key == selected else ""
        aria_current = ' aria-current="true"' if key == selected else ""
        button_parts.append(
            f'<a class="part-button{selected_class}" '
            f'href="/educacao/pc-explorer?componente={quote(key, safe="")}'
            f'&amp;azimute={azimuth:.1f}&amp;elevacao={elevation:.1f}"'
            f'{aria_current}>{escape(key)}</a>'
        )
    buttons = "".join(button_parts)
    if selected:
        diagnosis = DIAGNOSTICOS[selected]
        failures = "".join(f"<li>{escape(item)}</li>" for item in diagnosis["erros"])
        solutions = "".join(f"<li>{escape(item)}</li>" for item in diagnosis["solucao"])
        diagnosis_content = (
            f'<span class="component-kicker">COMPONENTE SELECIONADO</span>'
            f'<h3>{escape(selected)}</h3><h4>Falhas comuns</h4><ul>{failures}</ul>'
            f'<h4 class="solution-title">Possíveis soluções</h4><ul>{solutions}</ul>'
        )
    else:
        diagnosis_content = (
            '<div class="empty-state"><span class="empty-icon">+</span>'
            '<p>Selecione uma peça no modelo para consultar sintomas e recomendações.</p></div>'
        )
    return f"""<!doctype html>
<html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Explorador 3D de componentes | HelpTI</title>
<style>
* {{ box-sizing: border-box; }} body {{ margin: 0; padding: 18px; color: #18212b; background: #f3f5f7; font: 14px Arial,sans-serif; }}
.explorer {{ display: grid; grid-template-columns: minmax(0,1.55fr) minmax(245px,.8fr); gap: 16px; max-width: 1200px; margin: 0 auto; }}
.card {{ min-width: 0; padding: 18px; border: 1px solid #dfe5e9; border-radius: 8px; background: #fff; }}
.card-heading {{ display: flex; justify-content: space-between; gap: 12px; margin-bottom: 12px; }} h2 {{ margin: 0; font-size: 16px; }}
.live-badge {{ color: #087e6b; background: #e5f7f3; padding: 5px 8px; font-size: 10px; font-weight: 800; }}
.model-viewport {{ overflow: hidden; aspect-ratio: 760 / 520; border-radius: 6px; background: #111923; }} .model-viewport iframe {{ width: 100%; height: 100%; border: 0; }}
.hint,.empty-state p {{ color: #71808a; line-height: 1.6; }} .model-status {{ min-height: 16px; color: #b42318; }}
.parts {{ display: flex; flex-wrap: wrap; gap: 7px; }} .part-button {{ padding: 7px 9px; border: 1px solid #dce3e8; border-radius: 6px; color: #394652; text-decoration: none; }}
.part-button.selected,.part-button:hover {{ border-color: #41b9a3; color: #087e6b; background: #e8f8f5; }} .diagnosis h4 {{ margin: 18px 0 7px; color: #627382; font-size: 11px; text-transform: uppercase; }}
.diagnosis h4.solution-title {{ color: #0b907b; }} .diagnosis ul {{ display: grid; gap: 9px; padding-left: 19px; color: #4d5b66; line-height: 1.55; }}
.diagnosis .solution-title + ul li::marker {{ color: #0b907b; }} .empty-state {{ display: grid; min-height: 220px; align-content: center; justify-items: center; text-align: center; }}
@media(max-width:700px) {{ body {{ padding: 10px; }} .explorer {{ grid-template-columns: 1fr; }} .card {{ padding: 13px; }} }}
</style></head><body><main class="explorer"><section class="card">
<div class="card-heading"><h2>Custom Gaming PC</h2><span class="live-badge">MODELO INTERATIVO</span></div>
<div id="modelViewport" class="model-viewport"><iframe id="modelViewer" title="Custom Gaming PC" allow="autoplay; fullscreen; xr-spatial-tracking" allowfullscreen></iframe></div>
<p class="hint">Arraste o modelo para observar outros ângulos. Selecione um componente abaixo para consultar falhas e soluções.</p>
<p id="modelStatus" class="model-status" role="status" aria-live="polite"></p><nav class="parts" aria-label="Selecionar componente">{buttons}</nav></section>
<section class="card diagnosis" aria-live="polite"><div class="card-heading"><h2>Guia de diagnóstico</h2></div>{diagnosis_content}</section></main>
<script src="https://static.sketchfab.com/api/sketchfab-viewer-1.12.1.js"></script><script>{_SKETCHFAB_SCRIPT}</script></body></html>"""
