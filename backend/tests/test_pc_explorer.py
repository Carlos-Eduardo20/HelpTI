import unittest
from unittest.mock import patch

from backend import app as app_module
from backend.pc_explorer_3d import render_pc_explorer, render_pc_svg


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
        self.assertIn(b"<svg ", page.data)
        self.assertIn("Processador".encode(), page.data)
        self.assertEqual(model.status_code, 200)
        self.assertEqual(model.mimetype, "image/svg+xml")
        self.assertTrue(model.get_data(as_text=True).endswith("</svg>"))


if __name__ == "__main__":
    unittest.main()
