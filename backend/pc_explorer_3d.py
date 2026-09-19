import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

# ---------------------------------------------------------
# 1. BASE DE CONHECIMENTO / DIAGNÓSTICOS POR COMPONENTE
# ---------------------------------------------------------
DIAGNOSTICOS = {
    "Gabinete": {
        "erros": "Botão Power com mau contato ou acúmulo de poeira nos filtros de ar.",
        "solucao": "Verifique os cabos do Painel Frontal conectados à placa-mãe e realize a limpeza periódica das saídas de ar."
    },
    "Placa-mãe": {
        "erros": "Curto-circuito, BIOS corrompida ou capacitores estufados.",
        "solucao": "Faça o reset da BIOS (Clear CMOS), verifique os espaçadores do gabinete e teste com outra fonte de alimentação."
    },
    "Processador": {
        "erros": "Superaquecimento (Overheating) ou pinos dobrados.",
        "solucao": "Substitua a pasta térmica, limpe o cooler e certifique-se de que o sistema de refrigeração está firmemente instalado."
    },
    "Módulos de RAM": {
        "erros": "Tela azul (BSOD), apitos de erro na inicialização ou memória não reconhecida.",
        "solucao": "Limpe os contatos dourados com uma borracha escolar macia e teste os módulos em slots diferentes."
    },
    "Placa de vídeo": {
        "erros": "Artefatos visuais na tela, ausência de vídeo ou ventoinhas paradas.",
        "solucao": "Verifique se os cabos de alimentação PCIe estão bem conectados e atualize os drivers de vídeo."
    },
    "Fonte de alimentação": {
        "erros": "Computador desliga sozinho em carga alta ou não liga.",
        "solucao": "Utilize um testador de fonte para verificar as tensões de 12V, 5V e 3.3V antes de substituir a unidade."
    },
    "HD/SSD": {
        "erros": "Lentidão extrema, erros de I/O ou sistema operacional não encontrado.",
        "solucao": "Verifique a saúde do disco com diagnósticos S.M.A.R.T. e troque o cabo Sata ou o slot M.2."
    }
}

# CORES DOS COMPONENTES (HEX para RGBA)
COLORS = {
    "DARK": "#2E3A4E",
    "FRAME": "#3A4860",
    "PCB": "#1E3A5F",
    "ACCENT": "#2563EB",
    "HIGHLIGHT": "#EF4444",  # Vermelho ao selecionar/destacar
    "BODY": "#DCE3EE"
}

# DEFINIÇÃO DOS COMPONENTES (Nome, Posição Center-X,Y,Z e Tamanho W,D,H)
PART_DEFS = [
    {"key": "Gabinete", "pos": (0, 0, 1.25), "size": (2.3, 2.7, 2.5), "color": COLORS["FRAME"]},
    {"key": "Placa-mãe", "pos": (0, -0.6, 1.25), "size": (1.9, 0.07, 1.9), "color": COLORS["PCB"]},
    {"key": "Processador", "pos": (-0.35, -0.5, 1.7), "size": (0.42, 0.2, 0.42), "color": COLORS["ACCENT"]},
    {"key": "Módulos de RAM", "pos": (0.55, -0.4, 1.5), "size": (0.24, 0.3, 0.95), "color": COLORS["PCB"]},
    {"key": "Placa de vídeo", "pos": (0.35, 0.1, 0.72), "size": (1.35, 0.85, 0.45), "color": COLORS["DARK"]},
    {"key": "Fonte de alimentação", "pos": (-0.62, 0.4, 0.45), "size": (0.75, 1.0, 0.65), "color": COLORS["DARK"]},
    {"key": "HD/SSD", "pos": (0.68, 0.3, 0.15), "size": (0.6, 0.95, 0.14), "color": COLORS["BODY"]}
]

# ---------------------------------------------------------
# 2. FUNÇÃO AUXILIAR PARA DESENHAR BLOCOS 3D NO MATPLOTLIB
# ---------------------------------------------------------
def create_cube(pos, size):
    """Cria as vértices e faces de um paralelepípedo em 3D."""
    x, y, z = pos
    dx, dy, dz = size
    
    # Limites
    x0, x1 = x - dx/2, x + dx/2
    y0, y1 = y - dy/2, y + dy/2
    z0, z1 = z - dz/2, z + dz/2

    vertices = np.array([
        [x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
        [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]
    ])

    faces = [
        [vertices[0], vertices[1], vertices[2], vertices[3]], # Baixo
        [vertices[4], vertices[5], vertices[6], vertices[7]], # Cima
        [vertices[0], vertices[1], vertices[5], vertices[4]], # Frente
        [vertices[2], vertices[3], vertices[7], vertices[6]], # Trás
        [vertices[1], vertices[2], vertices[6], vertices[5]], # Direita
        [vertices[4], vertices[7], vertices[3], vertices[0]]  # Esquerda
    ]
    return faces

# ---------------------------------------------------------
# 3. INTERFACE GRÁFICA TKINTER + MATPLOTLIB
# ---------------------------------------------------------
class PcExplorerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("HelpTi - Educação Técnica PC 3D (Python)")
        self.root.geometry("1000x650")
        self.root.configure(bg="#F9FAFB")

        self.selected_part = None
        self.poly_collections = {}

        self.setup_ui()
        self.plot_pc_3d()

    def setup_ui(self):
        # Título Superior
        title_frame = tk.Frame(self.root, bg="#F9FAFB", pady=10)
        title_frame.pack(fill="x", px=20)
        
        lbl_title = tk.Label(title_frame, text="Educação Técnica", font=("Helvetica", 18, "bold"), bg="#F9FAFB", fg="#1E1B18")
        lbl_title.pack(anchor="w")
        
        lbl_sub = tk.Label(title_frame, text="Explore um PC em 3D: clique nos componentes ou botões abaixo para ver falhas comuns.", font=("Helvetica", 10), bg="#F9FAFB", fg="#6B7280")
        lbl_sub.pack(anchor="w")

        # Container Principal (Dividido em 2 colunas)
        main_container = tk.Frame(self.root, bg="#F9FAFB")
        main_container.pack(fill="both", expand=True, px=20, py=10)

        # ---- COLUNA ESQUERDA: CENA 3D (MATPLOTLIB) ----
        left_card = tk.Frame(main_container, bg="#FFFFFF", highlightbackground="#E2DCD0", highlightthickness=1)
        left_card.pack(side="left", fill="both", expand=True, padx=(0, 10))

        lbl_torre = tk.Label(left_card, text="Torre Interativa 3D", font=("Helvetica", 12, "bold"), bg="#FFFFFF", fg="#1E1B18", pady=10)
        lbl_torre.pack()

        # Canvas Matplotlib
        self.fig = plt.Figure(figsize=(5, 5), dpi=100)
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.canvas = FigureCanvasTkAgg(self.fig, master=left_card)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # Botões de Seleção Rápida dos Componentes
        btn_frame = tk.Frame(left_card, bg="#FFFFFF", pady=5)
        btn_frame.pack(fill="x")

        for p in PART_DEFS:
            key = p["key"]
            b = tk.Button(btn_frame, text=key, font=("Helvetica", 8), bg="#F3F4F6", fg="#1F2937",
                          command=lambda k=key: self.select_component(k))
            b.pack(side="left", expand=True, fill="x", padx=2, pady=2)

        # ---- COLUNA DIREITA: PAINEL DE DIAGNÓSTICO ----
        right_card = tk.Frame(main_container, bg="#FFFFFF", width=320, highlightbackground="#E2DCD0", highlightthickness=1)
        right_card.pack(side="right", fill="both", padx=(10, 0))
        right_card.pack_propagate(False)

        lbl_diag_title = tk.Label(right_card, text="Diagnóstico do Componente", font=("Helvetica", 12, "bold"), bg="#FFFFFF", fg="#1E1B18", pady=15)
        lbl_diag_title.pack(anchor="w", px=15)

        self.diag_content = tk.Frame(right_card, bg="#FFFFFF")
        self.diag_content.pack(fill="both", expand=True, px=15)

        # Estado Inicial
        self.lbl_empty = tk.Label(self.diag_content, text="➤\n\nSelecione um componente na torre 3D\npara ver as falhas comuns e soluções.",
                                  font=("Helvetica", 10), fg="#9CA3AF", bg="#FFFFFF", justify="center")
        self.lbl_empty.pack(expand=True)

    def plot_pc_3d(self):
        """Renderiza os componentes 3D no Matplotlib."""
        self.ax.clear()
        
        # Configurações estéticas da cena 3D
        self.ax.set_facecolor('#FFFFFF')
        self.ax.grid(False)
        self.ax.axis('off') # Ocultar eixos cartesianos

        for part in PART_DEFS:
            key = part["key"]
            pos = part["pos"]
            size = part["size"]
            color = COLORS["HIGHLIGHT"] if key == self.selected_part else part["color"]
            alpha = 0.3 if key == "Gabinete" and key != self.selected_part else 0.85

            faces = create_cube(pos, size)
            poly = Poly3DCollection(faces, facecolors=color, linewidths=0.5, edgecolors='#1E1B18', alpha=alpha)
            
            self.ax.add_collection3d(poly)
            self.poly_collections[key] = poly

            # Texto indicativo do componente
            self.ax.text(pos[0], pos[1], pos[2] + size[2]/2 + 0.1, key, color='#1E1B18',
                         fontsize=8, fontweight='bold', ha='center')

        # Ajuste de Limites do Espaço 3D
        self.ax.set_xlim(-1.5, 1.5)
        self.ax.set_ylim(-1.5, 1.5)
        self.ax.set_zlim(0, 3)
        self.ax.view_init(elev=20, azim=45) # Ângulo da câmera isometrica

        self.canvas.draw()

    def select_component(self, key):
        """Atualiza a peça destacada em vermelho no 3D e renderiza o diagnóstico."""
        self.selected_part = key
        self.plot_pc_3d()

        # Limpar painel de diagnósticos
        for widget in self.diag_content.winfo_children():
            widget.destroy()

        data = DIAGNOSTICOS.get(key, {})

        # Título da Peça
        lbl_part = tk.Label(self.diag_content, text=key, font=("Helvetica", 14, "bold"), bg="#FFFFFF", fg="#1E1B18")
        lbl_part.pack(anchor="w", pady=(10, 5))

        # Falhas Comuns
        lbl_err_title = tk.Label(self.diag_content, text="Falhas Comuns:", font=("Helvetica", 10, "bold"), bg="#FFFFFF", fg="#EF4444")
        lbl_err_title.pack(anchor="w", pady=(10, 2))

        lbl_err_desc = tk.Label(self.diag_content, text=data.get("erros", ""), font=("Helvetica", 9), bg="#FFFFFF", fg="#4B5563", wraplength=280, justify="left")
        lbl_err_desc.pack(anchor="w")

        # Solução Recomendada
        lbl_sol_title = tk.Label(self.diag_content, text="Solução Recomendada:", font=("Helvetica", 10, "bold"), bg="#FFFFFF", fg="#2563EB")
        lbl_sol_title.pack(anchor="w", pady=(15, 2))

        lbl_sol_desc = tk.Label(self.diag_content, text=data.get("solucao", ""), font=("Helvetica", 9), bg="#FFFFFF", fg="#4B5563", wraplength=280, justify="left")
        lbl_sol_desc.pack(anchor="w")


# ---------------------------------------------------------
# EXECUTAR APLICAÇÃO
# ---------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = PcExplorerApp(root)
    root.mainloop()