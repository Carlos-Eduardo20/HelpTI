from html import escape
import math
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
    from io import StringIO

    from matplotlib.backends.backend_svg import FigureCanvasSVG
    from matplotlib.figure import Figure
    from mpl_toolkits.mplot3d import Axes3D
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    selected = selected_part if selected_part in DIAGNOSTICOS else None
    azimuth = _normalizar_orientacao(azimuth, _DEFAULT_AZIMUTH)
    elevation = _normalizar_orientacao(elevation, _DEFAULT_ELEVATION, 8, 65)

    figure = Figure(figsize=(7.6, 5.6), dpi=100, facecolor="#0d131c")
    canvas = FigureCanvasSVG(figure)
    axes = figure.add_subplot(111, projection=Axes3D.name)
    axes.set_facecolor("#0d131c")
    axes.view_init(elev=elevation, azim=azimuth)
    axes.set_xlim(-2.0, 2.0)
    axes.set_ylim(-1.8, 1.8)
    axes.set_zlim(0, 4.7)
    axes.set_box_aspect((4.0, 3.6, 4.7))
    axes.set_axis_off()

    palette = {
        "Gabinete": "#202A31",
        "Placa-mãe": "#17604F",
        "Processador": "#C1CDD0",
        "Módulos de RAM": "#32D5BB",
        "Placa de vídeo": "#465760",
        "Fonte de alimentação": "#303C43",
        "HD/SSD": "#91A5AD",
    }
    component_ids = {}

    def add_box(component, origin, size, color=None, alpha=1.0, edge="#111923"):
        x, y, z = origin
        dx, dy, dz = size
        corners = [
            (x, y, z), (x + dx, y, z), (x + dx, y + dy, z), (x, y + dy, z),
            (x, y, z + dz), (x + dx, y, z + dz), (x + dx, y + dy, z + dz), (x, y + dy, z + dz),
        ]
        faces = [
            [corners[index] for index in face]
            for face in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))
        ]
        face_color = color or palette.get(component, "#29313B")
        if selected == component:
            face_color = "#36CBB1"
        mesh = Poly3DCollection(faces, facecolors=face_color, edgecolors=edge, linewidths=0.65, alpha=alpha)
        encoded = quote(component, safe="")
        component_ids[component] = component_ids.get(component, 0) + 1
        mesh.set_gid(f"component-{encoded}-{component_ids[component]}")
        mesh.set_url(
            f"/educacao/pc-explorer?componente={encoded}"
            f"&azimute={azimuth:.1f}&elevacao={elevation:.1f}"
        )
        axes.add_collection3d(mesh)
        return mesh

    # Chassi em perspectiva, com painel de vidro translúcido.
    add_box("Gabinete", (-1.52, -0.98, 0.12), (3.04, 0.12, 3.78), "#71838B")
    add_box("Gabinete", (-1.52, -0.98, 0.12), (3.04, 1.94, 0.12), "#3A4550")
    add_box("Gabinete", (-1.52, -0.98, 3.78), (3.04, 1.94, 0.12), "#3A4550")
    add_box("Gabinete", (-1.52, -0.98, 0.12), (0.12, 1.94, 3.78), "#64727D")
    add_box("Gabinete", (1.40, -0.98, 0.12), (0.12, 1.94, 3.78), "#64727D")
    add_box("Gabinete", (-1.38, 0.91, 0.18), (2.76, 0.035, 3.64), "#9CC6C8", alpha=0.16, edge="#A9E7DF")
    add_box("Gabinete", (-1.43, 0.96, 0.2), (0.045, 0.035, 3.4), "#71838B")
    add_box("Gabinete", (1.385, 0.96, 0.2), (0.045, 0.035, 3.4), "#71838B")

    # Placa, cooler, memória, armazenamento, placa de vídeo e fonte.
    add_box("Placa-mãe", (-1.12, -0.73, 0.88), (2.24, 0.12, 2.78))
    add_box("Processador", (0.12, -0.48, 2.42), (0.76, 0.28, 0.72), "#737E8D")
    add_box("Processador", (0.18, -0.12, 2.46), (0.66, 0.56, 0.62), "#202B32")
    add_box("Processador", (0.23, 0.43, 2.51), (0.56, 0.08, 0.52), "#465760")
    for radius, color, width in ((0.28, "#4DE0C3", 2.5), (0.21, "#A7F5E8", 1.3), (0.12, "#D5A05A", 1.8)):
        ring = [2 * index * math.pi / 64 for index in range(65)]
        axes.plot(
            [0.51 + radius * math.cos(angle) for angle in ring],
            [0.53] * len(ring),
            [2.77 + radius * math.sin(angle) for angle in ring],
            color=color, linewidth=width,
        )
    # Radiador AIO de 360 mm alinhado às três ventoinhas ARGB frontais.
    add_box("Processador", (1.02, 0.42, 0.9), (0.24, 0.28, 2.88), "#202B32")
    for fin in range(12):
        add_box("Processador", (1.015 + fin * 0.018, 0.72, 0.98), (0.009, 0.025, 2.72), "#91A5AD", edge="#53636C")
    for points, color, width in (
        (((0.76, 0.7, 3.0), (1.0, 0.76, 3.2), (1.29, 0.76, 3.58), (1.15, 0.76, 3.72)), "#111A20", 3.2),
        (((0.76, 0.7, 2.6), (1.0, 0.76, 2.5), (1.3, 0.76, 1.95), (1.15, 0.76, 1.05)), "#111A20", 3.2),
    ):
        axes.plot([p[0] for p in points], [p[1] for p in points], [p[2] for p in points], color=color, linewidth=width)
    for x in (-0.8, -0.52):
        add_box("Módulos de RAM", (x, -0.33, 2.04), (0.18, 0.2, 1.12))
        add_box("Módulos de RAM", (x + 0.02, -0.1, 3.0), (0.14, 0.04, 0.11), "#55D9BC")
    add_box("HD/SSD", (-0.58, -0.43, 1.88), (0.88, 0.2, 0.15), "#92A4B0")
    add_box("HD/SSD", (-1.13, -0.05, 0.55), (0.84, 0.66, 0.16), "#202B32")
    add_box("HD/SSD", (-1.09, 0.57, 0.59), (0.76, 0.045, 0.08), "#91A5AD")
    add_box("Placa de vídeo", (-1.25, -0.02, 1.20), (2.5, 0.66, 0.54))
    add_box("Placa de vídeo", (-1.1, 0.64, 1.23), (2.2, 0.07, 0.48), "#303944", edge="#71808C")
    add_box("Fonte de alimentação", (0.18, -0.55, 0.27), (1.12, 1.12, 0.56))
    add_box("Fonte de alimentação", (0.26, 0.58, 0.31), (0.96, 0.04, 0.48), "#414B56")

    # Ventoinhas na placa de vídeo e na entrada frontal do gabinete.
    def add_fan(component, x, y, z, radius, color="#51D4BC"):
        theta = [2 * index * math.pi / 48 for index in range(49)]
        axes.plot(
            [x + radius * math.cos(angle) for angle in theta],
            [y] * len(theta),
            [z + radius * math.sin(angle) for angle in theta],
            color=color, linewidth=2.2,
        )
        for blade in range(7):
            angle = blade * 2 * math.pi / 7
            curve_angles = [angle + step * 0.012 for step in range(25)]
            curve_radii = [radius * (0.2 + step * 0.022) for step in range(25)]
            axes.plot(
                [x + r * math.cos(a) for r, a in zip(curve_radii, curve_angles)],
                [y] * len(curve_angles),
                [z + r * math.sin(a) for r, a in zip(curve_radii, curve_angles)],
                color="#B9C9CB" if selected != component else color, linewidth=1.45,
            )
        hub = radius * 0.2
        axes.plot(
            [x + hub * math.cos(angle) for angle in theta], [y] * len(theta),
            [z + hub * math.sin(angle) for angle in theta], color="#D5A05A", linewidth=1.8,
        )

    for fan_x in (-0.72, 0, 0.72):
        add_fan("Placa de vídeo", fan_x, 0.72, 1.47, 0.22, "#70E6D3" if selected == "Placa de vídeo" else "#72828D")
    for fan_z in (1.35, 2.35, 3.35):
        add_fan("Gabinete", 1.16, 0.82, fan_z, 0.22, "#50D8BE")
    add_fan("Fonte de alimentação", 0.74, 0.63, 0.55, 0.15, "#50D8BE")

    # Botões de seleção também ficam codificados nos elementos SVG gerados.
    for key, (x, z) in zip(DIAGNOSTICOS, ((-1.15, 3.42), (-1.12, 3.05), (0.1, 3.55), (-0.75, 2.84), (-0.9, 1.17), (0.28, 0.42), (-0.6, 1.88))):
        text = axes.text(x, 1.12, z, key, color="#F3F8F7", fontsize=6.2, ha="center", va="center")
        encoded = quote(key, safe="")
        text.set_gid(f"component-label-{encoded}")
        text.set_url(
            f"/educacao/pc-explorer?componente={encoded}"
            f"&azimute={azimuth:.1f}&elevacao={elevation:.1f}"
        )

    figure.subplots_adjust(left=0, right=1, bottom=0, top=1)
    buffer = StringIO()
    canvas.print_svg(buffer, metadata={"Date": None})
    result = buffer.getvalue()
    svg_start = result.find("<svg ")
    svg_end = result.rfind("</svg>")
    if svg_start < 0 or svg_end < svg_start:
        raise RuntimeError("O Matplotlib não gerou um SVG válido para o modelo do PC.")
    return result[svg_start:svg_end + len("</svg>")]


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
