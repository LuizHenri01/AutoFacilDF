# =============================================================================
# auto_facildf.py — AutoFacilDF
# Sistema de Administração de Revenda de Veículos
#
# Dependências: pip install pillow
# Executar:     python auto_facildf.py
#
# Login padrão (após rodar populate_db.py):
#   Usuário: admin  |  Senha: 123456
# =============================================================================

import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from auto_facil_db import (
    init_db,
    db_verificar_login, db_inserir_usuario, db_buscar_usuarios,
    db_atualizar_role_usuario, db_excluir_usuario,
    db_inserir_cliente, db_buscar_clientes, db_excluir_cliente,
    db_inserir_funcionario, db_buscar_funcionarios, db_excluir_funcionario,
    db_inserir_veiculo, db_buscar_frota, db_excluir_veiculo,
    db_atualizar_status_veiculo,
    db_inserir_agendamento, db_agendamentos_hoje, db_todos_agendamentos,
    db_inserir_vistoria, db_buscar_vistorias,
    db_inserir_lancamento, db_resumo_financeiro,
    db_inserir_financiamento, db_resumo_financiamentos, db_buscar_financiamentos,
    db_kpis,
)

# ── Caminho base do projeto ───────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent

# ── Constantes de negócio ─────────────────────────────────────────────────────
CAPACIDADE_PATIO        = 60
TAXA_FINANCIAMENTO_PADRAO = 1.69
PRAZOS_FINANCIAMENTO    = [12, 24, 36, 48, 60]

# Imagem fallback quando a imagem do veículo não é encontrada
IMG_FALLBACK = "imagens/BMW 210i.png"

# ── Paleta de cores (tema dark luxury) ───────────────────────────────────────
BG_DARK      = "#0D0D0D"
BG_CARD      = "#161616"
BG_PANEL     = "#1C1C1C"
ACCENT       = "#C8A96E"
ACCENT_HOVER = "#E0C080"
TEXT_PRIMARY = "#F0EDE8"
TEXT_MUTED   = "#7A7570"
SUCCESS      = "#4CAF50"
DANGER       = "#E57373"

# ── Estado global da sessão ───────────────────────────────────────────────────
janela          = None
frame_principal = None
usuario_logado  = None   # Nome do usuário autenticado
role_logado     = None   # 'admin' ou 'user'


# =============================================================================
# Utilitários
# =============================================================================

def data_hora_atual():
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def converter_moeda(valor) -> float:
    """Converte string 'R$ 1.500,00' para float 1500.0."""
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor or "").strip()
    texto = texto.replace("R$", "").replace("r$", "").replace(" ", "")
    texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto) if texto else 0.0
    except ValueError:
        return 0.0


def formatar_moeda(valor) -> str:
    """Formata float como 'R$ 1.500,00'."""
    return f"R$ {float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def calcular_financiamento(valor_veiculo, entrada, parcelas, taxa_mensal):
    """Calcula valor da parcela e total financiado usando a fórmula Price."""
    saldo = max(valor_veiculo - entrada, 0)
    taxa  = taxa_mensal / 100
    if parcelas <= 0:
        return 0.0, saldo
    if taxa == 0:
        parcela = saldo / parcelas
    else:
        parcela = saldo * (taxa * (1 + taxa) ** parcelas) / ((1 + taxa) ** parcelas - 1)
    return parcela, parcela * parcelas


def sugerir_imagem_veiculo(nome: str) -> str:
    """Retorna o caminho de imagem mais adequado ao nome do veículo."""
    texto = (nome or "").lower()
    if "toyota" in texto or "corolla" in texto:
        return "imagens/toyata.png"
    if "honda" in texto or "civic" in texto or "cr-v" in texto or "crv" in texto or "hr-v" in texto:
        return "imagens/honda CR-V.png"
    if "bmw" in texto:
        return "imagens/BMW 210i.png"
    if "chevrolet" in texto or "onix" in texto:
        return "imagens/Chevrolet Onix.jpg"
    if "ford" in texto or "territory" in texto or "ka" in texto:
        return "imagens/ford-ka.jpg"
    if "hyundai" in texto or "hb20" in texto:
        return "imagens/Hyundai-HB20.png"
    if "nissan" in texto or "kicks" in texto or "versa" in texto:
        return "imagens/Nissan-Versa.jpg"
    if "renault" in texto or "kwid" in texto or "duster" in texto:
        return "imagens/Renault-Kwid.jpg"
    if "volkswagen" in texto or "t-cross" in texto or "golf" in texto:
        return "imagens/Volkswagen-Golf.jpg"
    return IMG_FALLBACK


def carregar_imagem_segura(caminho, largura, altura):
    """
    Carrega e redimensiona uma imagem de forma segura.
    Retorna PhotoImage ou None se falhar.
    """
    try:
        caminho_img = Path(caminho or IMG_FALLBACK)
        if not caminho_img.is_absolute():
            caminho_img = BASE_DIR / caminho_img
        if not caminho_img.exists():
            caminho_img = BASE_DIR / IMG_FALLBACK
        with Image.open(caminho_img) as img:
            img_redim = img.resize((largura, altura), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(img_redim)
    except (FileNotFoundError, OSError):
        return None


def mostrar_relatorio(titulo: str):
    """Placeholder para relatórios ainda não implementados."""
    messagebox.showinfo("Relatório", f"Relatório de {titulo} preparado para integração com dados reais.")


# =============================================================================
# Inicialização da janela principal
# =============================================================================

def configurar_janela():
    global janela, frame_principal
    janela = tk.Tk()
    janela.title("AutoFacilDF")
    janela.geometry("1200x750+150+20")
    janela.configure(bg=BG_DARK)
    janela.resizable(False, False)
    frame_principal = tk.Frame(janela, bg=BG_DARK)
    frame_principal.pack(fill="both", expand=True)


def limpar_tela():
    """Destroi todos os widgets do frame principal."""
    for widget in frame_principal.winfo_children():
        widget.destroy()


# =============================================================================
# Navbar padrão (reutilizável)
# =============================================================================

def criar_navbar(titulo_texto, cmd_voltar=None, texto_voltar="← Voltar"):
    """
    Cria a navbar superior padrão com linha dourada e botão de voltar.
    Retorna o frame da navbar para adicionar widgets extras se necessário.
    """
    navbar = tk.Frame(frame_principal, bg=BG_CARD, height=70)
    navbar.pack(side="top", fill="x")
    navbar.pack_propagate(False)
    tk.Frame(navbar, bg=ACCENT, height=3).pack(side="top", fill="x")

    content = tk.Frame(navbar, bg=BG_CARD)
    content.pack(fill="both", expand=True, padx=20, pady=15)

    tk.Label(content, text=titulo_texto, bg=BG_CARD, fg=ACCENT, font=("Times", 18, "bold")).pack(side="left")

    if cmd_voltar:
        btn = tk.Label(content, text=texto_voltar, bg=BG_CARD, fg=TEXT_PRIMARY,
        font=("Arial", 11, "bold"), padx=15, pady=5, cursor="hand2")
        btn.pack(side="right")
        btn.bind("<Button-1>", lambda e: cmd_voltar())
        btn.bind("<Enter>", lambda e: btn.config(fg=ACCENT_HOVER))
        btn.bind("<Leave>", lambda e: btn.config(fg=TEXT_PRIMARY))

    return navbar


# =============================================================================
# Tela de Login
# =============================================================================

def tela_login():
    limpar_tela()

    def fazer_login(event=None):
        global usuario_logado, role_logado
        usuario = entry_usuario.get().strip()
        senha   = entry_senha.get().strip()
        resultado = db_verificar_login(usuario, senha)
        if resultado:
            usuario_logado = resultado[1]
            role_logado    = resultado[2]
            print("ROLE:", role_logado)
            print("TIPO:", type(role_logado))
            messagebox.showinfo("Sucesso", f"Bem-vindo, {usuario_logado}!")
            tela_principal()
        else:
            messagebox.showerror("Erro", "Usuário ou senha inválidos.")

    # Painel esquerdo decorativo
    sidebar = tk.Frame(frame_principal, bg=BG_CARD, width=520)
    sidebar.pack(side="left", fill="y")
    barra   = tk.Frame(frame_principal, bg=BG_DARK)
    barra.pack(side="right", fill="both", expand=True)

    tk.Label(sidebar, text="AF-DF", bg=BG_CARD, fg=ACCENT_HOVER,  font=("Times", 33, "bold")).place(relx=0.5, rely=0.36, anchor="center")
    tk.Label(sidebar, text="AutoFacil-DF", bg=BG_CARD, fg=TEXT_PRIMARY,  font=("Times", 28, "bold")).place(relx=0.5, rely=0.49, anchor="center")
    tk.Label(sidebar, text="Sistema de Venda de Veículos", bg=BG_CARD, fg=TEXT_MUTED,    font=("Times", 12)).place(relx=0.5, rely=0.55, anchor="center")
    tk.Label(sidebar, text="Veículos excepcionais para\n pessoas extraordinárias",
    bg=BG_CARD, fg=TEXT_MUTED,    font=("Times", 12)).place(relx=0.5, rely=0.70, anchor="center")

    tk.Label(barra, text="Bem-vindo de volta!",               bg=BG_DARK, fg=TEXT_PRIMARY,  font=("Times", 20, "bold")).place(relx=0.415, rely=0.26, anchor="center")
    tk.Label(barra, text="Entre na sua conta para continuar", bg=BG_DARK, fg=TEXT_MUTED,    font=("Times", 12)).place(relx=0.39,  rely=0.30, anchor="center")

    tk.Label(barra, text="Usuário", bg=BG_DARK, fg=TEXT_MUTED, font=("Times", 12)).place(relx=0.24, rely=0.40, anchor="w")
    entry_usuario = tk.Entry(barra, width=51, font=("Times", 11), bg=BG_PANEL, fg=TEXT_PRIMARY, relief="flat")
    entry_usuario.place(relx=0.24, rely=0.45, anchor="w", height=38)
    entry_usuario.bind("<Return>", fazer_login)

    tk.Label(barra, text="Senha", bg=BG_DARK, fg=TEXT_MUTED, font=("Times", 12)).place(relx=0.24, rely=0.50, anchor="w")
    entry_senha = tk.Entry(barra, width=51, font=("Times", 11), bg=BG_PANEL, fg=TEXT_PRIMARY, relief="flat", show="*")
    entry_senha.place(relx=0.24, rely=0.55, anchor="w", height=38)
    entry_senha.bind("<Return>", fazer_login)

    tk.Button(barra, text="Entrar", width=39, height=2, bg=ACCENT, fg=TEXT_PRIMARY,
    font=("Times", 11, "bold"), relief="flat", cursor="hand2",
    command=fazer_login).place(relx=0.24, rely=0.65, anchor="w")

    tk.Label(barra, text="─────────────── ou ───────────────",
    bg=BG_DARK, fg=TEXT_MUTED, font=("Times", 12)).place(relx=0.5, rely=0.71, anchor="center")

    tk.Button(barra, text="Criar nova conta", width=39, height=2, bg=BG_PANEL, fg=TEXT_MUTED,
    font=("Times", 11, "bold"), relief="flat", cursor="hand2",
    command=tela_registro).place(relx=0.24, rely=0.765, anchor="w")


# =============================================================================
# Tela de Registro de novo usuário
# =============================================================================

def tela_registro():
    limpar_tela()

    def registrar_usuario():
        nome      = entry_nome.get()
        usuario   = entry_usuario.get()
        email     = entry_email.get()
        telefone  = entry_telefone.get()
        senha     = entry_senha.get()
        confirmar = entry_confirmar.get()

        if not nome or not usuario or not senha:
            messagebox.showerror("Erro", "Preencha os campos obrigatórios.")
            return
        if senha != confirmar:
            messagebox.showerror("Erro", "As senhas não coincidem.")
            return

        sucesso = db_inserir_usuario(nome, usuario, email, telefone, senha)
        if sucesso:
            messagebox.showinfo("Sucesso", "Conta criada com sucesso!")
            tela_login()
        else:
            messagebox.showerror("Erro", "Nome de usuário já existe.")

    bg_frame = tk.Frame(frame_principal, bg=BG_DARK)
    bg_frame.pack(fill="both", expand=True)

    # Container central com borda dourada
    container = tk.Frame(bg_frame, bg=BG_CARD, height=575, width=600,
    highlightthickness=2, highlightbackground=ACCENT)
    container.place(relx=0.5, rely=0.5, anchor="center")

    # Cantos decorativos
    for x, y in [(290,60),(910,60),(290,690),(910,690)]:
        tk.Label(bg_frame, text="◆", fg=ACCENT, bg=BG_DARK, font=("Times", 16)).place(x=x, y=y)

    tk.Label(container, text="Criar Conta", bg=BG_CARD, fg=TEXT_PRIMARY,
    font=("Times", 20, "bold")).place(relx=0.5, rely=0.08, anchor="center")
    tk.Button(container, text="← Voltar", bg=BG_PANEL, fg=TEXT_PRIMARY,
    font=("Times", 10, "bold"), relief="flat", cursor="hand2",
    command=tela_login).place(x=20, y=20)
    tk.Frame(container, bg=ACCENT, height=1).place(relx=0.1, rely=0.13, width=480)

    def campo(texto, rely, senha=False):
        tk.Label(container, text=texto, bg=BG_CARD, fg=TEXT_MUTED,
        font=("Times", 12)).place(relx=0.1, rely=rely, anchor="w")
        e = tk.Entry(container, width=66, font=("Times", 11),
        bg=BG_PANEL, fg=TEXT_PRIMARY, relief="flat")
        e.place(relx=0.1, rely=rely + 0.06, anchor="w", height=38)
        if senha:
            e.config(show="*")
        return e

    entry_nome      = campo("Nome Completo",   0.17)
    entry_usuario   = campo("Usuário",          0.31)
    entry_email     = campo("Email",            0.45)
    entry_telefone  = campo("Telefone",         0.59)
    entry_senha     = campo("Senha",            0.73, senha=True)
    entry_confirmar = campo("Confirmar Senha",  0.87, senha=True)

    tk.Button(bg_frame, text="Criar Conta", width=51, height=2, bg=ACCENT, fg=TEXT_PRIMARY,
    font=("Times", 11, "bold"), relief="flat", cursor="hand2",
    command=registrar_usuario).place(relx=0.5, rely=0.9, anchor="center")


# =============================================================================
# Tela Home / Principal
# =============================================================================

def tela_principal():
    limpar_tela()

    # ── Navbar com links de navegação ─────────────────────────────────────────
    navbar = tk.Frame(frame_principal, bg=BG_CARD, height=80)
    navbar.pack(side="top", fill="x")
    navbar.pack_propagate(False)
    tk.Frame(navbar, bg=ACCENT, height=3).pack(side="top", fill="x")

    nav_content = tk.Frame(navbar, bg=BG_CARD)
    nav_content.pack(fill="both", expand=True, padx=20, pady=15)

    tk.Label(nav_content, text="   AF-DF", bg=BG_CARD, fg=ACCENT,
    font=("Times", 18, "bold")).pack(side="left", padx=10)
    tk.Frame(nav_content, bg=BG_CARD).pack(side="left", expand=True)

    def nav_link(parent, texto, comando):
        """Cria um link de navegação com hover."""
        lbl = tk.Label(parent, text=texto, bg=BG_CARD, fg=TEXT_PRIMARY,
        font=("Arial", 11, "bold"), padx=15, pady=5, cursor="hand2")
        lbl.pack(side="left", padx=5)
        lbl.bind("<Enter>",    lambda e: lbl.config(fg=ACCENT_HOVER))
        lbl.bind("<Leave>",    lambda e: lbl.config(fg=TEXT_PRIMARY))
        lbl.bind("<Button-1>", lambda e: comando())

    nav_link(nav_content, " Pesquisa",     tela_pesquisa)
    nav_link(nav_content, " Agendamento",  tela_agendamento)
    nav_link(nav_content, " Dashboard",   tela_dashboard)
    nav_link(nav_content, " Cadastro",    tela_cadastro)
    # Link ADM só aparece para admins logados
    if role_logado == "admin":
        nav_link(nav_content, " ADM", tela_adm)

    tk.Frame(navbar, bg=ACCENT, height=1).pack(side="bottom", fill="x")

    # ── Área de conteúdo com scroll ──────────────────────────────────────────
    container    = tk.Frame(frame_principal, bg=BG_DARK)
    container.pack(fill="both", expand=True, padx=20, pady=20)
    canvas       = tk.Canvas(container, bg=BG_DARK, highlightthickness=0)
    scrollbar    = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
    scroll_frame = tk.Frame(canvas, bg=BG_DARK)

    scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    main = scroll_frame

    # ── Banner principal ──────────────────────────────────────────────────────
    banner = tk.Frame(main, bg=BG_CARD, height=300)
    banner.pack(fill="x", pady=(0, 30))
    banner.pack_propagate(False)
    tk.Frame(banner, bg=ACCENT, width=4).pack(side="left", fill="y")

    bc = tk.Frame(banner, bg=BG_CARD)
    bc.pack(side="left", fill="both", expand=True, padx=30, pady=40)
    tk.Label(bc, text="Encontre seu Veículo Ideal",        bg=BG_CARD, fg=TEXT_PRIMARY, font=("Times", 36, "bold")).pack(anchor="w")
    tk.Label(bc, text="Explore nossa seleção de veículos excepcionais com as melhores condições do mercado",
    bg=BG_CARD, fg=TEXT_MUTED, font=("Arial", 13), wraplength=500, justify="left").pack(anchor="w", pady=(10, 20))

    btn_desc = tk.Button(bc, text="➢ Descobrir Veículos", bg=ACCENT, fg=BG_DARK,
    font=("Arial", 12, "bold"), padx=20, pady=10, relief="flat",
    cursor="hand2", command=tela_automoveis)
    btn_desc.pack(anchor="w", pady=20)
    btn_desc.bind("<Enter>", lambda e: btn_desc.config(bg=ACCENT_HOVER))
    btn_desc.bind("<Leave>", lambda e: btn_desc.config(bg=ACCENT))

    # ── Seção de destaques (carrega os 3 primeiros veículos do banco) ─────────
    tk.Label(main, text="Veículos em Destaque", bg=BG_DARK, fg=TEXT_PRIMARY,
    font=("Times", 22, "bold")).pack(anchor="w", pady=(20, 15))

    cards_frame = tk.Frame(main, bg=BG_DARK)
    cards_frame.pack(fill="x", pady=(0, 30))

    # Busca os 3 veículos mais recentes para destaque
    destaques_db = db_buscar_frota()[:3]
    for vd in destaques_db:
        _, nome, ano, km, preco, cor, cambio, flex, imagem, placa = vd
        # Se não houver imagem no banco, sugere uma baseada no nome do veículo
        img_final = imagem if imagem else sugerir_imagem_veiculo(nome or "")
        dados = {
            "nome": nome or "Veículo", "ano": ano or "---",
            "preco": preco, "km": km or "0", "cor": cor or "---",
            "cambio": cambio or "---", "flex": flex or "---",
            "imagem": img_final, "placa": placa or "---",
        }

        card = tk.Frame(cards_frame, bg=BG_CARD, width=250, height=290)
        card.pack(side="left", padx=10, pady=10)
        card.pack_propagate(False)
        tk.Frame(card, bg=ACCENT, height=3).pack(fill="x")

        img = carregar_imagem_segura(dados["imagem"], 200, 120)
        if img:
            lbl_img = tk.Label(card, image=img, bg=BG_PANEL)
            lbl_img.image = img
            lbl_img.pack(fill="both", expand=True, padx=10, pady=10)
        else:
            tk.Label(card, text="🚗", bg=BG_PANEL, fg=TEXT_MUTED,
        font=("Arial", 32), height=3).pack(fill="both", expand=True, padx=10, pady=10)

        info = tk.Frame(card, bg=BG_CARD)
        info.pack(fill="x", padx=10, pady=(0, 10))
        tk.Label(info, text=nome, bg=BG_CARD, fg=TEXT_PRIMARY, font=("Arial", 12, "bold")).pack(anchor="w")
        tk.Label(info, text=f"Ano: {ano}", bg=BG_CARD, fg=TEXT_MUTED, font=("Arial", 10)).pack(anchor="w")
        preco_fmt = formatar_moeda(preco) if preco and preco != "Consulte-nos" else "Consulte-nos"
        tk.Label(info, text=preco_fmt, bg=BG_CARD, fg=ACCENT, font=("Arial", 12, "bold")).pack(anchor="w", pady=(5,0))
        tk.Button(info, text="VER DETALHES", bg=BG_DARK, fg=TEXT_PRIMARY,
        font=("Arial", 8, "bold"), relief="flat", cursor="hand2",
        command=lambda d=dados: tela_detalhes_veiculo(d)).pack(fill="x", pady=(8, 0))

        tk.Frame(card, bg=ACCENT, height=2).pack(side="bottom", fill="x")

    # ── Footer informativo ────────────────────────────────────────────────────
    footer = tk.Frame(main, bg=BG_CARD)
    footer.pack(fill="x", pady=20)
    tk.Frame(footer, bg=ACCENT, height=2).pack(fill="x")

    fc = tk.Frame(footer, bg=BG_CARD)
    fc.pack(fill="both", expand=True, padx=20, pady=15)
    tk.Label(fc, text="Por que escolher AutoFacil-DF?", bg=BG_CARD, fg=TEXT_PRIMARY,
            font=("Times", 16, "bold")).pack(anchor="w")
    for b in ["✓ Maior seleção de veículos do Distrito Federal",
            "✓ Financiamento com as melhores taxas",
            "✓ Garantia e suporte técnico completo"]:
        tk.Label(fc, text=b, bg=BG_CARD, fg=ACCENT, font=("Arial", 11), padx=10).pack(anchor="w", pady=3)

    canvas.configure(scrollregion=canvas.bbox("all"))


# =============================================================================
# Tela de Estoque / Automóveis
# =============================================================================

def tela_automoveis():
    limpar_tela()

    nav = tk.Frame(frame_principal, bg=BG_CARD, height=70)
    nav.pack(side="top", fill="x")
    tk.Frame(nav, bg=ACCENT, height=3).pack(side="top", fill="x")
    tk.Label(nav, text="  🚗 ESTOQUE AUTO FÁCIL DF", bg=BG_CARD, fg=ACCENT,
             font=("Times", 18, "bold")).pack(side="left", padx=20, pady=20)
    tk.Button(nav, text="Menu Principal", command=tela_principal, bg=BG_PANEL,
              fg=TEXT_PRIMARY, relief="flat", padx=15).pack(side="right", padx=20)

    # Canvas com scroll para os cards
    container = tk.Canvas(frame_principal, bg=BG_DARK, highlightthickness=0)
    scrollbar = tk.Scrollbar(frame_principal, orient="vertical", command=container.yview)
    scroll_f  = tk.Frame(container, bg=BG_DARK)

    scroll_f.bind("<Configure>", lambda e: container.configure(scrollregion=container.bbox("all")))
    container.create_window((0, 0), window=scroll_f, anchor="nw", width=1160)
    container.configure(yscrollcommand=scrollbar.set)
    container.pack(side="left", fill="both", expand=True, padx=5)
    scrollbar.pack(side="right", fill="y")
    container.bind_all("<MouseWheel>", lambda e: container.yview_scroll(int(-1*(e.delta/120)), "units"))

    # Carrega apenas veículos do banco (sem dados hardcoded)
    estoque = []
    for _, nome, ano, km, preco, cor, cambio, flex, imagem, placa in db_buscar_frota():
        # Se não houver imagem no banco, sugere uma baseada no nome do veículo
        img_final = imagem if imagem else sugerir_imagem_veiculo(nome or "")
        estoque.append({
            "nome":   nome or "Veículo sem nome",
            "ano":    ano  or "---",
            "preco":  formatar_moeda(preco) if preco and preco != "Consulte-nos" else "Consulte-nos",
            "km":     km   or "0",
            "cor":    cor  or "---",
            "cambio": cambio or "---",
            "flex":   flex  or "---",
            "imagem": img_final,
            "placa":  placa  or "---",
        })

    if not estoque:
        tk.Label(scroll_f,
                text="Nenhum veículo cadastrado. Use Cadastro > Frota para adicionar veículos.",
                bg=BG_DARK, fg=TEXT_MUTED, font=("Arial", 12, "italic")).pack(pady=40)
        return

    for col in range(3):
        scroll_f.grid_columnconfigure(col, weight=1)

    for i, carro in enumerate(estoque):
        r, c = divmod(i, 3)
        card = tk.Frame(scroll_f, bg=BG_PANEL, padx=25, pady=20,
                        highlightthickness=1, highlightbackground="#333333")
        card.grid(row=r, column=c, padx=15, pady=15, sticky="nsew")

        img_tk = carregar_imagem_segura(carro["imagem"], 280, 160)
        if img_tk:
            lbl_img = tk.Label(card, image=img_tk, bg=BG_PANEL)
            lbl_img.image = img_tk  # Mantém referência para evitar garbage collection
            lbl_img.pack(fill="x", pady=(0, 15))
        else:
            tk.Label(card, text="[ Foto Indisponível ]", bg=BG_CARD, fg=TEXT_MUTED,
                     font=("Arial", 10, "italic"), height=8).pack(fill="x", pady=(0, 15))

        tk.Label(card, text=carro["nome"],  bg=BG_PANEL, fg=TEXT_PRIMARY, font=("Arial", 14, "bold")).pack(anchor="w")
        tk.Label(card, text=f"{carro['ano']} • {carro['km']} km • {carro['cor']}",
                 bg=BG_PANEL, fg=TEXT_MUTED, font=("Arial", 10)).pack(anchor="w", pady=5)
        tk.Label(card, text=carro["preco"], bg=BG_PANEL, fg=ACCENT, font=("Arial", 18, "bold")).pack(anchor="w", pady=10)
        tk.Button(card, text="VER DETALHES", bg=BG_DARK, fg=TEXT_PRIMARY,
                  font=("Arial", 10, "bold"), relief="flat", pady=12, cursor="hand2",
                  command=lambda c=carro: tela_detalhes_veiculo(c)).pack(fill="x", pady=(15, 0))


# =============================================================================
# Tela de Detalhes do Veículo
# =============================================================================

def tela_detalhes_veiculo(carro: dict):
    limpar_tela()

    nome_carro = carro.get("nome", "Veículo")
    placa      = carro.get("placa", "---")
    ano        = carro.get("ano",   "---")
    cor        = carro.get("cor",   "---")

    # ── Navbar ────────────────────────────────────────────────────────────────
    nav = tk.Frame(frame_principal, bg=BG_CARD, height=90)
    nav.pack(side="top", fill="x")
    nav.pack_propagate(False)
    nc = tk.Frame(nav, bg=BG_CARD)
    nc.pack(fill="both", expand=True, padx=24, pady=18)

    tf = tk.Frame(nc, bg=BG_CARD)
    tf.pack(side="left", anchor="w")
    tk.Label(tf, text="DETALHES DO VEÍCULO", bg=BG_CARD, fg=ACCENT, font=("Arial", 11, "bold")).pack(anchor="w")
    tk.Label(tf, text=nome_carro, bg=BG_CARD, fg=TEXT_PRIMARY, font=("Arial", 20, "bold")).pack(anchor="w", pady=(4,0))
    tk.Label(tf, text=f"Placa: {placa} • Ano: {ano} • Cor: {cor}", bg=BG_CARD, fg=TEXT_MUTED, font=("Arial", 10)).pack(anchor="w", pady=(4,0))

    af = tk.Frame(nc, bg=BG_CARD)
    af.pack(side="right", anchor="e")
    tk.Button(af, text="← Voltar", bg=BG_PANEL, fg=TEXT_PRIMARY, relief="flat",
              padx=16, pady=10, cursor="hand2", command=tela_automoveis).pack(side="right", padx=(0,10))

    # ── Canvas com scroll ─────────────────────────────────────────────────────
    canvas_c = tk.Canvas(frame_principal, bg=BG_DARK, highlightthickness=0)
    sb       = tk.Scrollbar(frame_principal, orient="vertical", command=canvas_c.yview)
    canvas_c.configure(yscrollcommand=sb.set)
    canvas_c.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    sf = tk.Frame(canvas_c, bg=BG_DARK)
    canvas_c.create_window((0, 0), window=sf, anchor="nw")
    sf.bind("<Configure>", lambda e: canvas_c.configure(scrollregion=canvas_c.bbox("all")))
    canvas_c.bind_all("<MouseWheel>", lambda e: canvas_c.yview_scroll(int(-1*(e.delta/120)), "units"))

    mc = tk.Frame(sf, bg=BG_DARK, padx=30, pady=20)
    mc.pack(fill="both", expand=True)
    mc.columnconfigure(0, weight=2)
    mc.columnconfigure(1, weight=1)

    # ── COLUNA ESQUERDA: imagem + ficha técnica ───────────────────────────────
    left = tk.Frame(mc, bg=BG_DARK)
    left.grid(row=0, column=0, sticky="nsew", padx=(0, 20))

    img_card = tk.Frame(left, bg=BG_PANEL, padx=20, pady=20,
                         highlightthickness=1, highlightbackground="#333333")
    img_card.pack(fill="both", expand=True)

    # Se não houver imagem no banco, sugere uma baseada no nome do carro
    img_path = carro.get("imagem") or sugerir_imagem_veiculo(nome_carro)
    detalhe_img = carregar_imagem_segura(img_path, 560, 320)
    if detalhe_img:
        lbl = tk.Label(img_card, image=detalhe_img, bg=BG_PANEL)
        lbl.image = detalhe_img
        lbl.pack(fill="x", pady=(0, 18))
    else:
        tk.Label(img_card, text="Imagem não disponível", bg=BG_PANEL, fg=TEXT_MUTED,
                 font=("Arial", 11, "italic"), height=12).pack(fill="x", pady=(0, 18))

    ov = tk.Frame(img_card, bg=BG_PANEL)
    ov.pack(fill="x")
    tk.Label(ov, text=nome_carro,            bg=BG_PANEL, fg=TEXT_PRIMARY, font=("Arial", 18, "bold")).pack(anchor="w")
    tk.Label(ov, text=f"{placa} • {ano} • {cor}", bg=BG_PANEL, fg=TEXT_MUTED, font=("Arial", 10)).pack(anchor="w", pady=(5,12))

    for label, value in [("Status", carro.get("status", "Disponível")),
                          ("Localização", "Estoque Auto Fácil DF"),
                          ("Última atualização", carro.get("criado_em", "Não informado"))]:
        row = tk.Frame(img_card, bg=BG_PANEL)
        row.pack(fill="x", pady=4)
        tk.Label(row, text=label, bg=BG_PANEL, fg=TEXT_MUTED,    font=("Arial", 9)).pack(side="left")
        tk.Label(row, text=value, bg=BG_PANEL, fg=TEXT_PRIMARY,  font=("Arial", 9, "bold")).pack(side="right")

    ficha = tk.Frame(left, bg=BG_PANEL, padx=25, pady=25,
                      highlightthickness=1, highlightbackground="#333333")
    ficha.pack(fill="x", pady=(20, 0))
    tk.Label(ficha, text="Ficha Técnica", bg=BG_PANEL, fg=ACCENT, font=("Arial", 14, "bold")).pack(anchor="w", pady=(0,15))

    for label, valor in [
        ("Modelo",     carro.get("nome",   "---")),
        ("Marca",      carro.get("marca",  "---")),
        ("Placa",      placa),
        ("Ano",        ano),
        ("KM",         carro.get("km",     "---")),
        ("Cor",        cor),
        ("Câmbio",     carro.get("cambio", "---")),
        ("Combustível",carro.get("flex",   "---")),
    ]:
        row = tk.Frame(ficha, bg=BG_PANEL)
        row.pack(fill="x", pady=6)
        tk.Label(row, text=label, bg=BG_PANEL, fg=TEXT_MUTED,   font=("Arial", 10)).pack(side="left")
        tk.Label(row, text=valor, bg=BG_PANEL, fg=TEXT_PRIMARY, font=("Arial", 10, "bold")).pack(side="right")

    # ── COLUNA DIREITA: preço + simulação de financiamento ───────────────────
    right = tk.Frame(mc, bg=BG_DARK)
    right.grid(row=0, column=1, sticky="nsew")

    preco_card = tk.Frame(right, bg=BG_CARD, padx=25, pady=25,
                           highlightthickness=1, highlightbackground="#333333")
    preco_card.pack(fill="x", pady=(0, 20))
    tk.Label(preco_card, text="Preço de Venda", bg=BG_CARD, fg=TEXT_MUTED, font=("Arial", 11)).pack(anchor="w")

    preco_raw = carro.get("preco", "Consulte-nos")
    try:
        valor_num = converter_moeda(preco_raw)
    except Exception:
        valor_num = 0.0
    preco_fmt = formatar_moeda(valor_num) if valor_num > 0 else "Consulte-nos"

    tk.Label(preco_card, text=preco_fmt, bg=BG_CARD, fg=ACCENT, font=("Arial", 28, "bold")).pack(anchor="w", pady=(10,5))
    tk.Label(preco_card, text="Condição especial negociada no balcão.", bg=BG_CARD, fg=TEXT_MUTED,
             font=("Arial", 9), wraplength=280, justify="left").pack(anchor="w", pady=(0,10))
    tk.Button(preco_card, text="SOLICITAR PROPOSTA", bg=ACCENT, fg=BG_DARK,
              font=("Arial", 10, "bold"), relief="flat", padx=12, pady=12, cursor="hand2",
              command=lambda: messagebox.showinfo("Proposta", "Solicitação de proposta registrada.")).pack(fill="x")

    # Destaques do veículo
    dest = tk.Frame(right, bg=BG_PANEL, padx=20, pady=20,
                     highlightthickness=1, highlightbackground="#333333")
    dest.pack(fill="x", pady=(0, 20))
    tk.Label(dest, text="Destaques", bg=BG_PANEL, fg=ACCENT, font=("Arial", 12, "bold")).pack(anchor="w", pady=(0,10))
    for txt in ["Veículo pronto para venda em estoque.",
                "Laudo de vistoria disponível mediante solicitação.",
                "Taxa de financiamento a partir de 1,69% ao mês."]:
        tk.Label(dest, text=f"• {txt}", bg=BG_PANEL, fg=TEXT_PRIMARY, font=("Arial", 10),
                 wraplength=280, justify="left").pack(anchor="w", pady=4)

    # Simulação de financiamento
    fin_f = tk.Frame(right, bg=BG_PANEL, padx=20, pady=20,
                      highlightthickness=1, highlightbackground="#333333")
    fin_f.pack(fill="x")
    tk.Label(fin_f, text="Simulação de Financiamento", bg=BG_PANEL, fg=ACCENT,
             font=("Arial", 12, "bold")).pack(anchor="w", pady=(0,10))

    tk.Label(fin_f, text="Nome do cliente",  bg=BG_PANEL, fg=TEXT_MUTED, font=("Arial", 9)).pack(anchor="w", pady=(0,4))
    entry_cliente = tk.Entry(fin_f, bg=BG_DARK, fg=TEXT_PRIMARY, relief="flat", insertbackground=ACCENT)
    entry_cliente.pack(fill="x", ipady=6, pady=(0,12))

    tk.Label(fin_f, text="Entrada (R$)", bg=BG_PANEL, fg=TEXT_MUTED, font=("Arial", 9)).pack(anchor="w", pady=(0,4))
    entry_entrada = tk.Entry(fin_f, bg=BG_DARK, fg=TEXT_PRIMARY, relief="flat", insertbackground=ACCENT)
    entry_entrada.insert(0, "0")
    entry_entrada.pack(fill="x", ipady=6, pady=(0,12))

    ptf = tk.Frame(fin_f, bg=BG_PANEL)
    ptf.pack(fill="x", pady=(0,12))

    pf = tk.Frame(ptf, bg=BG_PANEL)
    pf.pack(side="left", fill="x", expand=True, padx=(0,8))
    tk.Label(pf, text="Parcelas", bg=BG_PANEL, fg=TEXT_MUTED, font=("Arial", 9)).pack(anchor="w", pady=(0,4))
    prazo_var = tk.StringVar(value="48")
    tk.OptionMenu(pf, prazo_var, *[str(p) for p in PRAZOS_FINANCIAMENTO]).pack(fill="x")

    tf2 = tk.Frame(ptf, bg=BG_PANEL)
    tf2.pack(side="left", fill="x", expand=True)
    tk.Label(tf2, text="Taxa (% ao mês)", bg=BG_PANEL, fg=TEXT_MUTED, font=("Arial", 9)).pack(anchor="w", pady=(0,4))
    taxa_var = tk.StringVar(value=str(TAXA_FINANCIAMENTO_PADRAO).replace(".", ","))
    tk.Entry(tf2, textvariable=taxa_var, bg=BG_DARK, fg=TEXT_PRIMARY, relief="flat",
             insertbackground=ACCENT).pack(fill="x", ipady=6)

    tk.Label(fin_f, text="Preço usado na simulação:", bg=BG_PANEL, fg=TEXT_MUTED, font=("Arial", 9)).pack(anchor="w", pady=(0,6))
    tk.Label(fin_f, text=formatar_moeda(valor_num), bg=BG_PANEL, fg=TEXT_PRIMARY, font=("Arial", 11, "bold")).pack(anchor="w", pady=(0,12))

    resultado_var = tk.StringVar(value="Resultado da simulação aparecerá aqui.")
    tk.Label(fin_f, textvariable=resultado_var, bg=BG_PANEL, fg=TEXT_PRIMARY,
             font=("Arial", 9), wraplength=280, justify="left").pack(anchor="w", pady=(0,12))

    def simular():
        if valor_num <= 0:
            resultado_var.set("Preço inválido. Atualize o cadastro do veículo.")
            return None
        entrada  = converter_moeda(entry_entrada.get())
        parcelas = int(prazo_var.get())
        taxa     = float(taxa_var.get().replace(",", ".") or 0)
        if entrada >= valor_num:
            resultado_var.set("Entrada maior ou igual ao preço. Ajuste o valor.")
            return None
        vp, tot = calcular_financiamento(valor_num, entrada, parcelas, taxa)
        resultado_var.set(f"{parcelas}x de {formatar_moeda(vp)} | Entrada {formatar_moeda(entrada)} | Total {formatar_moeda(tot)}")
        return entrada, parcelas, taxa, vp, tot

    def confirmar_financiamento():
        dados = simular()
        if not dados:
            return
        cliente = entry_cliente.get().strip()
        if not cliente:
            messagebox.showerror("Erro", "Informe o nome do cliente.")
            return
        entrada, parcelas, taxa, vp, tot = dados
        db_inserir_financiamento(nome_carro, cliente, valor_num, entrada, parcelas, taxa, vp, tot)
        messagebox.showinfo("Sucesso", "Financiamento cadastrado com sucesso!")
        tela_detalhes_veiculo(carro)

    tk.Button(fin_f, text="SIMULAR", bg=BG_DARK, fg=TEXT_PRIMARY,
              font=("Arial", 9, "bold"), relief="flat", pady=10, command=simular).pack(fill="x", pady=(0,8))
    tk.Button(fin_f, text="CADASTRAR FINANCIAMENTO", bg=SUCCESS, fg=TEXT_PRIMARY,
              font=("Arial", 10, "bold"), pady=10, relief="flat", cursor="hand2",
              command=confirmar_financiamento).pack(fill="x")


# =============================================================================
# Tela de Cadastro (Cliente / Funcionário / Frota)
# =============================================================================

def tela_cadastro(tipo_cadastro="cliente"):
    limpar_tela()

    navbar = tk.Frame(frame_principal, bg=BG_CARD, height=70)
    navbar.pack(side="top", fill="x")
    navbar.pack_propagate(False)
    tk.Frame(navbar, bg=ACCENT, height=3).pack(side="top", fill="x")
    nc = tk.Frame(navbar, bg=BG_CARD)
    nc.pack(fill="both", expand=True, padx=20, pady=15)
    logo = tk.Label(nc, text="   AF-DF", bg=BG_CARD, fg=ACCENT, font=("Times", 18, "bold"), cursor="hand2")
    logo.pack(side="left", padx=10)
    logo.bind("<Button-1>", lambda e: tela_principal())
    tk.Frame(nc, bg=BG_CARD).pack(side="left", expand=True)
    btn_v = tk.Label(nc, text="← Voltar", bg=BG_CARD, fg=TEXT_PRIMARY, font=("Arial", 11, "bold"),
                      padx=15, pady=5, cursor="hand2")
    btn_v.pack(side="right", padx=5)
    btn_v.bind("<Button-1>",    lambda e: tela_principal())
    btn_v.bind("<Enter>", lambda e: btn_v.config(fg=ACCENT_HOVER))
    btn_v.bind("<Leave>", lambda e: btn_v.config(fg=TEXT_PRIMARY))
    tk.Frame(navbar, bg=ACCENT, height=1).pack(side="bottom", fill="x")

    main = tk.Frame(frame_principal, bg=BG_DARK)
    main.pack(fill="both", expand=True, padx=20, pady=20)

    # Abas de navegação
    abas = tk.Frame(main, bg=BG_DARK)
    abas.pack(fill="x", pady=(0, 20))
    for label, tipo in [("👤 Cliente", "cliente"), ("👨‍💼 Funcionário", "funcionario"), ("🚗 Frota (Veículos)", "frota")]:
        ativo = tipo == tipo_cadastro
        a = tk.Label(abas, text=label,
                     bg=ACCENT if ativo else BG_PANEL,
                     fg=BG_DARK if ativo else TEXT_PRIMARY,
                     font=("Arial", 12, "bold"), padx=20, pady=10, cursor="hand2")
        a.pack(side="left", padx=5)
        a.bind("<Button-1>", lambda e, t=tipo: tela_cadastro(tipo_cadastro=t))

    # ── FORMULÁRIO DE CLIENTE ─────────────────────────────────────────────────
    if tipo_cadastro == "cliente":
        tk.Label(main, text="Cadastro de Cliente", bg=BG_DARK, fg=TEXT_PRIMARY,
                 font=("Times", 28, "bold")).pack(pady=(20, 30))

        form = tk.Frame(main, bg=BG_DARK)
        form.pack(fill="both", expand=True, padx=50, pady=10)
        col_e = tk.Frame(form, bg=BG_DARK)
        col_e.pack(side="left", fill="both", expand=True, padx=10)
        col_d = tk.Frame(form, bg=BG_DARK)
        col_d.pack(side="left", fill="both", expand=True, padx=10)

        def campo(parent, texto):
            tk.Label(parent, text=texto, bg=BG_DARK, fg=TEXT_MUTED, font=("Arial", 10)).pack(anchor="w", pady=(15,3))
            e = tk.Entry(parent, width=35, font=("Arial", 10), bg=BG_PANEL, fg=TEXT_PRIMARY, relief="flat")
            e.pack(anchor="w", pady=(0,15), ipady=6, fill="x")
            return e

        entry_nome     = campo(col_e, "Nome Completo")
        entry_telefone = campo(col_e, "Telefone")
        entry_endereco = campo(col_e, "Endereço")
        entry_email    = campo(col_d, "Email")
        entry_cpf      = campo(col_d, "CPF")
        entry_cidade   = campo(col_d, "Cidade")

        def salvar_cliente():
            nome = entry_nome.get().strip()
            if not nome:
                messagebox.showerror("Erro", "O campo Nome é obrigatório.")
                return
            db_inserir_cliente(nome, entry_telefone.get(), entry_endereco.get(),
                               entry_email.get(), entry_cpf.get(), entry_cidade.get())
            messagebox.showinfo("Sucesso", f"Cliente '{nome}' cadastrado com sucesso!")
            tela_cadastro("cliente")

        btn = tk.Button(main, text="✓ Salvar Cliente", width=40, height=2, bg=SUCCESS,
                         fg=TEXT_PRIMARY, font=("Arial", 12, "bold"), relief="flat",
                         cursor="hand2", command=salvar_cliente)
        btn.pack(pady=20)
        btn.bind("<Enter>", lambda e: btn.config(bg="#45a049"))
        btn.bind("<Leave>", lambda e: btn.config(bg=SUCCESS))

    # ── FORMULÁRIO DE FUNCIONÁRIO ─────────────────────────────────────────────
    elif tipo_cadastro == "funcionario":
        tk.Label(main, text="Cadastro de Funcionário", bg=BG_DARK, fg=TEXT_PRIMARY,
                 font=("Times", 28, "bold")).pack(pady=(20, 30))

        form = tk.Frame(main, bg=BG_DARK)
        form.pack(fill="both", expand=True, padx=50, pady=10)
        col_e = tk.Frame(form, bg=BG_DARK)
        col_e.pack(side="left", fill="both", expand=True, padx=10)
        col_d = tk.Frame(form, bg=BG_DARK)
        col_d.pack(side="left", fill="both", expand=True, padx=10)

        def campo(parent, texto):
            tk.Label(parent, text=texto, bg=BG_DARK, fg=TEXT_MUTED, font=("Arial", 10)).pack(anchor="w", pady=(15,3))
            e = tk.Entry(parent, width=35, font=("Arial", 10), bg=BG_PANEL, fg=TEXT_PRIMARY, relief="flat")
            e.pack(anchor="w", pady=(0,15), ipady=6, fill="x")
            return e

        entry_nome     = campo(col_e, "Nome Completo")
        entry_telefone = campo(col_e, "Telefone")
        entry_cargo    = campo(col_e, "Cargo")
        entry_email    = campo(col_d, "Email")
        entry_cpf      = campo(col_d, "CPF")
        entry_salario  = campo(col_d, "Salário (R$)")

        def salvar_funcionario():
            nome = entry_nome.get().strip()
            if not nome:
                messagebox.showerror("Erro", "O campo Nome é obrigatório.")
                return
            db_inserir_funcionario(nome, entry_telefone.get(), entry_cargo.get(),
                                   entry_email.get(), entry_cpf.get(), entry_salario.get())
            messagebox.showinfo("Sucesso", f"Funcionário '{nome}' cadastrado com sucesso!")
            tela_cadastro("funcionario")

        btn = tk.Button(main, text="✓ Salvar Funcionário", width=40, height=2, bg=SUCCESS,
                         fg=TEXT_PRIMARY, font=("Arial", 12, "bold"), relief="flat",
                         cursor="hand2", command=salvar_funcionario)
        btn.pack(pady=20)
        btn.bind("<Enter>", lambda e: btn.config(bg="#45a049"))
        btn.bind("<Leave>", lambda e: btn.config(bg=SUCCESS))

    # ── FORMULÁRIO DE FROTA ───────────────────────────────────────────────────
    elif tipo_cadastro == "frota":
        tk.Label(main, text="Cadastro de Veículo (Frota)", bg=BG_DARK, fg=TEXT_PRIMARY,
                 font=("Times", 28, "bold")).pack(pady=(20, 30))

        form = tk.Frame(main, bg=BG_DARK)
        form.pack(fill="both", expand=True, padx=50, pady=10)
        col_e = tk.Frame(form, bg=BG_DARK)
        col_e.pack(side="left", fill="both", expand=True, padx=10)
        col_d = tk.Frame(form, bg=BG_DARK)
        col_d.pack(side="left", fill="both", expand=True, padx=10)

        def campo(parent, texto):
            tk.Label(parent, text=texto, bg=BG_DARK, fg=TEXT_MUTED, font=("Arial", 10)).pack(anchor="w", pady=(15,3))
            e = tk.Entry(parent, width=35, font=("Arial", 10), bg=BG_PANEL, fg=TEXT_PRIMARY, relief="flat")
            e.pack(anchor="w", pady=(0,15), ipady=6, fill="x")
            return e

        entry_marca  = campo(col_e, "Marca")
        entry_ano    = campo(col_e, "Ano")
        entry_valor  = campo(col_e, "Valor de Compra (R$)")
        entry_modelo = campo(col_d, "Modelo")
        entry_placa  = campo(col_d, "Placa")
        entry_km     = campo(col_d, "Quilometragem")

        # Linha extras abaixo das colunas
        extras = tk.Frame(main, bg=BG_DARK)
        extras.pack(fill="x", padx=50)
        for frame in [tk.Frame(extras, bg=BG_DARK) for _ in range(4)]:
            frame.pack(side="left", fill="both", expand=True, padx=10)
        col_extras = extras.winfo_children()

        tk.Label(col_extras[0], text="Preço de Venda (R$)", bg=BG_DARK, fg=TEXT_MUTED, font=("Arial", 10)).pack(anchor="w", pady=(0,3))
        entry_preco = tk.Entry(col_extras[0], font=("Arial", 10), bg=BG_PANEL, fg=TEXT_PRIMARY, relief="flat")
        entry_preco.pack(fill="x", ipady=6)

        tk.Label(col_extras[1], text="Cor", bg=BG_DARK, fg=TEXT_MUTED, font=("Arial", 10)).pack(anchor="w", pady=(0,3))
        entry_cor = tk.Entry(col_extras[1], font=("Arial", 10), bg=BG_PANEL, fg=TEXT_PRIMARY, relief="flat")
        entry_cor.pack(fill="x", ipady=6)

        tk.Label(col_extras[2], text="Câmbio", bg=BG_DARK, fg=TEXT_MUTED, font=("Arial", 10)).pack(anchor="w", pady=(0,3))
        var_cambio = tk.StringVar(value="Automático")
        tk.OptionMenu(col_extras[2], var_cambio, "Automático", "Manual", "CVT").pack(fill="x")

        tk.Label(col_extras[3], text="Combustível", bg=BG_DARK, fg=TEXT_MUTED, font=("Arial", 10)).pack(anchor="w", pady=(0,3))
        var_flex = tk.StringVar(value="Flex")
        tk.OptionMenu(col_extras[3], var_flex, "Flex", "Gasolina", "Diesel", "Elétrico", "GNV").pack(fill="x")

        # Seleção de imagem
        img_frame = tk.Frame(main, bg=BG_DARK)
        img_frame.pack(fill="x", padx=60, pady=(12, 0))
        tk.Label(img_frame, text="Imagem do veículo (opcional)", bg=BG_DARK, fg=TEXT_MUTED, font=("Arial", 10)).pack(anchor="w")
        entry_imagem = tk.Entry(img_frame, font=("Arial", 10), bg=BG_PANEL, fg=TEXT_PRIMARY, relief="flat")
        entry_imagem.pack(fill="x", ipady=6)
        lbl_img_sel = tk.Label(img_frame, text="Nenhuma imagem selecionada.", bg=BG_DARK, fg=TEXT_MUTED, font=("Arial", 9, "italic"))
        lbl_img_sel.pack(anchor="w", pady=(5, 0))

        def selecionar_imagem():
            caminho = filedialog.askopenfilename(
                title="Selecione a imagem",
                filetypes=[("Imagens", "*.png *.jpg *.jpeg *.gif"), ("Todos", "*.*")]
            )
            if caminho:
                entry_imagem.delete(0, "end")
                entry_imagem.insert(0, caminho)
                lbl_img_sel.config(text=f"Selecionada: {Path(caminho).name}")

        tk.Button(img_frame, text="Selecionar imagem", bg=BG_PANEL, fg=TEXT_PRIMARY,
                  relief="flat", command=selecionar_imagem, cursor="hand2").pack(anchor="w", pady=(8, 0))

        def salvar_veiculo():
            marca  = entry_marca.get().strip()
            modelo = entry_modelo.get().strip()
            if not marca or not modelo:
                messagebox.showerror("Erro", "Marca e Modelo são obrigatórios.")
                return
            imagem = entry_imagem.get().strip() or sugerir_imagem_veiculo(f"{marca} {modelo}")
            db_inserir_veiculo(marca, modelo, entry_ano.get(), entry_placa.get(),
                               entry_km.get(), entry_valor.get(), entry_preco.get(),
                               entry_cor.get(), var_cambio.get(), var_flex.get(), imagem)
            messagebox.showinfo("Sucesso", f"Veículo '{marca} {modelo}' cadastrado com sucesso!")
            tela_cadastro("frota")

        btn = tk.Button(main, text="✓ Salvar Veículo", width=40, height=2, bg=SUCCESS,
                         fg=TEXT_PRIMARY, font=("Arial", 12, "bold"), relief="flat",
                         cursor="hand2", command=salvar_veiculo)
        btn.pack(pady=20)
        btn.bind("<Enter>", lambda e: btn.config(bg="#45a049"))
        btn.bind("<Leave>", lambda e: btn.config(bg=SUCCESS))


# =============================================================================
# Tela de Pesquisa
# =============================================================================

def tela_pesquisa():
    limpar_tela()
    criar_navbar("   AF-DF | SISTEMA DE BUSCA", cmd_voltar=tela_principal)

    main = tk.Frame(frame_principal, bg=BG_DARK, padx=30, pady=20)
    main.pack(fill="both", expand=True)

    # Barra de busca
    header = tk.Frame(main, bg=BG_DARK)
    header.pack(fill="x", pady=(0, 20))
    tk.Label(header, text="O que você deseja buscar?", bg=BG_DARK, fg=TEXT_PRIMARY,
             font=("Arial", 16, "bold")).pack(anchor="w", pady=(0, 15))

    search_var = tk.StringVar()
    sb_frame   = tk.Frame(header, bg=BG_DARK)
    sb_frame.pack(fill="x", pady=(0, 15))
    ent_search = tk.Entry(sb_frame, textvariable=search_var, bg=BG_PANEL, fg=TEXT_PRIMARY,
                           font=("Arial", 14), relief="flat", insertbackground=ACCENT)
    ent_search.pack(side="left", fill="x", expand=True, ipady=8)
    tk.Button(sb_frame, text="Pesquisar", bg=ACCENT, fg=BG_DARK, font=("Arial", 10, "bold"),
              relief="flat", padx=20, command=lambda: executar_busca()).pack(side="left", padx=(10,0))

    tabs_frame    = tk.Frame(header, bg=BG_DARK)
    tabs_frame.pack(anchor="w")
    display_frame = tk.Frame(main, bg=BG_DARK)
    display_frame.pack(fill="both", expand=True)

    active_tab             = tk.StringVar(value="cliente")
    atualizar_fn_ativo     = [None]

    def linha_resultado(parent, titulo, detalhe):
        linha = tk.Frame(parent, bg=BG_PANEL, padx=15, pady=12,
        highlightbackground="#252525", highlightthickness=1)
        linha.pack(fill="x", pady=5)
        tk.Label(linha, text=titulo, bg=BG_PANEL, fg=TEXT_PRIMARY, font=("Arial", 10, "bold")).pack(anchor="w")
        tk.Label(linha, text=detalhe, bg=BG_PANEL, fg=TEXT_MUTED, font=("Arial", 9),
        wraplength=980, justify="left").pack(anchor="w", pady=(4, 0))

    def atualizar_tabs():
        for btn, nome in [(btn_cli,"cliente"), (btn_frot,"frota"), (btn_func,"funcionario")]:
            btn.configure(bg=ACCENT if active_tab.get()==nome else BG_CARD,
            fg=BG_DARK if active_tab.get()==nome else TEXT_PRIMARY)

    def executar_busca(event=None):
        if atualizar_fn_ativo[0]:
            atualizar_fn_ativo[0]()

    def mostrar_clientes():
        for w in display_frame.winfo_children(): w.destroy()
        active_tab.set("cliente"); atualizar_tabs()
        f = tk.Frame(display_frame, bg=BG_CARD, padx=20, pady=20,
        highlightbackground=ACCENT, highlightthickness=1)
        f.pack(fill="x", pady=10)
        tk.Label(f, text="🔍 PESQUISAR CLIENTE", bg=BG_CARD, fg=ACCENT, font=("Arial", 12, "bold")).pack(anchor="w")
        tk.Label(f, text="Busque por Nome, CPF, Telefone ou Email.", bg=BG_CARD, fg=TEXT_MUTED, font=("Arial", 9)).pack(anchor="w")
        res = tk.Frame(display_frame, bg=BG_DARK)
        res.pack(fill="both", expand=True)

        def atualizar(event=None):
            for w in res.winfo_children(): w.destroy()
            termo    = search_var.get().strip()
            clientes = db_buscar_clientes(termo)
            tk.Label(res, text="Resultado da busca" if termo else "Últimos Clientes",
                     bg=BG_DARK, fg=TEXT_MUTED, font=("Arial", 10, "bold")).pack(anchor="w", pady=10)
            if not clientes:
                linha_resultado(res, "Nenhum cliente encontrado", "Cadastre um novo cliente em Cadastro.")
                return
            for _, nome, tel, email, cpf in clientes:
                linha_resultado(res, nome or "Cliente", f"Tel: {tel or '-'} | Email: {email or '-'} | CPF: {cpf or '-'}")

        atualizar_fn_ativo[0] = atualizar
        atualizar()

    def mostrar_frota():
        for w in display_frame.winfo_children(): w.destroy()
        active_tab.set("frota"); atualizar_tabs()
        f = tk.Frame(display_frame, bg=BG_CARD, padx=20, pady=20,
        highlightbackground=ACCENT, highlightthickness=1)
        f.pack(fill="x", pady=10)
        tk.Label(f, text="🚗 PESQUISAR NO ESTOQUE", bg=BG_CARD, fg=ACCENT, font=("Arial", 12, "bold")).pack(anchor="w")
        tk.Label(f, text="Busque por Nome, Placa, Cor, Marca ou Modelo.", bg=BG_CARD, fg=TEXT_MUTED, font=("Arial", 9)).pack(anchor="w")
        res = tk.Frame(display_frame, bg=BG_DARK)
        res.pack(fill="both", expand=True)

        def atualizar(event=None):
            for w in res.winfo_children(): w.destroy()
            termo    = search_var.get().strip()
            veiculos = db_buscar_frota(termo)
            tk.Label(res, text="Resultado da busca" if termo else "Veículos cadastrados",
            bg=BG_DARK, fg=TEXT_MUTED, font=("Arial", 10, "bold")).pack(anchor="w", pady=10)
            if not veiculos:
                linha_resultado(res, "Nenhum veículo encontrado", "Use Cadastro > Frota para adicionar veículos.")
                return
            for _, nome, ano, km, preco, cor, cambio, flex, _, placa in veiculos:
                preco_fmt = formatar_moeda(converter_moeda(preco)) if preco else "Consulte-nos"
                linha_resultado(res, nome or "Veículo",
                                f"Ano: {ano or '-'} | KM: {km or '-'} | Cor: {cor or '-'} | Câmbio: {cambio or '-'} | Placa: {placa or '-'} | Preço: {preco_fmt}")

        atualizar_fn_ativo[0] = atualizar
        atualizar()

    def mostrar_funcionarios():
        for w in display_frame.winfo_children(): w.destroy()
        active_tab.set("funcionario"); atualizar_tabs()
        f = tk.Frame(display_frame, bg=BG_CARD, padx=20, pady=20,
        highlightbackground=ACCENT, highlightthickness=1)
        f.pack(fill="x", pady=10)
        tk.Label(f, text="💼 GESTÃO DE EQUIPE", bg=BG_CARD, fg=ACCENT, font=("Arial", 12, "bold")).pack(anchor="w")
        tk.Label(f, text="Busque por Nome, Cargo, Telefone ou CPF.", bg=BG_CARD, fg=TEXT_MUTED, font=("Arial", 9)).pack(anchor="w")
        res = tk.Frame(display_frame, bg=BG_DARK)
        res.pack(fill="both", expand=True)

        def atualizar(event=None):
            for w in res.winfo_children(): w.destroy()
            termo = search_var.get().strip()
            funcs = db_buscar_funcionarios(termo)
            tk.Label(res, text="Resultado da busca" if termo else "Funcionários cadastrados",
            bg=BG_DARK, fg=TEXT_MUTED, font=("Arial", 10, "bold")).pack(anchor="w", pady=10)
            if not funcs:
                linha_resultado(res, "Nenhum funcionário encontrado", "Use Cadastro > Funcionário para adicionar.")
                return
            for _, nome, cargo, telefone in funcs:
                linha_resultado(res, nome or "Funcionário", f"Cargo: {cargo or '-'} | Tel: {telefone or '-'}")

        atualizar_fn_ativo[0] = atualizar
        atualizar()

    btn_cli  = tk.Button(tabs_frame, text=" Clientes",     bg=BG_CARD, fg=TEXT_PRIMARY, relief="flat",
    padx=20, pady=10, font=("Arial", 10, "bold"), cursor="hand2", command=mostrar_clientes)
    btn_frot = tk.Button(tabs_frame, text=" Frota",        bg=BG_CARD, fg=TEXT_PRIMARY, relief="flat",
    padx=20, pady=10, font=("Arial", 10, "bold"), cursor="hand2", command=mostrar_frota)
    btn_func = tk.Button(tabs_frame, text=" Funcionários", bg=BG_CARD, fg=TEXT_PRIMARY, relief="flat",
    padx=20, pady=10, font=("Arial", 10, "bold"), cursor="hand2", command=mostrar_funcionarios)
    btn_cli.pack(side="left", padx=2)
    btn_frot.pack(side="left", padx=2)
    btn_func.pack(side="left", padx=2)

    ent_search.bind("<Return>", executar_busca)
    mostrar_clientes()


# =============================================================================
# Tela de Agendamento
# =============================================================================

def tela_agendamento():
    limpar_tela()
    criar_navbar("   AF-DF | AGENDAMENTOS", cmd_voltar=tela_principal)

    main = tk.Frame(frame_principal, bg=BG_DARK, padx=30, pady=30)
    main.pack(fill="both", expand=True)
    main.columnconfigure(0, weight=1)
    main.columnconfigure(1, weight=1)

    # ── Coluna esquerda: formulário ───────────────────────────────────────────
    left = tk.Frame(main, bg=BG_DARK)
    left.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
    tk.Label(left, text="Novo Agendamento", bg=BG_DARK, fg=TEXT_PRIMARY,
    font=("Arial", 18, "bold")).pack(anchor="w", pady=(0, 20))

    form = tk.Frame(left, bg=BG_CARD, padx=25, pady=25,
    highlightbackground="#252525", highlightthickness=1)
    form.pack(fill="x")

    def campo(parent, rotulo):
        tk.Label(parent, text=rotulo, bg=BG_CARD, fg=TEXT_MUTED, font=("Arial", 9, "bold")).pack(anchor="w", pady=(10,2))
        e = tk.Entry(parent, font=("Arial", 11), bg=BG_PANEL, fg=TEXT_PRIMARY, relief="flat", insertbackground=ACCENT)
        e.pack(fill="x", ipady=8)
        return e

    ent_cliente = campo(form, "NOME DO CLIENTE *")

    dt_f = tk.Frame(form, bg=BG_CARD)
    dt_f.pack(fill="x")
    sub_d = tk.Frame(dt_f, bg=BG_CARD)
    sub_d.pack(side="left", expand=True, fill="x", padx=(0,5))
    ent_data = campo(sub_d, "DATA (DD/MM)")
    sub_h = tk.Frame(dt_f, bg=BG_CARD)
    sub_h.pack(side="left", expand=True, fill="x", padx=(5,0))
    ent_hora = campo(sub_h, "HORA (HH:MM)")

    tk.Label(form, text="TIPO DE SERVIÇO", bg=BG_CARD, fg=TEXT_MUTED,
             font=("Arial", 9, "bold")).pack(anchor="w", pady=(15,2))
    tipo_var = tk.StringVar(value="Selecione...")
    menu = tk.OptionMenu(form, tipo_var, "Test Drive", "Vistoria Técnica", "Entrega de Veículo", "Revisão")
    menu.config(bg=BG_PANEL, fg=TEXT_PRIMARY, relief="flat", highlightthickness=0, font=("Arial", 10))
    menu["menu"].config(bg=BG_PANEL, fg=TEXT_PRIMARY)
    menu.pack(fill="x", ipady=5)

    btn_conf = tk.Button(form, text="CONFIRMAR AGENDAMENTO", bg=ACCENT, fg=BG_DARK,
                          font=("Arial", 11, "bold"), relief="flat", pady=12, cursor="hand2")
    btn_conf.pack(fill="x", pady=(25, 0))

    def confirmar():
        cliente = ent_cliente.get().strip()
        data    = ent_data.get().strip()
        hora    = ent_hora.get().strip()
        tipo    = tipo_var.get()
        if not cliente or not data or not hora or tipo == "Selecione...":
            messagebox.showerror("Erro", "Preencha todos os campos obrigatórios.")
            return
        db_inserir_agendamento(cliente, data, hora, tipo)
        messagebox.showinfo("Sucesso", f"Agendamento de '{cliente}' confirmado para {data} às {hora}!")
        tela_agendamento()

    btn_conf.config(command=confirmar)

    # Próximos agendamentos (lista rolável)
    prox_card = tk.Frame(left, bg=BG_PANEL, padx=20, pady=20)
    prox_card.pack(fill="both", expand=True, pady=(20, 0))
    tk.Label(prox_card, text="Próximos Agendamentos", bg=BG_PANEL, fg=TEXT_PRIMARY,
             font=("Arial", 12, "bold")).pack(anchor="w")

    prox_sf = tk.Frame(prox_card, bg=BG_PANEL)
    prox_sf.pack(fill="both", expand=True, pady=(10, 0))
    prox_canvas = tk.Canvas(prox_sf, bg=BG_PANEL, highlightthickness=0, height=200)
    prox_sb     = tk.Scrollbar(prox_sf, orient="vertical", command=prox_canvas.yview)
    prox_canvas.configure(yscrollcommand=prox_sb.set)
    prox_canvas.pack(side="left", fill="both", expand=True)
    prox_sb.pack(side="right", fill="y")
    prox_container = tk.Frame(prox_canvas, bg=BG_PANEL)
    prox_canvas.create_window((0, 0), window=prox_container, anchor="nw")
    prox_container.bind("<Configure>", lambda e: prox_canvas.configure(scrollregion=prox_canvas.bbox("all")))

    todos = db_todos_agendamentos()
    if not todos:
        tk.Label(prox_container, text="Nenhum agendamento cadastrado.", bg=BG_PANEL,
                 fg=TEXT_MUTED, font=("Arial", 10)).pack(anchor="w", pady=10)
    for cliente, hora, tipo, status, data in todos:
        item = tk.Frame(prox_container, bg=BG_CARD, pady=10, padx=10)
        item.pack(fill="x", pady=5)
        topo = tk.Frame(item, bg=BG_CARD)
        topo.pack(fill="x")
        tk.Label(topo, text=cliente, bg=BG_CARD, fg=TEXT_PRIMARY, font=("Arial", 10, "bold")).pack(side="left")
        tk.Label(topo, text=data,    bg=BG_CARD, fg=ACCENT,       font=("Arial", 9, "bold")).pack(side="right")
        tk.Label(item, text=f"{tipo} às {hora}", bg=BG_CARD, fg=TEXT_MUTED, font=("Arial", 9)).pack(anchor="w", pady=(5,0))
        tk.Label(item, text=status,              bg=BG_CARD, fg=TEXT_MUTED, font=("Arial", 8, "italic")).pack(anchor="w")

    # ── Coluna direita: compromissos de hoje ──────────────────────────────────
    right = tk.Frame(main, bg=BG_DARK)
    right.grid(row=0, column=1, sticky="nsew")
    tk.Label(right, text="Compromissos de Hoje", bg=BG_DARK, fg=TEXT_PRIMARY,
             font=("Arial", 18, "bold")).pack(anchor="w", pady=(0, 20))

    agenda = tk.Frame(right, bg=BG_PANEL, padx=20, pady=20)
    agenda.pack(fill="both", expand=True)

    comp_canvas = tk.Canvas(agenda, bg=BG_PANEL, highlightthickness=0)
    comp_sb     = tk.Scrollbar(agenda, orient="vertical", command=comp_canvas.yview)
    comp_canvas.configure(yscrollcommand=comp_sb.set)
    comp_canvas.pack(side="left", fill="both", expand=True)
    comp_sb.pack(side="right", fill="y")
    comp_container = tk.Frame(comp_canvas, bg=BG_PANEL)
    comp_canvas.create_window((0, 0), window=comp_container, anchor="nw")
    comp_container.bind("<Configure>", lambda e: comp_canvas.configure(scrollregion=comp_canvas.bbox("all")))

    hoje = db_agendamentos_hoje()
    if not hoje:
        tk.Label(comp_container, text="Nenhum compromisso para hoje.", bg=BG_PANEL,
        fg=TEXT_MUTED, font=("Arial", 10)).pack(anchor="w", pady=10)
    for cliente, hora, tipo, status in hoje:
        item = tk.Frame(comp_container, bg=BG_CARD, pady=10, padx=10)
        item.pack(fill="x", pady=5)
        tk.Label(item, text=hora, bg=BG_CARD, fg=ACCENT, font=("Arial", 10, "bold")).pack(side="left")
        inf = tk.Frame(item, bg=BG_CARD)
        inf.pack(side="left", padx=15)
        tk.Label(inf, text=f"{tipo} - {cliente}", bg=BG_CARD, fg=TEXT_PRIMARY, font=("Arial", 10)).pack(anchor="w")
        cor = SUCCESS if status == "Concluído" else DANGER if status == "Pendente" else TEXT_MUTED
        tk.Label(item, text=status.upper(), bg=BG_CARD, fg=cor, font=("Arial", 7, "bold")).pack(side="right")

    tk.Label(right, text="* Evite agendar Test Drives com intervalo menor que 30min.",
    bg=BG_DARK, fg=TEXT_MUTED, font=("Arial", 8, "italic")).pack(anchor="w", pady=10)


# =============================================================================
# Tela de Vistoria Técnica (Nova Ordem de Serviço)
# =============================================================================

def tela_vistoria_detalhada():
    limpar_tela()
    criar_navbar("   AF-DF | ORDEM DE SERVIÇO TÉCNICO", cmd_voltar=tela_adm, texto_voltar="← Voltar ao ADM")

    container = tk.Frame(frame_principal, bg=BG_DARK, padx=40, pady=20)
    container.pack(fill="both", expand=True)

    # Identificação do veículo
    header = tk.Frame(container, bg=BG_PANEL, padx=20, pady=20)
    header.pack(fill="x", pady=(0, 20))
    header.columnconfigure([0, 1, 2], weight=1)

    tk.Label(header, text="VEÍCULO / MODELO:",    bg=BG_PANEL, fg=TEXT_MUTED, font=("Arial", 8, "bold")).grid(row=0, column=0, sticky="w")
    ent_carro = tk.Entry(header, bg=BG_DARK, fg=TEXT_PRIMARY, relief="flat", font=("Arial", 11))
    ent_carro.grid(row=1, column=0, padx=(0,20), ipady=8, sticky="ew")

    tk.Label(header, text="PLACA:",               bg=BG_PANEL, fg=TEXT_MUTED, font=("Arial", 8, "bold")).grid(row=0, column=1, sticky="w")
    ent_placa = tk.Entry(header, bg=BG_DARK, fg=TEXT_PRIMARY, relief="flat", font=("Arial", 11))
    ent_placa.grid(row=1, column=1, padx=(0,20), ipady=8, sticky="ew")

    tk.Label(header, text="RESPONSÁVEL:",         bg=BG_PANEL, fg=TEXT_MUTED, font=("Arial", 8, "bold")).grid(row=0, column=2, sticky="w")
    ent_mec = tk.Entry(header, bg=BG_DARK, fg=TEXT_PRIMARY, relief="flat", font=("Arial", 11))
    ent_mec.grid(row=1, column=2, ipady=8, sticky="ew")

    tk.Label(header, text="DATA DA VISTORIA:",    bg=BG_PANEL, fg=TEXT_MUTED, font=("Arial", 8, "bold")).grid(row=2, column=0, sticky="w", pady=(10,0))
    ent_data = tk.Entry(header, bg=BG_DARK, fg=TEXT_PRIMARY, relief="flat", font=("Arial", 11))
    ent_data.grid(row=3, column=0, padx=(0,20), ipady=8, sticky="ew")
    ent_data.insert(0, datetime.now().strftime("%d/%m/%Y"))

    # Checklist de itens de vistoria
    check_frame = tk.Frame(container, bg=BG_CARD, padx=30, pady=30,
                            highlightthickness=1, highlightbackground="#252525")
    check_frame.pack(fill="x")
    tk.Label(check_frame, text="ITENS DE VISTORIA", bg=BG_CARD, fg=TEXT_PRIMARY,
             font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 15))

    itens      = ["Motor / Óleo", "Câmbio", "Suspensão", "Pneus", "Elétrica", "Ar Condicionado", "Lataria", "Higienização", "Freios", "Bateria"]
    check_vars = []
    frame_checks = tk.Frame(check_frame, bg=BG_CARD)
    frame_checks.pack(anchor="w")
    for i, item in enumerate(itens):
        v = tk.IntVar()
        check_vars.append(v)
        col_check = i % 2  # Duas colunas de checkboxes
        tk.Checkbutton(frame_checks, text=item, variable=v, bg=BG_CARD, fg=TEXT_PRIMARY,
                       selectcolor=BG_DARK, activebackground=BG_CARD).grid(row=i//2, column=col_check, sticky="w", padx=(0, 30))

    tk.Label(check_frame, text="DIAGNÓSTICO TÉCNICO:", bg=BG_CARD, fg=TEXT_MUTED,
             font=("Arial", 8, "bold"), pady=10).pack(anchor="w")
    txt_diag = tk.Text(check_frame, height=4, bg=BG_PANEL, fg=TEXT_PRIMARY, relief="flat")
    txt_diag.pack(fill="x", pady=(0, 20))

    def salvar_laudo():
        carro  = ent_carro.get().strip()
        placa  = ent_placa.get().strip()
        resp   = ent_mec.get().strip()
        data_v = ent_data.get().strip()
        diag   = txt_diag.get("1.0", "end").strip()
        if not carro or not placa:
            messagebox.showerror("Erro", "Informe o veículo e a placa.")
            return
        itens_sel = [itens[i] for i, v in enumerate(check_vars) if v.get()]
        db_inserir_vistoria(carro, placa, resp, ", ".join(itens_sel), diag, data_v)
        messagebox.showinfo("Sucesso", "Laudo salvo com sucesso!")
        tela_vistoria_detalhada()

    tk.Button(check_frame, text="SALVAR LAUDO E FINALIZAR", bg=SUCCESS, fg=TEXT_PRIMARY,
    font=("Arial", 10, "bold"), relief="flat", pady=15, command=salvar_laudo).pack(fill="x")


# =============================================================================
# Tela de Histórico de Vistorias
# =============================================================================

def tela_historico_vistorias():
    limpar_tela()
    criar_navbar("   AF-DF | HISTÓRICO DE VISTORIAS", cmd_voltar=tela_adm, texto_voltar="← Voltar ao ADM")

    container = tk.Frame(frame_principal, bg=BG_DARK, padx=40, pady=20)
    container.pack(fill="both", expand=True)

    hf = tk.Frame(container, bg=BG_CARD, padx=25, pady=20,
    highlightthickness=1, highlightbackground="#333333")
    hf.pack(fill="both", expand=True)

    vistorias = db_buscar_vistorias()
    header_f  = tk.Frame(hf, bg=BG_CARD)
    header_f.pack(fill="x", pady=(0, 15))
    tk.Label(header_f, text="Histórico de Vistorias", bg=BG_CARD, fg=TEXT_PRIMARY,
             font=("Arial", 14, "bold")).pack(side="left")
    tk.Label(header_f, text=f"Total: {len(vistorias)}", bg=BG_CARD, fg=ACCENT,
             font=("Arial", 10, "bold")).pack(side="right")
    tk.Label(hf, text="Registros de inspeções realizadas no sistema.",
             bg=BG_CARD, fg=TEXT_MUTED, font=("Arial", 9)).pack(anchor="w", pady=(0, 10))
    tk.Frame(hf, bg="#2D2D2D", height=1).pack(fill="x", pady=(0, 20))

    # Canvas com scroll
    sf    = tk.Frame(hf, bg=BG_CARD)
    sf.pack(fill="both", expand=True)
    canvas = tk.Canvas(sf, bg=BG_CARD, highlightthickness=0)
    sb     = tk.Scrollbar(sf, orient="vertical", command=canvas.yview)
    sc_f   = tk.Frame(canvas, bg=BG_CARD)
    sc_f.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=sc_f, anchor="nw")
    canvas.configure(yscrollcommand=sb.set)
    canvas.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    if not vistorias:
        tk.Label(sc_f, text="Nenhuma vistoria registrada.", bg=BG_CARD, fg=TEXT_MUTED,
                 font=("Arial", 10)).pack(anchor="w")
    else:
        for v in vistorias:
            # v: (id, carro, placa, responsavel, itens, diagnostico, data)
            card = tk.Frame(sc_f, bg=BG_PANEL, padx=18, pady=18,
                             highlightbackground="#383838", highlightthickness=1)
            card.pack(fill="x", pady=(0, 14))

            ch = tk.Frame(card, bg=BG_PANEL)
            ch.pack(fill="x")
            tk.Label(ch, text=f"{v[1]} ({v[2]})", bg=BG_PANEL, fg=TEXT_PRIMARY, font=("Arial", 11, "bold")).pack(side="left")
            tk.Label(ch, text=v[6],               bg=BG_PANEL, fg=ACCENT,       font=("Arial", 9, "bold")).pack(side="right")

            df = tk.Frame(card, bg=BG_PANEL)
            df.pack(fill="x", pady=(10, 0))
            tk.Label(df, text=f"Responsável: {v[3]}", bg=BG_PANEL, fg=TEXT_MUTED, font=("Arial", 9)).pack(anchor="w")
            tk.Label(df, text=f"Itens: {v[4]}",       bg=BG_PANEL, fg=TEXT_MUTED, font=("Arial", 9)).pack(anchor="w", pady=(2, 0))
            if v[5]:
                tk.Label(card, text="Diagnóstico:", bg=BG_PANEL, fg=TEXT_PRIMARY, font=("Arial", 9, "bold")).pack(anchor="w", pady=(12, 0))
                tk.Label(card, text=v[5], bg=BG_PANEL, fg=TEXT_MUTED, font=("Arial", 9),
                wraplength=860, justify="left").pack(anchor="w", pady=(2, 0))

            # Botão de exclusão do laudo
            def excluir_vistoria(vid=v[0]):
                if messagebox.askyesno("Confirmar", "Excluir este laudo de vistoria?"):
                    from auto_facil_db import db_excluir_vistoria
                    db_excluir_vistoria(vid)
                    tela_historico_vistorias()

            tk.Button(card, text="🗑 Excluir Laudo", bg=DANGER, fg=TEXT_PRIMARY,
            font=("Arial", 8, "bold"), relief="flat", padx=8, pady=4,
            command=excluir_vistoria).pack(anchor="e", pady=(8, 0))


# =============================================================================
# Tela de Relatórios
# =============================================================================

def tela_relatorios():
    limpar_tela()
    criar_navbar(" 📊 RELATÓRIOS E PERFORMANCE", cmd_voltar=tela_adm, texto_voltar="← Voltar")

    container = tk.Frame(frame_principal, bg=BG_DARK, padx=40, pady=30)
    container.pack(fill="both", expand=True)

    grid = tk.Frame(container, bg=BG_DARK)
    grid.pack(fill="both", expand=True)

    tipos = [
        ("Vendas por Vendedor", "📊 Gráfico de conversão e comissões do mês."),
        ("Tempo em Pátio",      "⏳ Média de dias que cada veículo fica no estoque."),
        ("Origem de Leads",     "📱 Quantos clientes vêm do Instagram vs WhatsApp."),
        ("Margem de Lucro",     "💰 Comparativo valor de compra vs valor de venda."),
    ]
    for i, (t, d) in enumerate(tipos):
        r, c = divmod(i, 2)
        card = tk.Frame(grid, bg=BG_PANEL, padx=25, pady=25,
                         highlightthickness=1, highlightbackground="#252525")
        card.grid(row=r, column=c, padx=10, pady=10, sticky="nsew")
        grid.grid_columnconfigure(c, weight=1)
        tk.Label(card, text=t, bg=BG_PANEL, fg=ACCENT,       font=("Arial", 12, "bold")).pack(anchor="w")
        tk.Label(card, text=d, bg=BG_PANEL, fg=TEXT_MUTED,   font=("Arial", 9)).pack(anchor="w", pady=(5, 15))
        tk.Button(card, text="GERAR RELATÓRIO", bg=BG_DARK, fg=TEXT_PRIMARY,
        font=("Arial", 8, "bold"), relief="flat", padx=15,
        command=lambda titulo=t: mostrar_relatorio(titulo)).pack(anchor="w")


# =============================================================================
# Tela Financeira
# =============================================================================

def tela_financeiro():
    limpar_tela()
    criar_navbar(" 📈 CENTRO FINANCEIRO", cmd_voltar=tela_adm, texto_voltar="← Voltar")

    entradas, saidas, vencimentos = db_resumo_financeiro()
    saldo = entradas - saidas

    container = tk.Frame(frame_principal, bg=BG_DARK, padx=30, pady=20)
    container.pack(fill="both", expand=True)

    def abrir_lancamento():
        """Abre janela modal para registrar novo lançamento financeiro."""
        jl = tk.Toplevel(janela)
        jl.title("Novo Lançamento")
        jl.geometry("360x300+520+220")
        jl.configure(bg=BG_DARK)
        jl.resizable(False, False)
        jl.grab_set()  # Bloqueia a janela principal enquanto essa está aberta

        tk.Label(jl, text="Novo Lançamento", bg=BG_DARK, fg=TEXT_PRIMARY,
                 font=("Arial", 14, "bold")).pack(pady=(18, 12))

        campos = {}
        for rotulo in ["Descrição", "Valor", "Vencimento"]:
            tk.Label(jl, text=rotulo, bg=BG_DARK, fg=TEXT_MUTED, font=("Arial", 9)).pack(anchor="w", padx=30)
            e = tk.Entry(jl, bg=BG_PANEL, fg=TEXT_PRIMARY, relief="flat", insertbackground=ACCENT)
            e.pack(fill="x", padx=30, pady=(2, 10), ipady=6)
            campos[rotulo] = e

        tipo_var = tk.StringVar(value="saida")
        tk.OptionMenu(jl, tipo_var, "entrada", "saida").pack(fill="x", padx=30, pady=(0, 12))

        def salvar():
            descricao = campos["Descrição"].get().strip()
            valor     = campos["Valor"].get().strip()
            if not descricao or not valor:
                messagebox.showerror("Erro", "Descrição e valor são obrigatórios.", parent=jl)
                return
            db_inserir_lancamento(descricao, valor, tipo_var.get(), campos["Vencimento"].get().strip())
            messagebox.showinfo("Sucesso", "Lançamento salvo!", parent=jl)
            jl.destroy()
            tela_financeiro()

        tk.Button(jl, text="SALVAR", bg=SUCCESS, fg=TEXT_PRIMARY,
                  font=("Arial", 9, "bold"), relief="flat",
                  command=salvar).pack(fill="x", padx=30, pady=(0, 15))

    # Cards de resumo financeiro (CORREÇÃO: era "SaÃ­das" por bug de encoding)
    resumo = tk.Frame(container, bg=BG_DARK)
    resumo.pack(fill="x", pady=(0, 20))
    for t, v, c in [("Saídas",       formatar_moeda(saidas),  DANGER),
                     ("Entradas",     formatar_moeda(entradas), SUCCESS),
                     ("Saldo Previsto",formatar_moeda(saldo),   ACCENT if saldo >= 0 else DANGER)]:
        card = tk.Frame(resumo, bg=BG_CARD, padx=15, pady=10,
                         highlightthickness=1, highlightbackground="#252525")
        card.pack(side="left", padx=(0, 15), expand=True, fill="x")
        tk.Label(card, text=t, bg=BG_CARD, fg=TEXT_MUTED,   font=("Arial", 8, "bold")).pack(anchor="w")
        tk.Label(card, text=v, bg=BG_CARD, fg=c,            font=("Arial", 14, "bold")).pack(anchor="w")

    bottom = tk.Frame(container, bg=BG_DARK)
    bottom.pack(fill="both", expand=True)

    # Lista de vencimentos (saídas)
    venf = tk.Frame(bottom, bg=BG_PANEL, padx=20, pady=20)
    venf.pack(side="left", fill="both", expand=True, padx=(0, 10))
    tk.Label(venf, text="📅 Próximos Vencimentos", bg=BG_PANEL, fg=TEXT_PRIMARY,
             font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 15))

    contas = [(desc, formatar_moeda(val), venc or "Sem data") for desc, val, venc in vencimentos]
    if not contas:
        contas = [("Nenhum vencimento cadastrado", "R$ 0,00", "")]
    for nome, valor, data in contas:
        item = tk.Frame(venf, bg=BG_PANEL)
        item.pack(fill="x", pady=5)
        tk.Label(item, text=f"• {nome}", bg=BG_PANEL, fg=TEXT_PRIMARY).pack(side="left")
        tk.Label(item, text=f"{valor} — {data}", bg=BG_PANEL, fg=DANGER, font=("Arial", 8, "bold")).pack(side="right")

    # Ações
    acoes = tk.Frame(bottom, bg=BG_CARD, padx=20, pady=20, width=250)
    acoes.pack(side="right", fill="y")
    tk.Button(acoes, text="+ NOVO LANÇAMENTO", bg=ACCENT, fg=BG_DARK,
              font=("Arial", 9, "bold"), relief="flat", pady=10,
              command=abrir_lancamento).pack(fill="x", pady=5)
    tk.Button(acoes, text="ATUALIZAR", bg=BG_PANEL, fg=TEXT_PRIMARY,
              font=("Arial", 9, "bold"), relief="flat", pady=10,
              command=tela_financeiro).pack(fill="x", pady=5)


# =============================================================================
# Tela de Financiamentos
# =============================================================================

def tela_financiamentos():
    limpar_tela()
    criar_navbar(" FINANCIAMENTOS", cmd_voltar=tela_adm, texto_voltar="← Voltar ao Painel")

    total, carteira, parcelas = db_resumo_financiamentos()

    container = tk.Frame(frame_principal, bg=BG_DARK, padx=30, pady=20)
    container.pack(fill="both", expand=True)

    resumo = tk.Frame(container, bg=BG_DARK)
    resumo.pack(fill="x", pady=(0, 20))
    for t, v, c in [("Contratos",            str(total),               ACCENT),
                     ("Carteira Financiada",  formatar_moeda(carteira), SUCCESS),
                     ("Parcelas Registradas", str(parcelas),            TEXT_PRIMARY)]:
        card = tk.Frame(resumo, bg=BG_CARD, padx=18, pady=14,
                         highlightthickness=1, highlightbackground="#252525")
        card.pack(side="left", fill="x", expand=True, padx=(0, 12))
        tk.Label(card, text=t, bg=BG_CARD, fg=TEXT_MUTED,  font=("Arial", 8, "bold")).pack(anchor="w")
        tk.Label(card, text=v, bg=BG_CARD, fg=c,           font=("Arial", 15, "bold")).pack(anchor="w", pady=(4, 0))

    lista = tk.Frame(container, bg=BG_PANEL, padx=20, pady=20)
    lista.pack(fill="both", expand=True)
    tk.Label(lista, text="Últimos Financiamentos", bg=BG_PANEL, fg=TEXT_PRIMARY,
             font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 12))

    financiamentos = db_buscar_financiamentos()
    if not financiamentos:
        tk.Label(lista, text="Nenhum financiamento cadastrado.", bg=BG_PANEL,
                 fg=TEXT_MUTED, font=("Arial", 10)).pack(anchor="w")
        return

    for veiculo, cliente, val_vei, entrada, parc, taxa, val_parc, total_fin, criado in financiamentos:
        item = tk.Frame(lista, bg=BG_CARD, padx=12, pady=10)
        item.pack(fill="x", pady=5)
        tk.Label(item, text=f"{cliente}  |  {veiculo}", bg=BG_CARD, fg=TEXT_PRIMARY,
                 font=("Arial", 10, "bold")).pack(anchor="w")
        detalhe = (
            f"Entrada {formatar_moeda(entrada)} | {parc}x de {formatar_moeda(val_parc)} | "
            f"Taxa {float(taxa or 0):.2f}% | Total {formatar_moeda(total_fin)} | {criado}"
        )
        tk.Label(item, text=detalhe, bg=BG_CARD, fg=TEXT_MUTED, font=("Arial", 9)).pack(anchor="w", pady=(3, 0))


# =============================================================================
# Tela de Gerenciar Clientes (ADM)
# =============================================================================

def tela_clientes():
    limpar_tela()
    criar_navbar(" 👤 GESTÃO E FUNIL DE VENDAS", cmd_voltar=tela_adm, texto_voltar="← Voltar ao Painel")

    container = tk.Frame(frame_principal, bg=BG_DARK, padx=30, pady=20)
    container.pack(fill="both", expand=True)

    # Botões de ação
    acoes = tk.Frame(container, bg=BG_DARK)
    acoes.pack(fill="x", pady=(0, 20))
    tk.Button(acoes, text="+ NOVO CLIENTE", bg=SUCCESS, fg=TEXT_PRIMARY,
              font=("Arial", 9, "bold"), relief="flat", padx=15, pady=8,
              command=lambda: tela_cadastro("cliente")).pack(side="left")
    tk.Button(acoes, text="EXPORTAR RELATÓRIO", bg=BG_PANEL, fg=TEXT_PRIMARY,
              font=("Arial", 9, "bold"), relief="flat", padx=15, pady=8,
              command=lambda: mostrar_relatorio("clientes")).pack(side="left", padx=10)

    # Lista rolável de clientes
    sf = tk.Frame(container, bg=BG_DARK)
    sf.pack(fill="both", expand=True)
    canvas = tk.Canvas(sf, bg=BG_DARK, highlightthickness=0)
    sb     = tk.Scrollbar(sf, orient="vertical", command=canvas.yview)
    sc_f   = tk.Frame(canvas, bg=BG_DARK)
    sc_f.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=sc_f, anchor="nw")
    canvas.configure(yscrollcommand=sb.set)
    canvas.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    tk.Label(sc_f, text="Clientes Cadastrados", bg=BG_DARK, fg=TEXT_PRIMARY,
             font=("Arial", 14, "bold")).pack(anchor="w", pady=(0, 10))

    clientes = db_buscar_clientes()
    if not clientes:
        tk.Label(sc_f, text="Nenhum cliente cadastrado.", bg=BG_DARK, fg=TEXT_MUTED,
                 font=("Arial", 10)).pack(anchor="w")
    else:
        for id_cli, nome, telefone, email, cpf in clientes:
            card = tk.Frame(sc_f, bg=BG_PANEL, padx=15, pady=10,
                             highlightbackground="#252525", highlightthickness=1)
            card.pack(fill="x", pady=5)

            info = tk.Frame(card, bg=BG_PANEL)
            info.pack(side="left", fill="x", expand=True)
            tk.Label(info, text=nome or "Cliente", bg=BG_PANEL, fg=TEXT_PRIMARY,
                     font=("Arial", 11, "bold")).pack(anchor="w")
            tk.Label(info, text=f"Tel: {telefone or '-'} | Email: {email or '-'} | CPF: {cpf or '-'}",
                     bg=BG_PANEL, fg=TEXT_MUTED, font=("Arial", 9)).pack(anchor="w", pady=(3, 0))

            # Botão de exclusão por cliente
            def excluir(cid=id_cli, cnome=nome):
                if messagebox.askyesno("Confirmar", f"Excluir o cliente '{cnome}'?\nEssa ação não pode ser desfeita."):
                    db_excluir_cliente(cid)
                    tela_clientes()

            tk.Button(card, text="🗑 Excluir", bg=DANGER, fg=TEXT_PRIMARY,
            font=("Arial", 8, "bold"), relief="flat", padx=8, pady=4,
            command=excluir).pack(side="right")

    # Rodapé com dica
    dica = tk.Frame(container, bg=BG_CARD, height=60, highlightthickness=1, highlightbackground="#252525")
    dica.pack(fill="x", pady=(20, 0))
    tk.Label(dica, text="DICA:", bg=BG_CARD, fg=ACCENT, font=("Arial", 9, "bold")).pack(side="left", padx=20, pady=15)
    tk.Label(dica, text="Você pode cadastrar novos clientes diretamente pelo botão acima.",
            bg=BG_CARD, fg=TEXT_PRIMARY, font=("Arial", 9, "italic")).pack(side="left")


# =============================================================================
# Tela de Gerenciar Equipe (ADM)
# =============================================================================

def tela_equipe():
    limpar_tela()
    criar_navbar(" 👨‍💼 GESTÃO DE EQUIPE AF-DF", cmd_voltar=tela_adm, texto_voltar="← Voltar ao Painel")

    container = tk.Frame(frame_principal, bg=BG_DARK, padx=30, pady=20)
    container.pack(fill="both", expand=True)

    # Botão de novo funcionário
    header = tk.Frame(container, bg=BG_DARK)
    header.pack(fill="x", pady=(0, 20))
    tk.Button(header, text="+ ADMITIR COLABORADOR", bg=ACCENT, fg=BG_DARK,
              font=("Arial", 9, "bold"), relief="flat", padx=15, pady=8,
              command=lambda: tela_cadastro("funcionario")).pack(side="left")

    # Lista rolável de funcionários
    sf = tk.Frame(container, bg=BG_DARK)
    sf.pack(fill="both", expand=True)
    canvas = tk.Canvas(sf, bg=BG_DARK, highlightthickness=0)
    sb     = tk.Scrollbar(sf, orient="vertical", command=canvas.yview)
    sc_f   = tk.Frame(canvas, bg=BG_DARK)
    sc_f.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=sc_f, anchor="nw")
    canvas.configure(yscrollcommand=sb.set)
    canvas.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    funcionarios = db_buscar_funcionarios()
    if not funcionarios:
        tk.Label(sc_f, text="Nenhum funcionário cadastrado.", bg=BG_DARK, fg=TEXT_MUTED,
                 font=("Arial", 10)).pack(anchor="w", pady=20)
    else:
        for id_func, nome, cargo, telefone in funcionarios:
            card = tk.Frame(sc_f, bg=BG_PANEL, padx=15, pady=15,
                             highlightthickness=1, highlightbackground="#252525")
            card.pack(fill="x", pady=5, padx=10)

            # Avatar com iniciais
            av = tk.Frame(card, bg=BG_DARK, width=40, height=40)
            av.pack(side="left", anchor="nw")
            av.pack_propagate(False)
            tk.Label(av, text=(nome or " ")[:2].upper(), bg=BG_DARK, fg=ACCENT,
                     font=("Arial", 10, "bold")).pack(expand=True)

            # Informações
            info = tk.Frame(card, bg=BG_PANEL)
            info.pack(side="left", fill="x", expand=True, padx=(10, 0))
            tk.Label(info, text=nome or "Funcionário", bg=BG_PANEL, fg=TEXT_PRIMARY,
                     font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 2))
            tk.Label(info, text=cargo    or "-",        bg=BG_PANEL, fg=TEXT_MUTED, font=("Arial", 8)).pack(anchor="w")
            tk.Label(info, text=f"Tel: {telefone or '-'}", bg=BG_PANEL, fg=TEXT_MUTED, font=("Arial", 8)).pack(anchor="w")

            # Botões de ação
            btn_frame = tk.Frame(card, bg=BG_PANEL)
            btn_frame.pack(side="right")
            tk.Button(btn_frame, text="PERFIL", bg=BG_DARK, fg=TEXT_PRIMARY,
                      font=("Arial", 7, "bold"), relief="flat", width=8,
                      command=lambda n=nome: messagebox.showinfo("Perfil", f"Perfil de {n}")).pack(side="left", padx=2)
            tk.Button(btn_frame, text="COMISSÃO", bg=BG_DARK, fg=SUCCESS,
                      font=("Arial", 7, "bold"), relief="flat", width=10,
                      command=lambda n=nome: messagebox.showinfo("Comissão", f"Extrato de comissão de {n}")).pack(side="left", padx=2)

            # Botão de exclusão por funcionário
            def excluir(fid=id_func, fnome=nome):
                if messagebox.askyesno("Confirmar", f"Demitir '{fnome}'?\nEssa ação não pode ser desfeita."):
                    db_excluir_funcionario(fid)
                    tela_equipe()

            tk.Button(btn_frame, text="🗑 Demitir", bg=DANGER, fg=TEXT_PRIMARY,
                      font=("Arial", 7, "bold"), relief="flat", padx=6,
                      command=excluir).pack(side="left", padx=2)

    # Rodapé
    footer = tk.Frame(container, bg=BG_PANEL, padx=15, pady=10)
    footer.pack(fill="x", side="bottom")
    tk.Label(footer, text="Dica: Clique em 'Comissão' para ver o extrato de vendas do colaborador.",
             bg=BG_PANEL, fg=TEXT_MUTED, font=("Arial", 8, "italic")).pack(side="left")


# =============================================================================
# Tela de Gerenciar Frota (ADM) — com exclusão e status
# =============================================================================

def tela_gerenciar_frota():
    limpar_tela()
    criar_navbar(" 🚘 CONTROLE DE FROTA", cmd_voltar=tela_adm, texto_voltar="← Voltar ao ADM")

    container = tk.Frame(frame_principal, bg=BG_DARK, padx=30, pady=20)
    container.pack(fill="both", expand=True)

    # Botão de novo veículo
    header = tk.Frame(container, bg=BG_DARK)
    header.pack(fill="x", pady=(0, 20))
    tk.Button(header, text="+ CADASTRAR VEÍCULO", bg=ACCENT, fg=BG_DARK,
              font=("Arial", 9, "bold"), relief="flat", padx=15, pady=8,
              command=lambda: tela_cadastro("frota")).pack(side="left")
    tk.Button(header, text="📋 NOVA VISTORIA", bg=BG_PANEL, fg=TEXT_PRIMARY,
              font=("Arial", 9, "bold"), relief="flat", padx=15, pady=8,
              command=tela_vistoria_detalhada).pack(side="left", padx=10)

    # Lista rolável de veículos
    sf = tk.Frame(container, bg=BG_DARK)
    sf.pack(fill="both", expand=True)
    canvas = tk.Canvas(sf, bg=BG_DARK, highlightthickness=0)
    sb     = tk.Scrollbar(sf, orient="vertical", command=canvas.yview)
    sc_f   = tk.Frame(canvas, bg=BG_DARK)
    sc_f.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=sc_f, anchor="nw")
    canvas.configure(yscrollcommand=sb.set)
    canvas.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    tk.Label(sc_f, text="Veículos na Frota", bg=BG_DARK, fg=TEXT_PRIMARY,
             font=("Arial", 14, "bold")).pack(anchor="w", pady=(0, 10))

    frota = db_buscar_frota()
    if not frota:
        tk.Label(sc_f, text="Nenhum veículo cadastrado.", bg=BG_DARK, fg=TEXT_MUTED,
                 font=("Arial", 10)).pack(anchor="w")
    else:
        for id_v, nome, ano, km, preco, cor, cambio, flex, imagem, placa in frota:
            card = tk.Frame(sc_f, bg=BG_PANEL, padx=15, pady=12,
                             highlightbackground="#252525", highlightthickness=1)
            card.pack(fill="x", pady=5)

            info = tk.Frame(card, bg=BG_PANEL)
            info.pack(side="left", fill="x", expand=True)
            preco_fmt = formatar_moeda(converter_moeda(preco)) if preco else "Consulte-nos"
            tk.Label(info, text=nome or "Veículo", bg=BG_PANEL, fg=TEXT_PRIMARY,
                     font=("Arial", 11, "bold")).pack(anchor="w")
            tk.Label(info,
                     text=f"Placa: {placa or '-'} | Ano: {ano or '-'} | KM: {km or '-'} | Cor: {cor or '-'} | {preco_fmt}",
                     bg=BG_PANEL, fg=TEXT_MUTED, font=("Arial", 9)).pack(anchor="w", pady=(3, 0))

            # Botões de ação
            btn_f = tk.Frame(card, bg=BG_PANEL)
            btn_f.pack(side="right")

            def marcar_vendido(vid=id_v, vnome=nome):
                if messagebox.askyesno("Confirmar", f"Marcar '{vnome}' como VENDIDO?"):
                    db_atualizar_status_veiculo(vid, "vendido")
                    tela_gerenciar_frota()

            def excluir_v(vid=id_v, vnome=nome):
                if messagebox.askyesno("Confirmar", f"Excluir '{vnome}' da frota?\nEssa ação não pode ser desfeita."):
                    db_excluir_veiculo(vid)
                    tela_gerenciar_frota()

            tk.Button(btn_f, text="✅ Vendido", bg=SUCCESS, fg=TEXT_PRIMARY,
            font=("Arial", 8, "bold"), relief="flat", padx=8, pady=4,
            command=marcar_vendido).pack(side="left", padx=2)
            tk.Button(btn_f, text="🗑 Excluir", bg=DANGER, fg=TEXT_PRIMARY,
            font=("Arial", 8, "bold"), relief="flat", padx=8, pady=4,
            command=excluir_v).pack(side="left", padx=2)


# =============================================================================
# Tela de Gerenciar Usuários (ADM) — exclusivo para admin
# =============================================================================

def tela_gerenciar_usuarios():
    limpar_tela()
    criar_navbar(" 🔑 GERENCIAR USUÁRIOS", cmd_voltar=tela_adm, texto_voltar="← Voltar ao ADM")

    container = tk.Frame(frame_principal, bg=BG_DARK, padx=30, pady=20)
    container.pack(fill="both", expand=True)

    # Botão de novo usuário
    header = tk.Frame(container, bg=BG_DARK)
    header.pack(fill="x", pady=(0, 20))
    tk.Button(header, text="+ NOVO USUÁRIO", bg=SUCCESS, fg=TEXT_PRIMARY,
    font=("Arial", 9, "bold"), relief="flat", padx=15, pady=8,
    command=tela_registro).pack(side="left")

    tk.Label(container,
    text="⚠  Cuidado: excluir um usuário remove permanentemente o acesso dele ao sistema.",
    bg=BG_DARK, fg=DANGER, font=("Arial", 9, "italic")).pack(anchor="w", pady=(0, 15))

    # Lista de usuários
    sf = tk.Frame(container, bg=BG_DARK)
    sf.pack(fill="both", expand=True)
    canvas = tk.Canvas(sf, bg=BG_DARK, highlightthickness=0)
    sb     = tk.Scrollbar(sf, orient="vertical", command=canvas.yview)
    sc_f   = tk.Frame(canvas, bg=BG_DARK)
    sc_f.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=sc_f, anchor="nw")
    canvas.configure(yscrollcommand=sb.set)
    canvas.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    usuarios = db_buscar_usuarios()
    if not usuarios:
        tk.Label(sc_f, text="Nenhum usuário cadastrado.", bg=BG_DARK, fg=TEXT_MUTED,
                 font=("Arial", 10)).pack(anchor="w")
    else:
        for id_u, nome, usuario_login, email, role in usuarios:
            card = tk.Frame(sc_f, bg=BG_PANEL, padx=15, pady=12,
                             highlightbackground="#252525", highlightthickness=1)
            card.pack(fill="x", pady=5)

            info = tk.Frame(card, bg=BG_PANEL)
            info.pack(side="left", fill="x", expand=True)
            badge_cor = ACCENT if role == "admin" else TEXT_MUTED
            tk.Label(info, text=f"{nome}  [{role.upper()}]", bg=BG_PANEL, fg=badge_cor,
                     font=("Arial", 11, "bold")).pack(anchor="w")
            tk.Label(info, text=f"Login: {usuario_login} | Email: {email or '-'}",
                     bg=BG_PANEL, fg=TEXT_MUTED, font=("Arial", 9)).pack(anchor="w", pady=(3, 0))

            btn_f = tk.Frame(card, bg=BG_PANEL)
            btn_f.pack(side="right")

            # Alterna entre admin/user
            novo_role = "user" if role == "admin" else "admin"
            txt_role  = "→ user" if role == "admin" else "→ admin"
            def alterar_role(uid=id_u, nr=novo_role):
                db_atualizar_role_usuario(uid, nr)
                tela_gerenciar_usuarios()

            tk.Button(btn_f, text=txt_role, bg=BG_DARK, fg=ACCENT,
                      font=("Arial", 8, "bold"), relief="flat", padx=8,
                      command=alterar_role).pack(side="left", padx=2)

            # Impede que o admin exclua a si mesmo
            def excluir_u(uid=id_u, unome=nome):
                if uid == 1:  # Protege o usuário admin principal (id=1)
                    messagebox.showwarning("Protegido", "O usuário admin principal não pode ser excluído.")
                    return
                if messagebox.askyesno("Confirmar", f"Excluir o usuário '{unome}'? Ele perderá acesso ao sistema."):
                    db_excluir_usuario(uid)
                    tela_gerenciar_usuarios()

            tk.Button(btn_f, text="🗑 Excluir", bg=DANGER, fg=TEXT_PRIMARY,
                      font=("Arial", 8, "bold"), relief="flat", padx=8,
                      command=excluir_u).pack(side="left", padx=2)


# =============================================================================
# Tela de ADM (Painel Administrativo)
# =============================================================================

def tela_adm():
    # Verificação de permissão: apenas admins acessam essa tela
    if role_logado != "admin":
        messagebox.showwarning("Acesso Negado", "Você não tem permissão para acessar o painel administrativo.")
        tela_principal()
        return

    limpar_tela()

    navbar = tk.Frame(frame_principal, bg=BG_CARD, height=70)
    navbar.pack(side="top", fill="x")
    navbar.pack_propagate(False)
    tk.Frame(navbar, bg=ACCENT, height=3).pack(side="top", fill="x")
    nc = tk.Frame(navbar, bg=BG_CARD)
    nc.pack(fill="both", expand=True, padx=20, pady=15)
    logo = tk.Label(nc, text="   AF-DF", bg=BG_CARD, fg=ACCENT, font=("Times", 18, "bold"), cursor="hand2")
    logo.pack(side="left", padx=10)
    logo.bind("<Button-1>", lambda e: tela_principal())
    btn_v = tk.Label(nc, text="← Voltar ao Menu", bg=BG_CARD, fg=TEXT_PRIMARY,
                      font=("Arial", 11, "bold"), padx=15, pady=5, cursor="hand2")
    btn_v.pack(side="right", padx=5)
    btn_v.bind("<Button-1>",    lambda e: tela_principal())
    btn_v.bind("<Enter>", lambda e: btn_v.config(fg=ACCENT_HOVER))
    btn_v.bind("<Leave>", lambda e: btn_v.config(fg=TEXT_PRIMARY))

    main = tk.Frame(frame_principal, bg=BG_DARK)
    main.pack(fill="both", expand=True, padx=40, pady=20)

    # Cabeçalho
    header = tk.Frame(main, bg=BG_DARK)
    header.pack(fill="x", pady=(10, 30))
    tk.Label(header, text="Gestão Administrativa", bg=BG_DARK, fg=TEXT_PRIMARY,
             font=("Times", 26, "bold")).pack(side="left")
    tk.Label(header, text=f"Usuário: {usuario_logado or '-'} | {data_hora_atual()}",
             bg=BG_DARK, fg=TEXT_MUTED, font=("Arial", 9)).pack(side="right")

    # KPIs
    stats = tk.Frame(main, bg=BG_DARK)
    stats.pack(fill="x", pady=(0, 30))
    total_frota, total_clientes, total_func, agend_pend, _ = db_kpis()
    total_fin, _, _ = db_resumo_financiamentos()

    for i, (titulo, valor, icone) in enumerate([
        ("Estoque Total",   f"{total_frota}/{CAPACIDADE_PATIO}", "🚗"),
        ("Clientes",        str(total_clientes),                  "👤"),
        ("Equipe",          str(total_func),                      "👨‍💼"),
        ("Financiamentos",  str(total_fin),                       "💳"),
    ]):
        card = tk.Frame(stats, bg=BG_CARD, padx=15, pady=15,
                         highlightbackground="#252525", highlightthickness=1)
        card.grid(row=0, column=i, padx=(0, 15), sticky="nsew")
        stats.grid_columnconfigure(i, weight=1)
        tk.Label(card, text=icone,  bg=BG_CARD, fg=ACCENT,       font=("Arial", 14)).pack(anchor="w")
        tk.Label(card, text=valor,  bg=BG_CARD, fg=TEXT_PRIMARY, font=("Arial", 16, "bold")).pack(anchor="w", pady=(5,0))
        tk.Label(card, text=titulo, bg=BG_CARD, fg=TEXT_MUTED,   font=("Arial", 9, "bold")).pack(anchor="w")

    # Grid de módulos
    grid = tk.Frame(main, bg=BG_DARK)
    grid.pack(fill="both", expand=True)

    modulos = [
        {"tit": "Gerenciar Clientes",      "sub": "Histórico, cadastros e exclusões",   "ico": "👤",  "cmd": tela_clientes},
        {"tit": "Equipe AF-DF",            "sub": "Vendedores, mecânicos e admissões",  "ico": "👨‍💼", "cmd": tela_equipe},
        {"tit": "Controle de Frota",       "sub": "Veículos, vendas e vistorias",       "ico": "🚘",  "cmd": tela_gerenciar_frota},
        {"tit": "Centro Financeiro",       "sub": "Fluxo de caixa e lançamentos",       "ico": "📈",  "cmd": tela_financeiro},
        {"tit": "Financiamentos",          "sub": "Contratos e parcelas",               "ico": "💳",  "cmd": tela_financiamentos},
        {"tit": "Histórico de Vistorias",  "sub": "Registros de inspeções",             "ico": "📋",  "cmd": tela_historico_vistorias},
        {"tit": "Gerenciar Usuários",      "sub": "Contas, roles e acessos",            "ico": "🔑",  "cmd": tela_gerenciar_usuarios},
        {"tit": "Relatórios",              "sub": "Performance e indicadores",          "ico": "📊",  "cmd": tela_relatorios},
    ]

    for i, mod in enumerate(modulos):
        r, c = divmod(i, 4)  # 4 módulos por linha
        card = tk.Frame(grid, bg=BG_PANEL, padx=20, pady=20, cursor="hand2")
        card.grid(row=r, column=c, padx=10, pady=10, sticky="nsew")
        grid.grid_columnconfigure(c, weight=1)
        card.bind("<Button-1>", lambda e, cmd=mod["cmd"]: cmd())

        lbl_ico  = tk.Label(card, text=mod["ico"],  bg=BG_PANEL, fg=ACCENT,      font=("Arial", 24), cursor="hand2")
        lbl_tit  = tk.Label(card, text=mod["tit"],  bg=BG_PANEL, fg=TEXT_PRIMARY,font=("Arial", 12, "bold"), cursor="hand2")
        lbl_sub  = tk.Label(card, text=mod["sub"],  bg=BG_PANEL, fg=TEXT_MUTED,  font=("Arial", 9),  cursor="hand2")
        lbl_ico.pack(anchor="nw")
        lbl_tit.pack(anchor="nw", pady=(8, 0))
        lbl_sub.pack(anchor="nw", pady=(0, 12))
        for w in (lbl_ico, lbl_tit, lbl_sub):
            w.bind("<Button-1>", lambda e, cmd=mod["cmd"]: cmd())

        tk.Button(card, text="ABRIR MÓDULO", bg=BG_DARK, fg=ACCENT,
                  font=("Arial", 8, "bold"), relief="flat", padx=10, pady=5,
                  command=mod["cmd"]).pack(side="bottom", fill="x")

    # Rodapé de status
    footer = tk.Frame(main, bg=BG_DARK)
    footer.pack(fill="x", side="bottom", pady=20)
    tk.Label(footer, text="●", bg=BG_DARK, fg=SUCCESS, font=("Arial", 10)).pack(side="left")
    tk.Label(footer, text="Banco de Dados Protegido — SQLite Local", bg=BG_DARK,
             fg=TEXT_MUTED, font=("Arial", 8)).pack(side="left", padx=5)


# =============================================================================
# Tela de Dashboard
# =============================================================================

def tela_dashboard():
    limpar_tela()

    # Carrega dados do banco
    total_frota, total_clientes, _, agend_pend, total_vistorias = db_kpis()
    entradas, saidas, _ = db_resumo_financeiro()
    total_fin, carteira, _ = db_resumo_financiamentos()
    saldo = entradas - saidas

    criar_navbar("   AF-DF | DASHBOARD", cmd_voltar=tela_principal)

    content = tk.Frame(frame_principal, bg=BG_DARK, padx=30, pady=20)
    content.pack(fill="both", expand=True)

    # Cabeçalho
    hf = tk.Frame(content, bg=BG_DARK)
    hf.pack(fill="x", pady=(0, 20))
    tk.Label(hf, text="Visão Geral do Negócio", bg=BG_DARK, fg=TEXT_PRIMARY,
             font=("Arial", 20, "bold")).pack(side="left")
    tk.Label(hf, text=f"Última atualização: {data_hora_atual()}", bg=BG_DARK, fg=TEXT_MUTED,
             font=("Arial", 9)).pack(side="right", pady=10)

    # Cards de KPI
    cards = tk.Frame(content, bg=BG_DARK)
    cards.pack(fill="x", pady=(0, 20))
    for i, (label, valor, icone) in enumerate([
        ("Entradas",          formatar_moeda(entradas),  "💰"),
        ("Financiamentos",    str(total_fin),             "✅"),
        ("Carteira Financiada",formatar_moeda(carteira), "📊"),
        ("Saldo Previsto",    formatar_moeda(saldo),      "🔄"),
    ]):
        card = tk.Frame(cards, bg=BG_CARD, padx=15, pady=15,
                         highlightbackground="#252525", highlightthickness=1)
        card.grid(row=0, column=i, padx=(0, 10), sticky="nsew")
        cards.grid_columnconfigure(i, weight=1)
        tk.Label(card, text=icone, bg=BG_CARD, fg=ACCENT,       font=("Arial", 14)).pack(anchor="w")
        tk.Label(card, text=valor, bg=BG_CARD, fg=TEXT_PRIMARY, font=("Arial", 16, "bold")).pack(anchor="w", pady=(5,0))
        tk.Label(card, text=label, bg=BG_CARD, fg=TEXT_MUTED,   font=("Arial", 8, "bold")).pack(anchor="w")

    # Seção central: inventário e alertas
    mid = tk.Frame(content, bg=BG_DARK)
    mid.pack(fill="both", expand=True)
    mid.grid_columnconfigure(0, weight=2)
    mid.grid_columnconfigure(1, weight=1)

    # Painel de ocupação do pátio
    inv = tk.Frame(mid, bg=BG_PANEL, padx=20, pady=20)
    inv.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
    tk.Label(inv, text=f"Ocupação do Pátio (Capacidade: {CAPACIDADE_PATIO})",
             bg=BG_PANEL, fg=TEXT_PRIMARY, font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 15))

    ocupacao = int((total_frota / CAPACIDADE_PATIO) * 100) if CAPACIDADE_PATIO else 0
    for cat, val in [("Ocupação Total (%)", ocupacao),
                      ("Em Vistoria",        total_vistorias),
                      ("Agend. Pendentes",   agend_pend)]:
        val_p = max(0, min(int(val), 100))
        f = tk.Frame(inv, bg=BG_PANEL)
        f.pack(fill="x", pady=8)
        tk.Label(f, text=cat,       bg=BG_PANEL, fg=TEXT_MUTED,   font=("Arial", 10)).pack(side="left")
        tk.Label(f, text=f"{val_p}",bg=BG_PANEL, fg=TEXT_PRIMARY, font=("Arial", 10, "bold")).pack(side="right")
        bg = tk.Frame(inv, bg="#2D2D2D", height=6)
        bg.pack(fill="x")
        tk.Frame(bg, bg=ACCENT if val_p < 90 else DANGER, height=6, width=val_p * 4).place(x=0, y=0)

    # Painel de alertas
    alert = tk.Frame(mid, bg=BG_PANEL, padx=20, pady=20)
    alert.grid(row=0, column=1, sticky="nsew")
    tk.Label(alert, text="⚠️ Alertas de Atenção", bg=BG_PANEL, fg=DANGER,
             font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 10))
    alertas = [
        f"{agend_pend} agendamento(s) pendente(s)",
        f"{total_vistorias} vistoria(s) no histórico",
        f"{total_fin} financiamento(s) ativo(s)",
        f"Frota: {total_frota} de {CAPACIDADE_PATIO} vagas",
    ]
    for msg in alertas:
        tk.Label(alert, text=f"• {msg}", bg=BG_PANEL, fg=TEXT_PRIMARY,
                 font=("Arial", 9), anchor="w").pack(fill="x", pady=3)

    # Rodapé com status
    log = tk.Frame(content, bg=BG_CARD, padx=20, pady=15)
    log.pack(fill="x", pady=(20, 0))
    tk.Label(log, text="Fluxo Recente de Loja", bg=BG_CARD, fg=TEXT_PRIMARY,
             font=("Arial", 10, "bold")).pack(side="left")
    tk.Label(log, text="Sistema em operação. Dados em tempo real do banco SQLite.",
             bg=BG_CARD, fg=TEXT_MUTED, font=("Arial", 9, "italic")).pack(side="right")


# =============================================================================
# Ponto de entrada
# =============================================================================

def main():
    init_db()  # Cria tabelas se não existirem
    try:
        configurar_janela()
    except tk.TclError:
        print("Erro ao iniciar o Tkinter. Verifique se o Tcl/Tk está instalado corretamente.")
        raise
    tela_login()
    janela.mainloop()


if __name__ == "__main__":
    main()