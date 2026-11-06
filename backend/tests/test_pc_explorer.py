import unittest
from pathlib import Path
from unittest.mock import patch

from backend import app as app_module
from backend.pc_explorer_3d import (
    DIAGNOSTICOS,
    SKETCHFAB_MODEL_UID,
    _build_parts,
    render_pc_explorer,
    render_pc_svg,
)


class PcExplorerTests(unittest.TestCase):
    def test_svg_renders_selection_and_normalizes_orientation(self):
        svg = render_pc_svg("Placa de vídeo", "205", "90")
        default_svg = render_pc_svg("<script>", "invalid", "invalid")

        self.assertTrue(svg.startswith("<svg "))
        self.assertTrue(svg.endswith("</svg>"))
        self.assertIn('azimute=205.0&amp;elevacao=65.0', svg)
        self.assertIn('component-Placa%20de%20v%C3%ADdeo', svg)
        self.assertNotIn("<script>", default_svg)
        self.assertIn("azimute=0.0", render_pc_svg(azimuth=0))

    def test_page_shows_component_diagnosis_and_selected_state(self):
        page = render_pc_explorer("Placa de vídeo", 18, 18)

        self.assertIn("Guia de diagnóstico", page)
        self.assertIn("COMPONENTE SELECIONADO", page)
        self.assertIn("Falhas comuns", page)
        self.assertIn('aria-current="true"', page)
        self.assertIn("arraste", page.lower())
        untrusted_page = render_pc_explorer("</script><script>alert(1)</script>")
        self.assertNotIn("alert(1)", untrusted_page)
        self.assertIn("Possíveis soluções", page)
        self.assertGreaterEqual(page.count("<li>"), 8)

    def test_each_component_has_multiple_failures_and_solutions(self):
        for diagnosis in DIAGNOSTICOS.values():
            with self.subTest(component=diagnosis):
                self.assertGreaterEqual(len(diagnosis["erros"]), 4)
                self.assertGreaterEqual(len(diagnosis["solucao"]), 4)

    def test_local_model_fallback_renders_case_mesh(self):
        svg = render_pc_svg()
        material_colors = {face["color"] for _, face in _build_parts(18, 18)}

        self.assertIn("#29313B", material_colors)
        self.assertIn("component-Gabinete", svg)

    def test_diagnostic_route_and_education_page_use_current_viewers(self):
        page = render_pc_explorer()
        education_page = (
            Path(__file__).resolve().parents[2]
            / "frontend"
            / "pages"
            / "educacao.html"
        ).read_text(encoding="utf-8")

        self.assertIn(f'init("{SKETCHFAB_MODEL_UID}"', page)
        self.assertIn('id="modelViewer"', page)
        self.assertNotIn("src=\"https://sketchfab.com/models/", page)
        self.assertIn('id="canvas-pc-3d"', education_page)
        self.assertIn('src="../assets/js/educacao-3d.js"', education_page)
        controls = (
            "pc-auto-rotate",
            "pc-explode",
            "pc-hide-case",
            "pc-wireframe",
            "pc-rgb",
        )
        for control in controls:
            with self.subTest(control=control):
                self.assertIn(f'id="{control}"', education_page)

    def test_page_shows_empty_state_without_selection(self):
        page = render_pc_explorer()

        self.assertIn("Selecione uma peça", page)
        self.assertNotIn("COMPONENTE SELECIONADO", page)

    def test_flask_routes_render_the_explorer_for_authorized_users(self):
        client = app_module.app.test_client()
        membro = {"cargo": "Administrador", "permissoes": "[]"}

        with patch.object(app_module, "_carregar_membro_da_sessao", return_value=membro):
            page = client.get("/educacao/pc-explorer?componente=Processador")
            model = client.get("/educacao/pc-explorer/modelo.svg?componente=Processador")

        self.assertEqual(page.status_code, 200)
        self.assertIn(b'id="modelViewer"', page.data)
        self.assertIn(SKETCHFAB_MODEL_UID.encode(), page.data)
        self.assertIn("Processador".encode(), page.data)
        self.assertEqual(model.status_code, 200)
        self.assertEqual(model.mimetype, "image/svg+xml")
        self.assertTrue(model.get_data(as_text=True).endswith("</svg>"))

    def test_diagnosis_api_returns_all_component_options(self):
        client = app_module.app.test_client()
        membro = {"cargo": "Administrador", "permissoes": '["educacao"]'}

        with patch.object(app_module, "_carregar_membro_da_sessao", return_value=membro):
            response = client.get("/api/educacao/diagnosticos")

        self.assertEqual(response.status_code, 200)
        for component, diagnosis in DIAGNOSTICOS.items():
            self.assertIn(component, response.get_json())
            self.assertGreaterEqual(len(response.get_json()[component]["erros"]), 4)
            self.assertGreaterEqual(len(response.get_json()[component]["solucao"]), 4)


if __name__ == "__main__":
    unittest.main()
