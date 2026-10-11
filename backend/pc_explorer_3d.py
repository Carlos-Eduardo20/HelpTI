from functools import lru_cache
from html import escape
from math import cos, isfinite, pi, sin, sqrt
from urllib.parse import quote


DIAGNOSTICOS = {
    "Gabinete": {
        "erros": "Botão Power com mau contato ou filtros de ar obstruídos por poeira.",
        "solucao": "Verifique os conectores do painel frontal e limpe os filtros de ar com o equipamento desligado.",
    },
    "Placa-mãe": {
        "erros": "Falha de inicialização, BIOS corrompida ou componentes com sinais de superaquecimento.",
        "solucao": "Confira os cabos de alimentação, verifique os espaçadores e faça o reset da BIOS (Clear CMOS).",
    },
    "Processador": {
        "erros": "Temperatura elevada, desligamentos inesperados ou falha durante a inicialização.",
        "solucao": "Confira a fixação do cooler, renove a pasta térmica e confirme se a ventoinha está conectada ao CPU_FAN.",
    },
    "Módulos de RAM": {
        "erros": "Tela azul, bipes na inicialização ou memória não reconhecida pelo sistema.",
        "solucao": "Desligue o computador, recoloque os módulos e teste um de cada vez em slots recomendados pelo fabricante.",
    },
    "Placa de vídeo": {
        "erros": "Artefatos na tela, ausência de vídeo ou ventoinhas que não giram sob carga.",
        "solucao": "Confira os conectores PCIe, a instalação da placa e os drivers de vídeo.",
    },
    "Fonte de alimentação": {
        "erros": "O computador não liga ou reinicia quando os componentes estão sob carga.",
        "solucao": "Verifique os cabos e a potência recomendada. Não abra a fonte: capacitores internos podem manter carga perigosa.",
    },
    "HD/SSD": {
        "erros": "Inicialização lenta, erros de leitura ou unidade ausente no sistema.",
        "solucao": "Confira cabos e conexões M.2 e consulte o diagnóstico S.M.A.R.T. para verificar a saúde da unidade.",
    },
}

PARTES = (
    {"key": "Gabinete", "label": (0, 2.72, -0.5)},
    {"key": "Placa-mãe", "label": (0, 2.35, -1.1)},
    {"key": "Processador", "label": (-0.35, 2.12, -0.85)},
    {"key": "Módulos de RAM", "label": (0.75, 2.16, -0.8)},
    {"key": "Placa de vídeo", "label": (0.45, 1.10, -0.2)},
    {"key": "Fonte de alimentação", "label": (-0.70, 0.72, 0.65)},
    {"key": "HD/SSD", "label": (0.78, 0.42, 0.6)},
)

_COLORS = {
    "CASE": "#29313B",
    "FRAME": "#687586",
    "PCB": "#173D38",
    "PCB_EDGE": "#2C6255",
    "DARK": "#111923",
    "METAL": "#C1CBD3",
    "STEEL": "#7F8D9A",
    "GOLD": "#D5A84F",
    "RGB": "#55D6BE",
    "FAN": "#283744",
}
_FACE_SHADE = (0.64, 1.12, 0.83, 0.73, 0.94, 0.77)
_WIDTH, _HEIGHT = 760, 560
_TARGET = (0, 1.25, 0)
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


def _mesh_box(center, dimensions, color, azimuth, elevation, rotation_z=0):
    x, y, z = center
    width, height, depth = dimensions
    vertices = (
        (x - width / 2, y - height / 2, z - depth / 2),
        (x + width / 2, y - height / 2, z - depth / 2),
        (x + width / 2, y + height / 2, z - depth / 2),
        (x - width / 2, y + height / 2, z - depth / 2),
        (x - width / 2, y - height / 2, z + depth / 2),
        (x + width / 2, y - height / 2, z + depth / 2),
        (x + width / 2, y + height / 2, z + depth / 2),
        (x - width / 2, y + height / 2, z + depth / 2),
    )
    if rotation_z:
        vertices = tuple(
            (
                x + (vx - x) * cos(rotation_z) - (vy - y) * sin(rotation_z),
                y + (vx - x) * sin(rotation_z) + (vy - y) * cos(rotation_z),
                vz,
            )
            for vx, vy, vz in vertices
        )
    faces = (
        (0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4),
        (2, 3, 7, 6), (1, 2, 6, 5), (4, 7, 3, 0),
    )
    projected = [_project(vertex, azimuth, elevation) for vertex in vertices]
    return [
        {
            "depth": sum(projected[index][2] for index in face) / len(face),
            "points": " ".join(
                f"{projected[index][0]:.1f},{projected[index][1]:.1f}" for index in face
            ),
            "color": color,
            "shade": _FACE_SHADE[index],
        }
        for index, face in enumerate(faces)
    ]


def _mesh_cylinder(center, radius, length, color, axis, azimuth, elevation, segments=20):
    direction = _unit(axis)
    reference = (0, 0, 1) if abs(direction[2]) < 0.9 else (0, 1, 0)
    tangent = _unit(_cross(direction, reference))
    bitangent = _cross(direction, tangent)
    start = _add(center, _scale(direction, -length / 2))
    end = _add(center, _scale(direction, length / 2))
    rings = []
    for endpoint in (start, end):
        rings.append([
            _project(
                _add(endpoint, _add(
                    _scale(tangent, radius * cos(2 * pi * index / segments)),
                    _scale(bitangent, radius * sin(2 * pi * index / segments)),
                )),
                azimuth,
                elevation,
            )
            for index in range(segments)
        ])

    faces = []
    for index in range(segments):
        following = (index + 1) % segments
        quad = (rings[0][index], rings[0][following], rings[1][following], rings[1][index])
        faces.append({
            "depth": sum(point[2] for point in quad) / 4,
            "points": " ".join(f"{point[0]:.1f},{point[1]:.1f}" for point in quad),
            "color": color,
            "shade": 0.72 + 0.34 * (index % 4) / 3,
        })
    for ring in rings:
        faces.append({
            "depth": sum(point[2] for point in ring) / len(ring),
            "points": " ".join(f"{point[0]:.1f},{point[1]:.1f}" for point in ring),
            "color": _shade(color, 1.12),
            "shade": 1,
        })
    return faces


def _add_box(meshes, component, center, dimensions, color, azimuth, elevation, rotation_z=0):
    meshes.extend(
        (component, face)
        for face in _mesh_box(center, dimensions, color, azimuth, elevation, rotation_z)
    )


def _add_cylinder(meshes, component, center, radius, length, color, axis, azimuth, elevation):
    meshes.extend(
        (component, face)
        for face in _mesh_cylinder(center, radius, length, color, axis, azimuth, elevation)
    )


def _build_parts(azimuth, elevation):
    meshes = []
    _add_box(meshes, "Gabinete", (0, 0.06, 0), (2.35, 0.12, 2.72), _COLORS["CASE"], azimuth, elevation)
    _add_box(meshes, "Gabinete", (0, 1.30, -1.34), (2.35, 2.50, 0.08), _COLORS["FRAME"], azimuth, elevation)
    for x in (-1.14, 1.14):
        _add_box(meshes, "Gabinete", (x, 1.30, 1.32), (0.07, 2.50, 0.07), _COLORS["FRAME"], azimuth, elevation)
    for y in (0.12, 2.50):
        _add_box(meshes, "Gabinete", (0, y, 1.32), (2.30, 0.07, 0.07), _COLORS["FRAME"], azimuth, elevation)

    board = (-0.02, 1.30, -1.17)
    _add_box(meshes, "Placa-mãe", board, (1.92, 2.14, 0.08), _COLORS["PCB"], azimuth, elevation)
    _add_box(meshes, "Placa-mãe", (-0.70, 0.78, -1.105), (0.32, 0.36, 0.08), _COLORS["STEEL"], azimuth, elevation)
    for x, y, width, height in (
        (0.48, 0.72, 0.42, 0.35), (-0.70, 1.95, 0.27, 0.18),
        (0.65, 1.98, 0.28, 0.14), (-0.66, 1.55, 0.08, 0.24),
    ):
        _add_box(meshes, "Placa-mãe", (x, y, -1.095), (width, height, 0.07), _COLORS["DARK"], azimuth, elevation)
    for x in (-0.78, 0.75):
        _add_box(meshes, "Placa-mãe", (x, 1.12, -1.085), (0.055, 0.74, 0.045), _COLORS["GOLD"], azimuth, elevation)
    for x, y in ((-0.8, 0.45), (0.8, 0.45), (-0.8, 2.2), (0.8, 2.2)):
        _add_cylinder(meshes, "Placa-mãe", (x, y, -1.07), 0.045, 0.06, _COLORS["GOLD"], (0, 0, 1), azimuth, elevation)

    cpu = (-0.35, 1.82, -0.92)
    _add_box(meshes, "Processador", cpu, (0.62, 0.62, 0.14), _COLORS["DARK"], azimuth, elevation)
    _add_box(meshes, "Processador", (-0.35, 1.82, -0.82), (0.48, 0.48, 0.08), _COLORS["METAL"], azimuth, elevation)
    _add_box(meshes, "Processador", (-0.35, 1.82, -0.75), (0.38, 0.38, 0.10), _COLORS["STEEL"], azimuth, elevation)
    _add_cylinder(meshes, "Processador", (-0.35, 1.82, -0.65), 0.18, 0.12, _COLORS["FAN"], (0, 0, 1), azimuth, elevation)
    for index in range(4):
        _add_box(meshes, "Processador", (-0.35, 1.82, -0.56), (0.56, 0.025, 0.025), _COLORS["METAL"], azimuth, elevation, index * pi / 4)

    for x in (0.38, 0.62):
        _add_box(meshes, "Módulos de RAM", (x, 1.72, -0.96), (0.13, 0.92, 0.25), _COLORS["PCB_EDGE"], azimuth, elevation)
        _add_box(meshes, "Módulos de RAM", (x, 1.72, -0.81), (0.12, 0.62, 0.08), _COLORS["STEEL"], azimuth, elevation)
        _add_box(meshes, "Módulos de RAM", (x, 1.24, -0.78), (0.11, 0.10, 0.035), _COLORS["GOLD"], azimuth, elevation)

    gpu = (0.18, 0.82, -0.12)
    _add_box(meshes, "Placa de vídeo", gpu, (1.58, 0.46, 0.82), _COLORS["DARK"], azimuth, elevation)
    _add_box(meshes, "Placa de vídeo", (0.18, 1.07, -0.12), (1.52, 0.06, 0.78), _COLORS["STEEL"], azimuth, elevation)
    for x in (-0.22, 0.52):
        _add_cylinder(meshes, "Placa de vídeo", (x, 0.85, 0.32), 0.23, 0.06, _COLORS["FAN"], (0, 0, 1), azimuth, elevation)
        _add_cylinder(meshes, "Placa de vídeo", (x, 0.85, 0.36), 0.075, 0.04, _COLORS["METAL"], (0, 0, 1), azimuth, elevation)
        _add_cylinder(meshes, "Placa de vídeo", (x, 0.85, 0.39), 0.028, 0.025, _COLORS["RGB"], (0, 0, 1), azimuth, elevation)
    _add_box(meshes, "Placa de vídeo", (0.18, 0.52, -0.59), (1.35, 0.28, 0.08), _COLORS["PCB_EDGE"], azimuth, elevation)
    for x in (-0.38, 0.74):
        _add_box(meshes, "Placa de vídeo", (x, 1.12, -0.02), (0.035, 0.04, 0.035), _COLORS["GOLD"], azimuth, elevation)

    _add_box(meshes, "Fonte de alimentação", (-0.62, 0.44, 0.62), (0.76, 0.68, 1.05), _COLORS["DARK"], azimuth, elevation)
    _add_box(meshes, "Fonte de alimentação", (-0.62, 0.44, 1.16), (0.55, 0.45, 0.035), _COLORS["STEEL"], azimuth, elevation)
    _add_cylinder(meshes, "Fonte de alimentação", (-0.62, 0.44, 1.19), 0.22, 0.035, _COLORS["FAN"], (0, 0, 1), azimuth, elevation)
    _add_box(meshes, "HD/SSD", (0.72, 0.42, 0.65), (0.58, 0.14, 0.92), _COLORS["DARK"], azimuth, elevation)
    _add_box(meshes, "HD/SSD", (0.72, 0.51, 0.65), (0.40, 0.035, 0.62), _COLORS["STEEL"], azimuth, elevation)
    _add_box(meshes, "HD/SSD", (0.72, 0.58, 0.65), (0.22, 0.025, 0.06), _COLORS["GOLD"], azimuth, elevation)
    return meshes


def render_pc_svg(selected_part=None, azimuth=_DEFAULT_AZIMUTH, elevation=_DEFAULT_ELEVATION):
    selected = selected_part if selected_part in DIAGNOSTICOS else None
    azimuth = _normalizar_orientacao(azimuth, _DEFAULT_AZIMUTH, None, None)
    elevation = _normalizar_orientacao(elevation, _DEFAULT_ELEVATION, 8, 65)
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" class="model" viewBox="0 0 {_WIDTH} {_HEIGHT}" role="img" aria-label="Modelo 3D interativo de um computador">',
        '<defs><linearGradient id="scene" x2="0" y2="1"><stop stop-color="#17212d"/><stop offset="1" stop-color="#0d131c"/></linearGradient><radialGradient id="halo"><stop stop-color="#2c575b" stop-opacity=".52"/><stop offset="1" stop-color="#17212d" stop-opacity="0"/></radialGradient></defs>',
        '<rect width="760" height="560" rx="18" fill="url(#scene)"/>',
        '<ellipse cx="380" cy="283" rx="300" ry="275" fill="url(#halo)"/>',
        '<ellipse cx="380" cy="492" rx="190" ry="20" fill="#05090e" opacity=".66"/>',
    ]
    meshes = _build_parts(azimuth, elevation)
    for key, face in sorted(meshes, key=lambda item: item[1]["depth"], reverse=True):
        color = "#5eead4" if key == selected else face["color"]
        shade = 1 if key == selected else face["shade"]
        svg.append(
            f'<a class="component component-{quote(key, safe="")}" '
            f'href="/educacao/pc-explorer?componente={quote(key, safe="")}'
            f'&amp;azimute={azimuth:.1f}&amp;elevacao={elevation:.1f}" '
            f'aria-label="Selecionar {escape(key, quote=True)}">'
            f'<polygon points="{face["points"]}" fill="{_shade(color, shade)}" '
            'stroke="#101820" stroke-width="1.2" stroke-linejoin="round"/></a>'
        )

    for part in PARTES:
        key = part["key"]
        x, y, _ = _project(part["label"], azimuth, elevation)
        label = escape(key, quote=True)
        svg.append(
            f'<a class="component-label" href="/educacao/pc-explorer?componente={quote(key, safe="")}'
            f'&amp;azimute={azimuth:.1f}&amp;elevacao={elevation:.1f}" aria-label="Selecionar {label}">'
            f'<rect x="{x - 72:.1f}" y="{y - 13:.1f}" width="144" height="25" rx="12" '
            'fill="#101923" fill-opacity=".94" stroke="#536472"/>'
            f'<text x="{x:.1f}" y="{y + 4:.1f}" text-anchor="middle" '
            'font-family="Arial, sans-serif" font-size="11" font-weight="700" fill="#e5edf1">'
            f'{label}</text></a>'
        )
    svg.append("</svg>")
    return "".join(svg)


_DRAG_SCRIPT = """
(() => {
  const viewport = document.getElementById("modelViewport");
  const status = document.getElementById("modelStatus");
  const search = new URLSearchParams(location.search);
  const requestedAzimuth = Number(search.get("azimute"));
  const requestedElevation = Number(search.get("elevacao"));
  let azimuth = Number.isFinite(requestedAzimuth) ? requestedAzimuth : 18;
  let elevation = Number.isFinite(requestedElevation)
    ? Math.min(65, Math.max(8, requestedElevation))
    : 18;
  let pointerId = null;
  let startX = 0, startY = 0, previousX = 0, previousY = 0;
  let dragged = false, suppressClick = false, requestId = 0, animationFrame = 0;

  viewport.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    pointerId = event.pointerId;
    startX = previousX = event.clientX;
    startY = previousY = event.clientY;
    dragged = false;
  });
  viewport.addEventListener("pointermove", (event) => {
    if (event.pointerId !== pointerId) return;
    const dx = event.clientX - previousX, dy = event.clientY - previousY;
    previousX = event.clientX;
    previousY = event.clientY;
    if (!dragged && Math.abs(event.clientX - startX) + Math.abs(event.clientY - startY) > 4) {
      dragged = true;
      viewport.setPointerCapture(pointerId);
      viewport.classList.add("dragging");
    }
    if (!dragged) return;
    azimuth = (azimuth + dx * 0.65 + 360) % 360;
    elevation = Math.min(65, Math.max(8, elevation - dy * 0.45));
    if (!animationFrame) animationFrame = requestAnimationFrame(updateModel);
  });
  async function updateModel() {
    animationFrame = 0;
    const currentRequest = ++requestId;
    const params = new URLSearchParams({
      azimute: azimuth.toFixed(1),
      elevacao: elevation.toFixed(1),
      componente: search.get("componente") || ""
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
        status.textContent = "Não foi possível atualizar o modelo 3D.";
        console.error("Falha ao atualizar o modelo 3D:", error);
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
    viewport.classList.remove("dragging");
  }
  viewport.addEventListener("pointerup", stopDragging);
  viewport.addEventListener("pointercancel", stopDragging);
  viewport.addEventListener("click", (event) => {
    if (!suppressClick) return;
    event.preventDefault();
    event.stopPropagation();
    suppressClick = false;
  }, true);
})();
"""


def render_pc_explorer(selected_part=None, azimuth=_DEFAULT_AZIMUTH, elevation=_DEFAULT_ELEVATION):
    selected = selected_part if selected_part in DIAGNOSTICOS else None
    azimuth = _normalizar_orientacao(azimuth, _DEFAULT_AZIMUTH, None, None)
    elevation = _normalizar_orientacao(elevation, _DEFAULT_ELEVATION, 8, 65)
    button_links = []
    for key in DIAGNOSTICOS:
        selected_class = " selected" if key == selected else ""
        current_state = ' aria-current="true"' if key == selected else ""
        button_links.append(
            f'<a class="part-button{selected_class}" '
            f'href="/educacao/pc-explorer?componente={quote(key, safe="")}'
            f'&amp;azimute={azimuth:.1f}&amp;elevacao={elevation:.1f}"'
            f'{current_state}>{escape(key)}</a>'
        )
    buttons = "".join(button_links)
    if selected:
        diagnosis = DIAGNOSTICOS[selected]
        diagnosis_content = (
            f'<span class="component-kicker">COMPONENTE SELECIONADO</span>'
            f'<h3>{escape(selected)}</h3>'
            f'<h4>Falhas comuns</h4><p>{escape(diagnosis["erros"])}</p>'
            f'<h4 class="solution-title">O que verificar</h4><p>{escape(diagnosis["solucao"])}</p>'
        )
    else:
        diagnosis_content = (
            '<div class="empty-state"><span class="empty-icon">+</span>'
            '<p>Selecione uma peça no modelo para consultar sintomas e recomendações.</p></div>'
        )
    page = """<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Explorador 3D de componentes | HelpTI</title>
  <style>
    * { box-sizing: border-box; }
    body { margin: 0; padding: 18px; color: #18212b; background: #f3f5f7; font: 14px Inter, Arial, sans-serif; }
    .explorer { display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(245px, .8fr); gap: 16px; max-width: 1200px; margin: 0 auto; }
    .card { min-width: 0; padding: 18px; border: 1px solid #dfe5e9; border-radius: 16px; background: #fff; box-shadow: 0 8px 28px #15232d0a; }
    .card-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
    h2 { margin: 0; font-size: 16px; letter-spacing: -.02em; }
    .live-badge { padding: 5px 8px; border-radius: 99px; color: #087e6b; background: #e5f7f3; font-size: 10px; font-weight: 800; letter-spacing: .08em; }
    .model-viewport { overflow: hidden; border-radius: 12px; cursor: grab; touch-action: none; user-select: none; }
    .model-viewport.dragging { cursor: grabbing; }
    .model { display: block; width: 100%; height: auto; }
    .component polygon { transition: filter .15s ease; }
    .component:hover polygon { filter: brightness(1.3); stroke: #73e6d0; stroke-width: 2; }
    .component-label { cursor: pointer; }
    .component-label:hover rect { stroke: #73e6d0; stroke-width: 2; }
    .hint { margin: 10px 0 0; color: #74808b; font-size: 12px; line-height: 1.5; }
    .model-status { min-height: 16px; margin: 4px 0 0; color: #b42318; font-size: 12px; }
    .parts { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 9px; }
    .part-button { padding: 7px 9px; border: 1px solid #dce3e8; border-radius: 8px; color: #394652; background: #f8fafb; font-size: 11px; text-decoration: none; transition: .15s ease; }
    .part-button:hover, .part-button.selected { border-color: #41b9a3; color: #087e6b; background: #e8f8f5; }
    .diagnosis { min-height: 300px; }
    .component-kicker { color: #0b907b; font-size: 10px; font-weight: 800; letter-spacing: .1em; }
    .diagnosis h3 { margin: 7px 0 28px; font-size: 24px; letter-spacing: -.03em; }
    .diagnosis h4 { margin: 18px 0 7px; color: #627382; font-size: 11px; text-transform: uppercase; letter-spacing: .08em; }
    .diagnosis h4.solution-title { color: #0b907b; }
    .diagnosis p { margin: 0; color: #4d5b66; line-height: 1.7; }
    .empty-state { display: grid; min-height: 220px; align-content: center; justify-items: center; text-align: center; }
    .empty-icon { display: grid; width: 42px; height: 42px; margin-bottom: 12px; place-items: center; border-radius: 50%; color: #148e7b; background: #e5f7f3; font-size: 24px; }
    .empty-state p { max-width: 230px; color: #71808a; }
    @media (max-width: 700px) { body { padding: 10px; } .explorer { grid-template-columns: 1fr; gap: 10px; } .card { padding: 13px; } }
  </style>
</head>
<body>
  <main class="explorer">
    <section class="card">
      <div class="card-heading"><h2>Visão interna do computador</h2><span class="live-badge">MODELO INTERATIVO</span></div>
      <div id="modelViewport" class="model-viewport" aria-label="Arraste para girar o modelo 3D">__MODEL__</div>
      <p class="hint">Arraste para observar por outros ângulos. Clique em uma peça para ver os sintomas e as recomendações.</p>
      <p id="modelStatus" class="model-status" role="status" aria-live="polite"></p>
      <nav class="parts" aria-label="Selecionar componente">__BUTTONS__</nav>
    </section>
    <section class="card diagnosis" aria-live="polite">
      <div class="card-heading"><h2>Guia de diagnóstico</h2></div>
      __DIAGNOSIS__
    </section>
  </main>
  <script>__SCRIPT__</script>
</body>
</html>"""
    return (
        page.replace("__MODEL__", render_pc_svg(selected, azimuth, elevation))
        .replace("__BUTTONS__", buttons)
        .replace("__DIAGNOSIS__", diagnosis_content)
        .replace("__SCRIPT__", _DRAG_SCRIPT)
    )
