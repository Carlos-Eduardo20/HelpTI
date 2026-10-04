from html import escape
from functools import lru_cache
from math import cos, isfinite, pi, sin, sqrt
from urllib.parse import quote


DIAGNOSTICOS = {
    "Gabinete": {
        "erros": "Botão Power com mau contato ou acúmulo de poeira nos filtros de ar.",
        "solucao": "Verifique os cabos do Painel Frontal conectados à placa-mãe e realize a limpeza periódica das saídas de ar.",
    },
    "Placa-mãe": {
        "erros": "Curto-circuito, BIOS corrompida ou capacitores estufados.",
        "solucao": "Faça o reset da BIOS (Clear CMOS), verifique os espaçadores do gabinete e teste com outra fonte de alimentação.",
    },
    "Processador": {
        "erros": "Superaquecimento (Overheating) ou pinos dobrados.",
        "solucao": "Substitua a pasta térmica, limpe o cooler e certifique-se de que o sistema de refrigeração está firmemente instalado.",
    },
    "Módulos de RAM": {
        "erros": "Tela azul (BSOD), apitos de erro na inicialização ou memória não reconhecida.",
        "solucao": "Limpe os contatos dourados com uma borracha escolar macia e teste os módulos em slots diferentes.",
    },
    "Placa de vídeo": {
        "erros": "Artefatos visuais na tela, ausência de vídeo ou ventoinhas paradas.",
        "solucao": "Verifique se os cabos de alimentação PCIe estão bem conectados e atualize os drivers de vídeo.",
    },
    "Fonte de alimentação": {
        "erros": "Computador desliga sozinho em carga alta ou não liga.",
        "solucao": "Utilize um testador de fonte para verificar as tensões de 12V, 5V e 3.3V antes de substituir a unidade.",
    },
    "HD/SSD": {
        "erros": "Lentidão extrema, erros de I/O ou sistema operacional não encontrado.",
        "solucao": "Verifique a saúde do disco com diagnósticos S.M.A.R.T. e troque o cabo Sata ou o slot M.2.",
    },
}

PARTES = (
    {"key": "Gabinete", "label": (0, 2.95, -0.5)},
    {"key": "Placa-mãe", "label": (0, 2.55, -1.1)},
    {"key": "Processador", "label": (-0.35, 2.4, -0.85)},
    {"key": "Módulos de RAM", "label": (0.55, 2.25, -0.8)},
    {"key": "Placa de vídeo", "label": (0.35, 1.4, -0.2)},
    {"key": "Fonte de alimentação", "label": (-0.62, 1.05, 0.65)},
    {"key": "HD/SSD", "label": (0.68, 0.65, 0.6)},
)

_COLORS = {
    "DARK": "#303538",
    "FRAME": "#555B5E",
    "PCB": "#26372F",
    "ACCENT": "#899398",
    "GOLD": "#B58A52",
    "BODY": "#AEB6B8",
    "METAL": "#D0D4D2",
}
_FACE_SHADE = (0.64, 1.12, 0.83, 0.73, 0.94, 0.77)
_WIDTH, _HEIGHT = 760, 560
_TARGET = (0, 1.2, 0)
_DEFAULT_AZIMUTH, _DEFAULT_ELEVATION = 18, 18
_FOV_SCALE = _HEIGHT / (2 * sin(21 * pi / 180))


def _add(left, right):
    return tuple(a + b for a, b in zip(left, right))


def _dot(left, right):
    return sum(a * b for a, b in zip(left, right))


def _scale(vector, factor):
    return tuple(value * factor for value in vector)


def _cross(left, right):
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def _unit(vector):
    length = sqrt(_dot(vector, vector))
    if not length:
        raise ValueError("A geometria 3D exige um vetor diferente de zero.")
    return _scale(vector, 1 / length)


def _shade(color, factor):
    channels = (int(color[index:index + 2], 16) for index in (1, 3, 5))
    return "#" + "".join(f"{min(255, int(channel * factor)):02x}" for channel in channels)


def _normalizar_orientacao(value, default, minimum, maximum):
    try:
        angle = float(value)
    except (TypeError, ValueError):
        return default
    if not isfinite(angle):
        return default
    if minimum is None:
        return angle % 360
    return min(maximum, max(minimum, angle))


@lru_cache(maxsize=128)
def _camera_frame(azimuth, elevation):
    distance = sqrt(2.2 ** 2 + 7 ** 2)
    azimuth_radians = azimuth * pi / 180
    elevation_radians = elevation * pi / 180
    horizontal_distance = distance * cos(elevation_radians)
    camera = (
        _TARGET[0] + horizontal_distance * sin(azimuth_radians),
        _TARGET[1] + distance * sin(elevation_radians),
        _TARGET[2] + horizontal_distance * cos(azimuth_radians),
    )
    forward = _unit(tuple(target - position for target, position in zip(_TARGET, camera)))
    right = _unit(_cross(forward, (0, 1, 0)))
    up = _cross(right, forward)
    return camera, right, up, forward


def _project(point, azimuth, elevation):
    camera, right, up, forward = _camera_frame(azimuth, elevation)
    relative = tuple(value - position for value, position in zip(point, camera))
    depth = _dot(relative, forward)
    if depth <= 0:
        raise ValueError("A geometria 3D está atrás da câmera.")
    x = _WIDTH / 2 + _dot(relative, right) * _FOV_SCALE / depth
    y = _HEIGHT / 2 - _dot(relative, up) * _FOV_SCALE / depth
    return x, y, depth


def _mesh_box(center, dimensions, color, azimuth, elevation, *, opacity=1, glow=False, rotation_z=0):
    x, y, z = center
    width, height, depth = dimensions
    x0, x1 = x - width / 2, x + width / 2
    y0, y1 = y - height / 2, y + height / 2
    z0, z1 = z - depth / 2, z + depth / 2
    vertices = (
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    )
    if rotation_z:
        vertices = tuple(
            (x + (vertex_x - x) * cos(rotation_z) - (vertex_y - y) * sin(rotation_z),
             y + (vertex_x - x) * sin(rotation_z) + (vertex_y - y) * cos(rotation_z),
             vertex_z)
            for vertex_x, vertex_y, vertex_z in vertices
        )
    faces = ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4),
             (2, 3, 7, 6), (1, 2, 6, 5), (4, 7, 3, 0))
    projected = [_project(vertex, azimuth, elevation) for vertex in vertices]
    meshes = []
    for face_index, face in enumerate(faces):
        face_depth = sum(projected[index][2] for index in face) / len(face)
        points = " ".join(
            f"{projected[index][0]:.1f},{projected[index][1]:.1f}" for index in face
        )
        meshes.append({
            "depth": face_depth,
            "points": points,
            "color": color,
            "shade": _FACE_SHADE[face_index],
            "opacity": opacity,
            "glow": glow,
        })
    return meshes


def _mesh_cylinder(center, radius, length, color, axis, azimuth, elevation, *, segments=18):
    direction = _unit(axis)
    reference = (0, 0, 1) if abs(direction[2]) < 0.9 else (0, 1, 0)
    tangent = _unit(_cross(direction, reference))
    bitangent = _cross(direction, tangent)
    start = _add(center, _scale(direction, -length / 2))
    end = _add(center, _scale(direction, length / 2))
    first_ring = []
    second_ring = []
    for index in range(segments):
        angle = 2 * pi * index / segments
        offset = _add(_scale(tangent, radius * cos(angle)),
                      _scale(bitangent, radius * sin(angle)))
        first_ring.append(_project(_add(start, offset), azimuth, elevation))
        second_ring.append(_project(_add(end, offset), azimuth, elevation))

    faces = []
    for index in range(segments):
        next_index = (index + 1) % segments
        quad = (first_ring[index], first_ring[next_index],
                second_ring[next_index], second_ring[index])
        faces.append({
            "depth": sum(vertex[2] for vertex in quad) / len(quad),
            "points": " ".join(f"{vertex[0]:.1f},{vertex[1]:.1f}" for vertex in quad),
            "color": color,
            "shade": 0.72 + 0.38 * (index % 4) / 3,
            "opacity": 1,
            "glow": False,
        })

    for ring in (first_ring, second_ring):
        faces.append({
            "depth": sum(vertex[2] for vertex in ring) / len(ring),
            "points": " ".join(f"{vertex[0]:.1f},{vertex[1]:.1f}" for vertex in ring),
            "color": _shade(color, 1.08),
            "shade": 1,
            "opacity": 1,
            "glow": False,
        })
    return faces


def _add_box(
    meshes, key, parent, local, dimensions, color, azimuth, elevation,
    *, opacity=1, glow=False, rotation_z=0
):
    center = _add(parent, local)
    meshes.extend((key, face) for face in _mesh_box(
        center, dimensions, color, azimuth, elevation,
        opacity=opacity, glow=glow, rotation_z=rotation_z
    ))


def _add_cylinder(meshes, key, parent, local, radius, length, color, axis, azimuth, elevation):
    meshes.extend((key, face) for face in _mesh_cylinder(
        _add(parent, local), radius, length, color, axis, azimuth, elevation
    ))


def _build_parts(azimuth, elevation):
    meshes = []

    # Gabinete aberto, com base, painel traseiro e trilhos para deixar as peças visíveis.
    case = (0, 0, 0)
    _add_box(meshes, "Gabinete", case, (0, 0.05, 0), (2.3, 0.1, 2.7),
             _COLORS["DARK"], azimuth, elevation)
    _add_box(meshes, "Gabinete", case, (0, 1.3, -1.32), (2.3, 2.5, 0.08),
             _COLORS["FRAME"], azimuth, elevation)
    for x in (-1.12, 1.12):
        _add_box(meshes, "Gabinete", case, (x, 1.3, 1.32), (0.07, 2.5, 0.07),
                 _COLORS["FRAME"], azimuth, elevation)
    for y in (0.08, 2.52):
        _add_box(meshes, "Gabinete", case, (0, y, 1.32), (2.3, 0.08, 0.07),
                 _COLORS["FRAME"], azimuth, elevation)

    board = (0, 1.25, -1.2)
    _add_box(meshes, "Placa-mãe", board, (0, 0, 0), (1.9, 1.9, 0.07),
             _COLORS["PCB"], azimuth, elevation)
    _add_box(meshes, "Placa-mãe", board, (-0.55, 0.7, 0.1), (0.5, 0.35, 0.16),
             _COLORS["BODY"], azimuth, elevation)
    _add_box(meshes, "Placa-mãe", board, (0.55, -0.45, 0.06), (0.45, 0.45, 0.05),
             _COLORS["DARK"], azimuth, elevation)
    for x, y in ((0.15, 0.2), (0.4, 0.2), (0.27, -0.1)):
        _add_cylinder(meshes, "Placa-mãe", board, (x, y, 0.1),
                      0.06, 0.14, _COLORS["DARK"], (0, 0, 1), azimuth, elevation)

    cpu = (-0.35, 1.7, -1.05)
    _add_box(meshes, "Processador", cpu, (0, 0, 0), (0.5, 0.5, 0.08),
             _COLORS["DARK"], azimuth, elevation)
    _add_box(meshes, "Processador", cpu, (0, 0, 0.06), (0.4, 0.4, 0.04),
             _COLORS["METAL"], azimuth, elevation)
    _add_box(meshes, "Processador", cpu, (0, 0, 0.083), (0.22, 0.02, 0.006),
             _COLORS["ACCENT"], azimuth, elevation)

    ram = (0.55, 1.5, -0.9)
    for x in (0, 0.24):
        _add_box(meshes, "Módulos de RAM", ram, (x, 0, 0), (0.1, 0.95, 0.3),
                 _COLORS["PCB"], azimuth, elevation)
        _add_box(meshes, "Módulos de RAM", ram, (x, 0.18, 0), (0.12, 0.5, 0.34),
                 _COLORS["BODY"], azimuth, elevation)
        _add_box(meshes, "Módulos de RAM", ram, (x, -0.4, 0), (0.08, 0.1, 0.26),
                 _COLORS["GOLD"], azimuth, elevation)

    gpu = (0.35, 0.72, -0.3)
    _add_box(meshes, "Placa de vídeo", gpu, (0, 0, 0), (1.35, 0.45, 0.85),
             _COLORS["DARK"], azimuth, elevation)
    _add_box(meshes, "Placa de vídeo", gpu, (0, 0.28, 0), (1.39, 0.06, 0.89),
             _COLORS["BODY"], azimuth, elevation)
    for x in (-0.32, 0.32):
        _add_cylinder(meshes, "Placa de vídeo", gpu, (x, 0.33, 0),
                      0.24, 0.05, _COLORS["DARK"], (0, 1, 0), azimuth, elevation)
        _add_cylinder(meshes, "Placa de vídeo", gpu, (x, 0.34, 0),
                      0.08, 0.06, _COLORS["METAL"], (0, 1, 0), azimuth, elevation)
    _add_box(meshes, "Placa de vídeo", gpu, (0, -0.05, -0.45),
             (1.25, 0.32, 0.08), _COLORS["PCB"], azimuth, elevation)
    for x in (-0.42, 0.42):
        _add_box(meshes, "Placa de vídeo", gpu, (x, 0.31, 0.04),
                 (0.025, 0.035, 0.025), _COLORS["GOLD"], azimuth, elevation)

    psu = (-0.62, 0.45, 0.65)
    _add_box(meshes, "Fonte de alimentação", psu, (0, 0, 0), (0.75, 0.65, 1.0),
             _COLORS["DARK"], azimuth, elevation)
    _add_box(meshes, "Fonte de alimentação", psu, (0, 0, 0.52),
             (0.5, 0.38, 0.03), _COLORS["BODY"], azimuth, elevation)
    _add_cylinder(meshes, "Fonte de alimentação", psu, (0, 0.35, 0),
                  0.24, 0.05, _COLORS["BODY"], (0, 1, 0), azimuth, elevation)
    _add_box(meshes, "Fonte de alimentação", psu, (0.25, -0.18, 0.52),
             (0.08, 0.05, 0.04), _COLORS["ACCENT"], azimuth, elevation)

    ssd = (0.68, 0.15, 0.6)
    _add_box(meshes, "HD/SSD", ssd, (0, 0, 0), (0.6, 0.14, 0.95),
             _COLORS["DARK"], azimuth, elevation)
    _add_box(meshes, "HD/SSD", ssd, (0, 0.09, 0),
             (0.42, 0.05, 0.62), _COLORS["BODY"], azimuth, elevation)
    _add_box(meshes, "HD/SSD", ssd, (0, -0.09, 0),
             (0.6, 0.05, 0.95), _COLORS["METAL"], azimuth, elevation)
    return meshes


def _render_mesh(key, face, selected):
    highlighted = key == selected
    color = "#B58A52" if highlighted else face["color"]
    shade = 1 if highlighted else face["shade"]
    opacity = face["opacity"]
    return (
        f'<polygon points="{face["points"]}" fill="{_shade(color, shade)}" '
        f'fill-opacity="{opacity}" stroke="#303538" stroke-width="1.1" '
        'stroke-linejoin="round"/>'
    )


def render_pc_svg(
    selected_part=None,
    azimuth=_DEFAULT_AZIMUTH,
    elevation=_DEFAULT_ELEVATION,
):
    """Gera a cena 3D detalhada do PC como SVG usando somente geometria Python."""
    selected = selected_part if selected_part in DIAGNOSTICOS else None
    azimuth = _normalizar_orientacao(azimuth, _DEFAULT_AZIMUTH, None, None)
    elevation = _normalizar_orientacao(elevation, _DEFAULT_ELEVATION, 8, 65)
    meshes = _build_parts(azimuth, elevation)
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" class="model" viewBox="0 0 {_WIDTH} {_HEIGHT}" '
        'role="img" aria-label="Modelo 3D detalhado de uma torre de computador">',
        '<rect width="760" height="560" rx="14" fill="#F1F2F0"/>',
        '<ellipse cx="380" cy="488" rx="205" ry="24" fill="#DDE5E8" opacity=".65"/>',
    ]

    for key, face in sorted(meshes, key=lambda item: item[1]["depth"], reverse=True):
        svg.append(
            f'<a class="component component-{quote(key, safe="")}" '
            f'href="/educacao/pc-explorer?componente={quote(key, safe="")}'
            f'&amp;azimute={azimuth:.1f}&amp;elevacao={elevation:.1f}" '
            f'aria-label="Selecionar {escape(key, quote=True)}">'
            f'{_render_mesh(key, face, selected)}</a>'
        )

    for part in PARTES:
        key = part["key"]
        x, y, _ = _project(part["label"], azimuth, elevation)
        label = escape(key, quote=True)
        svg.append(
            f'<a class="component-label" href="/educacao/pc-explorer?componente={quote(key, safe="")}'
            f'&amp;azimute={azimuth:.1f}&amp;elevacao={elevation:.1f}" '
            f'aria-label="Selecionar {label}">'
            f'<rect x="{x - 72:.1f}" y="{y - 13:.1f}" width="144" height="25" rx="12" '
            'fill="#FFFFFF" fill-opacity=".94" stroke="#CBD5E1"/>'
            f'<text x="{x:.1f}" y="{y + 4:.1f}" text-anchor="middle" '
            f'font-family="Arial, sans-serif" font-size="12" font-weight="700" fill="#1E293B">{label}</text>'
            "</a>"
        )

    svg.append("</svg>")
    return "".join(svg)


_DRAG_SCRIPT = """
(() => {
  const viewport = document.getElementById("modelViewport");
  const status = document.getElementById("modelStatus");
  let azimuth = 18;
  let elevation = 18;
  let pointerId = null;
  let captured = false;
  let startX = 0;
  let startY = 0;
  let previousX = 0;
  let previousY = 0;
  let dragged = false;
  let suppressClick = false;
  let requestId = 0;
  let animationFrame = 0;

  viewport.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    pointerId = event.pointerId;
    startX = previousX = event.clientX;
    startY = previousY = event.clientY;
    dragged = false;
    captured = false;
  });

  viewport.addEventListener("pointermove", (event) => {
    if (event.pointerId !== pointerId) return;
    const deltaX = event.clientX - previousX;
    const deltaY = event.clientY - previousY;
    previousX = event.clientX;
    previousY = event.clientY;
    if (!dragged && Math.abs(event.clientX - startX) + Math.abs(event.clientY - startY) > 4) {
      dragged = true;
      if (!captured) {
        viewport.setPointerCapture(pointerId);
        captured = true;
        viewport.classList.add("dragging");
      }
    }
    if (dragged) {
      azimuth = (azimuth + deltaX * 0.65 + 360) % 360;
      elevation = Math.min(65, Math.max(8, elevation - deltaY * 0.45));
    }
    if (dragged && !animationFrame) {
      animationFrame = requestAnimationFrame(updateModel);
    }
  });

  async function updateModel() {
    animationFrame = 0;
    const currentRequest = ++requestId;
    const params = new URLSearchParams({
      azimute: azimuth.toFixed(1),
      elevacao: elevation.toFixed(1),
      componente: new URLSearchParams(location.search).get("componente") || ""
    });
    history.replaceState(null, "", `${location.pathname}?${params}`);
    try {
      const response = await fetch(`/educacao/pc-explorer/modelo.svg?${params}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const svg = await response.text();
      if (currentRequest === requestId) {
        viewport.innerHTML = svg;
        status.textContent = "";
      }
    } catch (error) {
      if (currentRequest === requestId) {
        status.textContent = "Não foi possível atualizar a visualização 3D.";
        console.error("Falha ao girar o modelo 3D:", error);
      }
    }
  }

  function stopDragging(event) {
    if (event.pointerId !== pointerId) return;
    if (dragged) {
      suppressClick = true;
      if (!animationFrame) animationFrame = requestAnimationFrame(updateModel);
      setTimeout(() => { suppressClick = false; }, 0);
    }
    pointerId = null;
    captured = false;
    viewport.classList.remove("dragging");
  }

  viewport.addEventListener("pointerup", stopDragging);
  viewport.addEventListener("pointercancel", stopDragging);
  viewport.addEventListener("click", (event) => {
    if (suppressClick) {
      event.preventDefault();
      event.stopPropagation();
      suppressClick = false;
    }
  }, true);
})();
"""


def render_pc_explorer(selected_part=None, azimuth=_DEFAULT_AZIMUTH, elevation=_DEFAULT_ELEVATION):
    selected = selected_part if selected_part in DIAGNOSTICOS else None
    azimuth = _normalizar_orientacao(azimuth, _DEFAULT_AZIMUTH, None, None)
    elevation = _normalizar_orientacao(elevation, _DEFAULT_ELEVATION, 8, 65)
    buttons = "".join(
        '<a class="part-button{}" href="/educacao/pc-explorer?componente={}&amp;azimute={:.1f}&amp;elevacao={:.1f}"{}>{}</a>'.format(
            " selected" if part == selected else "",
            quote(part, safe=""),
            azimuth,
            elevation,
            ' aria-current="true"' if part == selected else "",
            escape(part),
        )
        for part in DIAGNOSTICOS
    )

    if selected:
        diagnosis = DIAGNOSTICOS[selected]
        diagnosis_content = (
            f"<h3>{escape(selected)}</h3>"
            f"<h4>Falhas comuns</h4><p>{escape(diagnosis['erros'])}</p>"
            f"<h4 class=\"solution-title\">Solução recomendada</h4>"
            f"<p>{escape(diagnosis['solucao'])}</p>"
        )
    else:
        diagnosis_content = (
            '<p class="empty-state">Selecione um componente para ver as falhas '
            "comuns e as soluções recomendadas.</p>"
        )

    return f"""<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Explorador 3D de componentes | HelpTI</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; color: #1E1B18; font: 14px Arial, sans-serif; }}
    .explorer {{ display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(250px, .8fr); gap: 20px; }}
    .card {{ min-width: 0; padding: 20px; border: 1px solid #E2DCD0; border-radius: 12px; background: #FFF; }}
    h2 {{ margin: 0 0 12px; font-size: 17px; }}
    .model {{ display: block; width: 100%; height: auto; }}
    .model-viewport {{ cursor: grab; touch-action: none; user-select: none; }}
    .model-viewport.dragging {{ cursor: grabbing; }}
    .component polygon {{ transition: fill .16s ease; }}
    .component:hover polygon {{ fill: #B58A52 !important; fill-opacity: 1 !important; }}
    .component-label {{ cursor: pointer; }}
    .component-label:hover rect {{ fill: #F4EBDD; stroke: #B58A52; }}
    .hint {{ margin: 10px 0 0; color: #6B7280; font-size: 12px; line-height: 1.5; }}
    .model-status {{ min-height: 16px; margin: 4px 0 0; color: #B91C1C; font-size: 12px; }}
    .parts {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }}
    .part-button {{ padding: 8px 10px; border: 1px solid #D1D5DB; border-radius: 6px; color: #1F2937; background: #F9FAFB; font-size: 12px; text-decoration: none; }}
    .part-button:hover, .part-button.selected {{ border-color: #B58A52; color: #59452D; background: #F4EBDD; }}
    .diagnosis h3 {{ margin: 4px 0 22px; font-size: 20px; }}
    .diagnosis h4 {{ margin: 18px 0 6px; color: #76572F; font-size: 13px; }}
    .diagnosis h4.solution-title {{ color: #2563EB; }}
    .diagnosis p {{ margin: 0; color: #4B5563; line-height: 1.6; }}
    .diagnosis .empty-state {{ display: grid; min-height: 200px; place-items: center; text-align: center; color: #6B7280; }}
    @media (max-width: 760px) {{ .explorer {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <main class="explorer">
    <section class="card">
      <h2>Torre interativa 3D</h2>
      <div id="modelViewport" class="model-viewport" aria-label="Arraste para girar o modelo 3D">
        {render_pc_svg(selected, azimuth, elevation)}
      </div>
      <p class="hint">Clique e arraste o modelo para girar. Passe o mouse sobre uma peça para destacá-la ou clique para consultar o diagnóstico.</p>
      <p id="modelStatus" class="model-status" role="status" aria-live="polite"></p>
      <nav class="parts" aria-label="Selecionar componente">{buttons}</nav>
    </section>
    <section class="card diagnosis" aria-live="polite">
      <h2>Diagnóstico do componente</h2>
      {diagnosis_content}
    </section>
  </main>
  <script>{_DRAG_SCRIPT}</script>
</body>
</html>"""
