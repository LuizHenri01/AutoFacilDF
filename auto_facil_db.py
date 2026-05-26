import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path

# ── Caminhos ─────────────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).resolve().parent
DB_PATH         = BASE_DIR / "autofacildf.db"
MEDIUM_DB_PATH  = BASE_DIR / "autofacildf_medium.db"


# ── Utilitários básicos ───────────────────────────────────────────────────────

def data_hora_atual():
    """Retorna data e hora formatadas: DD/MM/AAAA HH:MM"""
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def _hash(senha: str) -> str:
    """Gera hash SHA-256 da senha."""
    return hashlib.sha256(senha.encode()).hexdigest()


def _conn() -> sqlite3.Connection:
    """Abre e retorna uma conexão com o banco principal."""
    return sqlite3.connect(DB_PATH)


def converter_moeda(valor) -> float:
    """
    Converte string de moeda brasileira (ex: 'R$ 1.500,00') para float.
    Aceita int/float diretamente.
    """
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor or "").strip()
    texto = texto.replace("R$", "").replace("r$", "").replace(" ", "")
    texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto) if texto else 0.0
    except ValueError:
        return 0.0


# ── Criação e migração do banco ───────────────────────────────────────────────

def init_db(db_path=None):
    """
    Cria todas as tabelas necessárias caso não existam.
    Também aplica migrações leves (ADD COLUMN) sem destruir dados.
    """
    db_path = Path(db_path or DB_PATH)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS usuarios (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        nome        TEXT NOT NULL,
        usuario     TEXT UNIQUE NOT NULL,
        email       TEXT,
        telefone    TEXT,
        senha_hash  TEXT NOT NULL,
        role        TEXT DEFAULT 'user',
        criado_em   TEXT
    )""")

    # Migração: garante coluna 'role' para bancos antigos
    try:
        c.execute("ALTER TABLE usuarios ADD COLUMN role TEXT DEFAULT 'user'")
    except sqlite3.OperationalError:
        pass  # Coluna já existe

    c.execute("""CREATE TABLE IF NOT EXISTS clientes (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        nome        TEXT,
        telefone    TEXT,
        endereco    TEXT,
        email       TEXT,
        cpf         TEXT,
        cidade      TEXT,
        criado_em   TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS funcionarios (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        nome        TEXT,
        telefone    TEXT,
        cargo       TEXT,
        email       TEXT,
        cpf         TEXT,
        salario     TEXT,
        criado_em   TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS frota (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        marca       TEXT,
        modelo      TEXT,
        nome        TEXT,
        ano         TEXT,
        placa       TEXT,
        km          TEXT,
        valor_compra TEXT,
        preco       TEXT,
        cor         TEXT,
        cambio      TEXT,
        flex        TEXT,
        imagem      TEXT,
        status      TEXT DEFAULT 'disponivel',
        criado_em   TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS agendamentos (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente     TEXT,
        data        TEXT,
        hora        TEXT,
        tipo        TEXT,
        status      TEXT DEFAULT 'Pendente',
        criado_em   TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS vistorias (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        carro       TEXT,
        placa       TEXT,
        responsavel TEXT,
        itens       TEXT,
        diagnostico TEXT,
        data        TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS financeiro (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        descricao   TEXT,
        valor       REAL,
        tipo        TEXT,
        vencimento  TEXT,
        criado_em   TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS financiamentos (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        veiculo         TEXT,
        cliente         TEXT,
        valor_veiculo   REAL,
        entrada         REAL,
        parcelas        INTEGER,
        taxa            REAL,
        valor_parcela   REAL,
        total_financiado REAL,
        criado_em       TEXT
    )""")

    conn.commit()
    conn.close()


# ── Funções de dados de demonstração ─────────────────────────────────────────

def _clear_tables(conn: sqlite3.Connection):
    """Limpa todas as tabelas e reseta os IDs auto-increment."""
    tabelas = [
        "usuarios", "clientes", "funcionarios", "frota",
        "agendamentos", "vistorias", "financeiro", "financiamentos",
    ]
    c = conn.cursor()
    for tabela in tabelas:
        c.execute(f"DELETE FROM {tabela}")
        c.execute("DELETE FROM sqlite_sequence WHERE name=?", (tabela,))
    conn.commit()


def create_demo_db(medium=False):
    """
    Recria o banco com dados de demonstração.
    medium=True usa o banco autofacildf_medium.db com mais registros.
    """
    db_path = MEDIUM_DB_PATH if medium else DB_PATH
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    _clear_tables(conn)
    if medium:
        _populate_medium_demo(conn)
    else:
        _populate_default_demo(conn)
    conn.commit()
    conn.close()
    print(f"Banco de dados {'médio' if medium else 'padrão'} criado em: {db_path}")


def _populate_default_demo(conn: sqlite3.Connection):
    """Popula o banco padrão com dados de demonstração (menor volume)."""
    c = conn.cursor()

    # Usuários: admin e dois usuários comuns (senha padrão: 123456)
    c.executemany(
        "INSERT INTO usuarios (nome, usuario, email, telefone, senha_hash, role, criado_em) VALUES (?,?,?,?,?,?,?)",
        [
            ("Admin",         "admin", "admin@autofacildf.com", "(61)99999-9999", _hash("123456"), "admin", data_hora_atual()),
            ("João Silva",    "joao",  "joao@email.com",        "(61)98888-8888", _hash("123456"), "user",  data_hora_atual()),
            ("Maria Santos",  "maria", "maria@email.com",       "(61)97777-7777", _hash("123456"), "user",  data_hora_atual()),
        ]
    )

    # 15 clientes da região do DF
    c.executemany(
        "INSERT INTO clientes (nome, telefone, endereco, email, cpf, cidade, criado_em) VALUES (?,?,?,?,?,?,?)",
        [
            ("Carlos Oliveira",  "(61)98765-4321", "QNN 12 Conj. C, 123", "carlos@email.com",   "123.456.789-01", "Brasília",        data_hora_atual()),
            ("Ana Pereira",      "(61)98765-4322", "QMS 7 Lote 456",       "ana@email.com",      "123.456.789-02", "Brasília",        data_hora_atual()),
            ("Pedro Lima",       "(61)98765-4323", "CNB 13 Lote 789",      "pedro@email.com",    "123.456.789-03", "Taguatinga",      data_hora_atual()),
            ("Lucia Ferreira",   "(61)98765-4324", "QNJ 2 Casa 101",       "lucia@email.com",    "123.456.789-04", "Ceilândia",       data_hora_atual()),
            ("Roberto Costa",   "(61)98765-4325", "Rua das Flores, 202",  "roberto@email.com",  "123.456.789-05", "Gama",            data_hora_atual()),
            ("Mariana Silva",    "(61)98765-4326", "Av. Elmo Serejo, 303", "mariana@email.com",  "123.456.789-06", "Sobradinho",      data_hora_atual()),
            ("Fernando Alves",  "(61)98765-4327", "QR 610 Conj. E, 404", "fernando@email.com", "123.456.789-07", "Planaltina",      data_hora_atual()),
            ("Juliana Rocha",   "(61)98765-4328", "QD 10 Bloco B, 505",  "juliana@email.com",  "123.456.789-08", "Recanto das Emas",data_hora_atual()),
            ("Gustavo Mendes",  "(61)98765-4329", "QR 406 Conj. B, 606", "gustavo@email.com",  "123.456.789-09", "Samambaia",       data_hora_atual()),
            ("Camila Santos",   "(61)98765-4330", "Av. das Araucárias, 707","camila@email.com", "123.456.789-10", "Águas Claras",    data_hora_atual()),
            ("Rafael Nunes",    "(61)98765-4331", "SQN 312 Bloco F, 808", "rafael@email.com",   "123.456.789-11", "Brasília",        data_hora_atual()),
            ("Beatriz Lima",    "(61)98765-4332", "QNL 5 Conj. B, 909",  "beatriz@email.com",  "123.456.789-12", "Taguatinga",      data_hora_atual()),
            ("Thiago Pereira",  "(61)98765-4333", "QNM 8 Casa 1010",     "thiago@email.com",   "123.456.789-13", "Ceilândia",       data_hora_atual()),
            ("Isabela Costa",   "(61)98765-4334", "Rua dos Ipês, 1111",  "isabela@email.com",  "123.456.789-14", "Gama",            data_hora_atual()),
            ("Lucas Oliveira",  "(61)98765-4335", "Av. Central, 1212",   "lucas@email.com",    "123.456.789-15", "Sobradinho",      data_hora_atual()),
        ]
    )

    # 9 funcionários
    c.executemany(
        "INSERT INTO funcionarios (nome, telefone, cargo, email, cpf, salario, criado_em) VALUES (?,?,?,?,?,?,?)",
        [
            ("José Almeida",    "(61)96666-6666", "Vendedor",    "jose@afdf.com",      "987.654.321-01", "2500.00", data_hora_atual()),
            ("Fernanda Rocha",  "(61)95555-5555", "Gerente",     "fernanda@afdf.com",  "987.654.321-02", "3500.00", data_hora_atual()),
            ("Ricardo Souza",   "(61)94444-4444", "Mecânico",    "ricardo@afdf.com",   "987.654.321-03", "2000.00", data_hora_atual()),
            ("Patrícia Nunes",  "(61)93333-3333", "Atendente",   "patricia@afdf.com",  "987.654.321-04", "1800.00", data_hora_atual()),
            ("Marcos Lima",     "(61)92222-2222", "Vendedor",    "marcos@afdf.com",    "987.654.321-05", "2400.00", data_hora_atual()),
            ("Sofia Pereira",   "(61)91111-1111", "Contadora",   "sofia@afdf.com",     "987.654.321-06", "3000.00", data_hora_atual()),
            ("Eduardo Silva",   "(61)90000-0000", "Mecânico",    "eduardo@afdf.com",   "987.654.321-07", "2100.00", data_hora_atual()),
            ("Carla Mendes",    "(61)99999-9998", "Atendente",   "carla@afdf.com",     "987.654.321-08", "1750.00", data_hora_atual()),
            ("Bruno Costa",     "(61)98888-8887", "Vendedor",    "bruno@afdf.com",     "987.654.321-09", "2600.00", data_hora_atual()),
        ]
    )

    # 10 veículos com preços realistas (mercado BR 2025/2026)
    c.executemany(
        "INSERT INTO frota (marca, modelo, nome, ano, placa, km, valor_compra, preco, cor, cambio, flex, imagem, status, criado_em) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            ("Toyota",     "Corolla",  "Toyota Corolla",     "2023", "ABC-1D23",  "18000", "108000.00", "118000.00", "Prata",   "Automático", "Flex",    "imagens/toyata.png",           "disponivel", data_hora_atual()),
            ("Honda",      "Civic",    "Honda Civic",        "2022", "DEF-2E45",  "32000",  "98000.00", "108000.00", "Preto",   "Automático", "Flex",    "imagens/honda CR-V.png",       "disponivel", data_hora_atual()),
            ("BMW",        "320i",     "BMW 320i",           "2022", "GHI-3F67",  "25000", "195000.00", "219000.00", "Branco",  "Automático", "Gasolina","imagens/BMW 210i.png",         "disponivel", data_hora_atual()),
            ("Fiat",       "Pulse",    "Fiat Pulse",         "2023", "JKL-4G89",  "15000",  "92000.00",  "99000.00", "Vermelho","Automático", "Flex",    "",                             "disponivel", data_hora_atual()),
            ("Volkswagen", "T-Cross",  "Volkswagen T-Cross", "2023", "MNO-5H01",  "20000", "110000.00", "122000.00", "Azul",    "Automático", "Flex",    "imagens/Volkswagen-Golf.jpg",  "disponivel", data_hora_atual()),
            ("Chevrolet",  "Onix",     "Chevrolet Onix",     "2024", "PQR-6I22",   "8000",  "72000.00",  "79000.00", "Cinza",   "Automático", "Flex",    "imagens/Chevrolet Onix.jpg",   "disponivel", data_hora_atual()),
            ("Hyundai",    "HB20",     "Hyundai HB20",       "2023", "STU-7J44",  "22000",  "68000.00",  "74000.00", "Branco",  "Manual",     "Flex",    "imagens/Hyundai-HB20.png",     "disponivel", data_hora_atual()),
            ("Renault",    "Kwid",     "Renault Kwid",       "2024", "VWX-8K66",   "5000",  "55000.00",  "61000.00", "Laranja", "Manual",     "Flex",    "imagens/Renault-Kwid.jpg",     "disponivel", data_hora_atual()),
            ("Nissan",     "Kicks",    "Nissan Kicks",       "2023", "YZA-9L88",  "19000", "115000.00", "128000.00", "Preto",   "Automático", "Flex",    "imagens/Nissan-Versa.jpg",     "disponivel", data_hora_atual()),
            ("Ford",       "Territory","Ford Territory",     "2022", "BCD-0M09",  "38000", "130000.00", "142000.00", "Azul",    "Automático", "Gasolina","imagens/ford-ka.jpg",          "disponivel", data_hora_atual()),
        ]
    )

    # Agendamentos de exemplo
    c.executemany(
        "INSERT INTO agendamentos (cliente, data, hora, tipo, status, criado_em) VALUES (?,?,?,?,?,?)",
        [
            ("Carlos Oliveira",  "26/05", "10:00", "Test Drive",          "Pendente",   data_hora_atual()),
            ("Ana Pereira",      "27/05", "14:00", "Vistoria Técnica",    "Confirmado", data_hora_atual()),
            ("Pedro Lima",       "28/05", "09:00", "Entrega de Veículo",  "Pendente",   data_hora_atual()),
            ("Lucia Ferreira",   "29/05", "11:00", "Revisão",             "Confirmado", data_hora_atual()),
            ("Roberto Costa",   "30/05", "16:00", "Test Drive",          "Pendente",   data_hora_atual()),
        ]
    )

    # Vistorias de exemplo
    c.executemany(
        "INSERT INTO vistorias (carro, placa, responsavel, itens, diagnostico, data) VALUES (?,?,?,?,?,?)",
        [
            ("Toyota Corolla",    "ABC-1D23", "Ricardo Souza",  "Motor / Óleo, Pneus",     "Troca de óleo 5W30 e calibragem dos pneus para 32 PSI",   "20/05/2026"),
            ("Honda Civic",       "DEF-2E45", "Eduardo Silva",  "Câmbio, Suspensão",       "Revisão do câmbio automático e alinhamento das rodas",      "21/05/2026"),
            ("BMW 320i",          "GHI-3F67", "Ricardo Souza",  "Elétrica, Ar-Cond.",      "Ajuste no módulo elétrico e recarga de gás do A/C",        "22/05/2026"),
            ("Fiat Pulse",        "JKL-4G89", "Patrícia Nunes", "Higienização, Lataria",   "Higienização completa e polimento da lataria",             "23/05/2026"),
            ("Volkswagen T-Cross","MNO-5H01", "Eduardo Silva",  "Pneus, Freios",           "Rodízio de pneus e verificação do sistema de freios",      "24/05/2026"),
        ]
    )


def _populate_medium_demo(conn: sqlite3.Connection):
    """Popula o banco médio com volume maior de dados para demonstrações."""
    c = conn.cursor()

    # Mais usuários
    c.executemany(
        "INSERT INTO usuarios (nome, usuario, email, telefone, senha_hash, role, criado_em) VALUES (?,?,?,?,?,?,?)",
        [
            ("Admin",            "admin",   "admin@autofacildf.com",   "(61)99999-9999", _hash("123456"), "admin", data_hora_atual()),
            ("João Silva",       "joao",    "joao@email.com",           "(61)98888-8888", _hash("123456"), "user",  data_hora_atual()),
            ("Maria Santos",     "maria",   "maria@email.com",          "(61)97777-7777", _hash("123456"), "user",  data_hora_atual()),
            ("Paulo Ramos",      "paulo",   "paulo@email.com",          "(61)96666-6666", _hash("123456"), "user",  data_hora_atual()),
            ("Daniela Martins",  "daniela", "daniela@email.com",        "(61)95555-5555", _hash("123456"), "user",  data_hora_atual()),
        ]
    )

    # 17 clientes
    c.executemany(
        "INSERT INTO clientes (nome, telefone, endereco, email, cpf, cidade, criado_em) VALUES (?,?,?,?,?,?,?)",
        [
            ("Carlos Oliveira",  "(61)98765-4321", "QNN 12 Conj. C, 123",  "carlos@email.com",    "123.456.789-01", "Brasília",         data_hora_atual()),
            ("Ana Pereira",      "(61)98765-4322", "QMS 7 Lote 456",        "ana@email.com",       "123.456.789-02", "Brasília",         data_hora_atual()),
            ("Pedro Lima",       "(61)98765-4323", "CNB 13 Lote 789",       "pedro@email.com",     "123.456.789-03", "Taguatinga",       data_hora_atual()),
            ("Lucia Ferreira",   "(61)98765-4324", "QNJ 2 Casa 101",        "lucia@email.com",     "123.456.789-04", "Ceilândia",        data_hora_atual()),
            ("Roberto Costa",   "(61)98765-4325", "Rua das Flores, 202",   "roberto@email.com",   "123.456.789-05", "Gama",             data_hora_atual()),
            ("Mariana Silva",    "(61)98765-4326", "Av. Elmo Serejo, 303",  "mariana@email.com",   "123.456.789-06", "Sobradinho",       data_hora_atual()),
            ("Fernando Alves",  "(61)98765-4327", "QR 610 Conj. E, 404",  "fernando@email.com",  "123.456.789-07", "Planaltina",       data_hora_atual()),
            ("Juliana Rocha",   "(61)98765-4328", "QD 10 Bloco B, 505",   "juliana@email.com",   "123.456.789-08", "Recanto das Emas", data_hora_atual()),
            ("Gustavo Mendes",  "(61)98765-4329", "QR 406 Conj. B, 606",  "gustavo@email.com",   "123.456.789-09", "Samambaia",        data_hora_atual()),
            ("Camila Santos",   "(61)98765-4330", "Av. das Araucárias 707","camila@email.com",    "123.456.789-10", "Águas Claras",     data_hora_atual()),
            ("Rafael Nunes",    "(61)98765-4331", "SQN 312 Bloco F, 808",  "rafael@email.com",    "123.456.789-11", "Brasília",         data_hora_atual()),
            ("Beatriz Lima",    "(61)98765-4332", "QNL 5 Conj. B, 909",   "beatriz@email.com",   "123.456.789-12", "Taguatinga",       data_hora_atual()),
            ("Thiago Pereira",  "(61)98765-4333", "QNM 8 Casa 1010",      "thiago@email.com",    "123.456.789-13", "Ceilândia",        data_hora_atual()),
            ("Isabela Costa",   "(61)98765-4334", "Rua dos Ipês, 1111",   "isabela@email.com",   "123.456.789-14", "Gama",             data_hora_atual()),
            ("Lucas Oliveira",  "(61)98765-4335", "Av. Central, 1212",    "lucas@email.com",     "123.456.789-15", "Sobradinho",       data_hora_atual()),
            ("Priscila Ramos",  "(61)98765-4336", "Av. das Castanheiras 13","priscila@email.com", "123.456.789-16", "Águas Claras",     data_hora_atual()),
            ("Victor Souza",    "(61)98765-4337", "QNR 7 Casa 1414",      "victor@email.com",    "123.456.789-17", "Samambaia",        data_hora_atual()),
        ]
    )

    # 11 funcionários
    c.executemany(
        "INSERT INTO funcionarios (nome, telefone, cargo, email, cpf, salario, criado_em) VALUES (?,?,?,?,?,?,?)",
        [
            ("José Almeida",     "(61)96666-6666", "Vendedor",       "jose@afdf.com",          "987.654.321-01", "2500.00", data_hora_atual()),
            ("Fernanda Rocha",   "(61)95555-5555", "Gerente",        "fernanda@afdf.com",       "987.654.321-02", "3500.00", data_hora_atual()),
            ("Ricardo Souza",    "(61)94444-4444", "Mecânico",       "ricardo@afdf.com",        "987.654.321-03", "2000.00", data_hora_atual()),
            ("Patrícia Nunes",   "(61)93333-3333", "Atendente",      "patricia@afdf.com",       "987.654.321-04", "1800.00", data_hora_atual()),
            ("Marcos Lima",      "(61)92222-2222", "Vendedor",       "marcos@afdf.com",         "987.654.321-05", "2400.00", data_hora_atual()),
            ("Sofia Pereira",    "(61)91111-1111", "Contadora",      "sofia@afdf.com",          "987.654.321-06", "3000.00", data_hora_atual()),
            ("Eduardo Silva",    "(61)90000-0000", "Mecânico",       "eduardo@afdf.com",        "987.654.321-07", "2100.00", data_hora_atual()),
            ("Carla Mendes",     "(61)99999-9998", "Atendente",      "carla@afdf.com",          "987.654.321-08", "1750.00", data_hora_atual()),
            ("Bruno Costa",      "(61)98888-8887", "Vendedor",       "bruno@afdf.com",          "987.654.321-09", "2600.00", data_hora_atual()),
            ("Camila Andrade",   "(61)97777-7776", "Assistente",     "camila.andrade@afdf.com", "987.654.321-10", "2200.00", data_hora_atual()),
            ("Aline Teixeira",   "(61)96666-6665", "Administração",  "aline@afdf.com",          "987.654.321-11", "2800.00", data_hora_atual()),
        ]
    )

    # 15 veículos com preços de mercado BR 2025/2026
    c.executemany(
        "INSERT INTO frota (marca, modelo, nome, ano, placa, km, valor_compra, preco, cor, cambio, flex, imagem, status, criado_em) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            ("Toyota",     "Corolla",   "Toyota Corolla",      "2023", "ABC-1D23",  "18000", "108000.00", "118000.00", "Prata",    "Automático", "Flex",    "imagens/toyata.png",           "disponivel", data_hora_atual()),
            ("Honda",      "Civic",     "Honda Civic",         "2022", "DEF-2E45",  "32000",  "98000.00", "108000.00", "Preto",    "Automático", "Flex",    "imagens/honda CR-V.png",       "disponivel", data_hora_atual()),
            ("BMW",        "320i",      "BMW 320i",            "2022", "GHI-3F67",  "25000", "195000.00", "219000.00", "Branco",   "Automático", "Gasolina","imagens/BMW 210i.png",         "disponivel", data_hora_atual()),
            ("Fiat",       "Pulse",     "Fiat Pulse",          "2023", "JKL-4G89",  "15000",  "92000.00",  "99000.00", "Vermelho", "Automático", "Flex",    "",                             "disponivel", data_hora_atual()),
            ("Volkswagen", "T-Cross",   "Volkswagen T-Cross",  "2023", "MNO-5H01",  "20000", "110000.00", "122000.00", "Azul",     "Automático", "Flex",    "imagens/Volkswagen-Golf.jpg",  "disponivel", data_hora_atual()),
            ("Chevrolet",  "Onix",      "Chevrolet Onix",      "2024", "PQR-6I22",   "8000",  "72000.00",  "79000.00", "Cinza",    "Automático", "Flex",    "imagens/Chevrolet Onix.jpg",   "disponivel", data_hora_atual()),
            ("Hyundai",    "HB20",      "Hyundai HB20",        "2023", "STU-7J44",  "22000",  "68000.00",  "74000.00", "Branco",   "Manual",     "Flex",    "imagens/Hyundai-HB20.png",     "disponivel", data_hora_atual()),
            ("Renault",    "Kwid",      "Renault Kwid",        "2024", "VWX-8K66",   "5000",  "55000.00",  "61000.00", "Laranja",  "Manual",     "Flex",    "imagens/Renault-Kwid.jpg",     "disponivel", data_hora_atual()),
            ("Nissan",     "Kicks",     "Nissan Kicks",        "2023", "YZA-9L88",  "19000", "115000.00", "128000.00", "Preto",    "Automático", "Flex",    "imagens/Nissan-Versa.jpg",     "disponivel", data_hora_atual()),
            ("Ford",       "Territory", "Ford Territory",      "2022", "BCD-0M09",  "38000", "130000.00", "142000.00", "Azul",     "Automático", "Gasolina","imagens/ford-ka.jpg",          "disponivel", data_hora_atual()),
            ("Jeep",       "Renegade",  "Jeep Renegade",       "2023", "EFG-1N21",  "14000", "135000.00", "149000.00", "Verde",    "Automático", "Flex",    "",                             "disponivel", data_hora_atual()),
            ("Audi",       "A3",        "Audi A3 Sedan",       "2022", "HIJ-2O43",  "28000", "195000.00", "215000.00", "Preto",    "Automático", "Gasolina","",                             "disponivel", data_hora_atual()),
            ("Renault",    "Duster",    "Renault Duster",      "2023", "KLM-3P65",  "17000",  "98000.00", "109000.00", "Branco",   "Automático", "Flex",    "",                             "disponivel", data_hora_atual()),
            ("Chevrolet",  "Tracker",   "Chevrolet Tracker",   "2023", "NOP-4Q87",  "12000", "148000.00", "162000.00", "Cinza",    "Automático", "Flex",    "",                             "disponivel", data_hora_atual()),
            ("Honda",      "HR-V",      "Honda HR-V",          "2022", "QRS-5R09",  "30000", "145000.00", "159000.00", "Prata",    "Automático", "Flex",    "",                             "disponivel", data_hora_atual()),
        ]
    )

    # Agendamentos (mais volume)
    c.executemany(
        "INSERT INTO agendamentos (cliente, data, hora, tipo, status, criado_em) VALUES (?,?,?,?,?,?)",
        [
            ("Carlos Oliveira",  "26/05", "10:00", "Test Drive",         "Pendente",   data_hora_atual()),
            ("Ana Pereira",      "27/05", "14:00", "Vistoria Técnica",   "Confirmado", data_hora_atual()),
            ("Pedro Lima",       "28/05", "09:00", "Entrega de Veículo", "Pendente",   data_hora_atual()),
            ("Lucia Ferreira",   "29/05", "11:00", "Revisão",            "Confirmado", data_hora_atual()),
            ("Roberto Costa",   "30/05", "16:00", "Test Drive",         "Pendente",   data_hora_atual()),
            ("Mariana Silva",    "26/05", "13:00", "Test Drive",         "Confirmado", data_hora_atual()),
            ("Fernando Alves",  "27/05", "10:30", "Avaliação",          "Pendente",   data_hora_atual()),
            ("Juliana Rocha",   "28/05", "15:00", "Vistoria Técnica",   "Confirmado", data_hora_atual()),
            ("Gustavo Mendes",  "29/05", "08:30", "Entrega de Veículo", "Pendente",   data_hora_atual()),
            ("Camila Santos",   "30/05", "12:00", "Revisão",            "Confirmado", data_hora_atual()),
            ("Victor Souza",    "31/05", "09:30", "Test Drive",         "Pendente",   data_hora_atual()),
            ("Priscila Ramos",  "01/06", "14:30", "Avaliação",          "Confirmado", data_hora_atual()),
        ]
    )

    # Vistorias
    c.executemany(
        "INSERT INTO vistorias (carro, placa, responsavel, itens, diagnostico, data) VALUES (?,?,?,?,?,?)",
        [
            ("Toyota Corolla",    "ABC-1D23", "Ricardo Souza",  "Motor / Óleo, Pneus",  "Troca de óleo 5W30 e calibragem 32 PSI",       "20/05/2026"),
            ("Honda Civic",       "DEF-2E45", "Eduardo Silva",  "Câmbio, Suspensão",    "Revisão do câmbio automático e alinhamento",    "21/05/2026"),
            ("BMW 320i",          "GHI-3F67", "Ricardo Souza",  "Elétrica, Ar-Cond.",   "Ajuste no módulo elétrico e recarga gás A/C",   "22/05/2026"),
            ("Fiat Pulse",        "JKL-4G89", "Patrícia Nunes", "Higienização, Lataria","Higienização completa e polimento",              "23/05/2026"),
            ("Volkswagen T-Cross","MNO-5H01", "Eduardo Silva",  "Pneus, Freios",        "Rodízio de pneus e verificação dos freios",     "24/05/2026"),
            ("Chevrolet Onix",    "PQR-6I22", "Ricardo Souza",  "Freios, Óleo",         "Troca de pastilhas de freio e óleo de motor",   "25/05/2026"),
            ("Hyundai HB20",      "STU-7J44", "Eduardo Silva",  "Alinhamento, Balanceamento","Alinhamento de direção e balanceamento de rodas","26/05/2026"),
            ("Renault Kwid",      "VWX-8K66", "Ricardo Souza",  "Bateria, Luzes",       "Substituição de bateria e revisão de lâmpadas", "27/05/2026"),
            ("Nissan Kicks",      "YZA-9L88", "Eduardo Silva",  "Suspensão, Filtros",   "Troca de buchas e filtros de ar/combustível",   "28/05/2026"),
            ("Ford Territory",    "BCD-0M09", "Ricardo Souza",  "Pneus, Revisão Geral", "Rodízio e revisão de 40.000 km",                "29/05/2026"),
        ]
    )

    # Lançamentos financeiros
    c.executemany(
        "INSERT INTO financeiro (descricao, valor, tipo, vencimento, criado_em) VALUES (?,?,?,?,?)",
        [
            ("Venda Toyota Corolla",        118000.00, "entrada", "30/05/2026", data_hora_atual()),
            ("Compra de peças BMW 320i",       3200.00, "saida",   "10/05/2026", data_hora_atual()),
            ("Manutenção Honda Civic",          1500.00, "saida",   "12/05/2026", data_hora_atual()),
            ("Venda Renault Duster",          109000.00, "entrada", "31/05/2026", data_hora_atual()),
            ("Conta de energia elétrica",        850.00, "saida",   "15/05/2026", data_hora_atual()),
            ("Venda Chevrolet Onix",           79000.00, "entrada", "28/05/2026", data_hora_atual()),
            ("Conta de água",                    280.00, "saida",   "18/05/2026", data_hora_atual()),
            ("Recebimento de financiamento",   35000.00, "entrada", "27/05/2026", data_hora_atual()),
            ("Investimento em marketing digital", 1500.00,"saida",  "20/05/2026", data_hora_atual()),
            ("Receita aluguel de espaço",        5000.00, "entrada", "25/05/2026", data_hora_atual()),
            ("Compra de material de escritório",  650.00, "saida",   "22/05/2026", data_hora_atual()),
            ("Venda Honda HR-V",             159000.00, "entrada", "29/05/2026", data_hora_atual()),
            ("Pagamento de IPVA/DPVAT frota",   4200.00, "saida",   "23/05/2026", data_hora_atual()),
            ("Venda Nissan Kicks",            128000.00, "entrada", "26/05/2026", data_hora_atual()),
            ("Pagamento de serviço terceirizado",3400.00, "saida",  "26/05/2026", data_hora_atual()),
            ("Venda Jeep Renegade",           149000.00, "entrada", "24/05/2026", data_hora_atual()),
            ("Venda Audi A3 Sedan",           215000.00, "entrada", "01/06/2026", data_hora_atual()),
            ("Limpeza e zeladoria",              500.00, "saida",   "27/05/2026", data_hora_atual()),
            ("Venda Renault Kwid",             61000.00, "entrada", "02/06/2026", data_hora_atual()),
            ("Internet e telefonia",             280.00, "saida",   "27/05/2026", data_hora_atual()),
        ]
    )

    # Financiamentos com valores corretos calculados à taxa de 1,69% a.m.
    c.executemany(
        "INSERT INTO financiamentos (veiculo, cliente, valor_veiculo, entrada, parcelas, taxa, valor_parcela, total_financiado, criado_em) VALUES (?,?,?,?,?,?,?,?,?)",
        [
            ("Toyota Corolla",   "Carlos Oliveira",  118000.00, 23600.00, 48, 1.69,  2276.82, 109287.36, data_hora_atual()),
            ("Honda Civic",      "Ana Pereira",      108000.00, 21600.00, 60, 1.69,  1740.95, 104457.00, data_hora_atual()),
            ("BMW 320i",         "Pedro Lima",       219000.00, 43800.00, 60, 1.69,  3512.87, 210772.20, data_hora_atual()),
            ("Volkswagen T-Cross","Lucia Ferreira",  122000.00, 24400.00, 48, 1.69,  2348.86, 112745.28, data_hora_atual()),
            ("Chevrolet Onix",   "Roberto Costa",    79000.00, 15800.00, 36, 1.69,  1942.47,  69928.92, data_hora_atual()),
            ("Hyundai HB20",     "Mariana Silva",    74000.00, 14800.00, 36, 1.69,  1819.12,  65488.32, data_hora_atual()),
            ("Renault Duster",   "Fernando Alves",  109000.00, 21800.00, 60, 1.69,  1748.46, 104907.60, data_hora_atual()),
            ("Nissan Kicks",     "Juliana Rocha",   128000.00, 25600.00, 48, 1.69,  2464.73, 118307.04, data_hora_atual()),
            ("Honda HR-V",       "Gustavo Mendes",  159000.00, 31800.00, 60, 1.69,  2548.61, 152916.60, data_hora_atual()),
            ("Audi A3 Sedan",    "Camila Santos",   215000.00, 43000.00, 60, 1.69,  3448.60, 206916.00, data_hora_atual()),
            ("Jeep Renegade",    "Victor Souza",    149000.00, 29800.00, 48, 1.69,  2869.29, 137725.92, data_hora_atual()),
            ("Renault Kwid",     "Priscila Ramos",   61000.00, 12200.00, 36, 1.69,  1300.73,  46826.28, data_hora_atual()),
        ]
    )


# =============================================================================
# Funções CRUD — Usuários
# =============================================================================

def db_inserir_usuario(nome, usuario, email, telefone, senha, role='user') -> bool:
    """Cria um novo usuário. Retorna False se o nome de usuário já existir."""
    try:
        conn = _conn()
        conn.execute(
            "INSERT INTO usuarios (nome,usuario,email,telefone,senha_hash,role,criado_em) VALUES (?,?,?,?,?,?,?)",
            (nome, usuario, email, telefone, _hash(senha), role, data_hora_atual())
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def db_verificar_login(usuario, senha):
    """
    Verifica credenciais. Retorna tupla (id, nome, role) se válido, senão None.
    """
    conn = _conn()
    row = conn.execute(
        "SELECT id, nome, role FROM usuarios WHERE usuario=? AND senha_hash=?",
        (usuario, _hash(senha))
    ).fetchone()
    conn.close()
    return row


def db_buscar_usuarios():
    """Retorna todos os usuários para gestão no painel ADM."""
    conn = _conn()
    rows = conn.execute(
        "SELECT id, nome, usuario, email, role FROM usuarios ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return rows


def db_atualizar_role_usuario(id_usuario: int, novo_role: str):
    """Altera o papel (role) de um usuário: 'user' ou 'admin'."""
    conn = _conn()
    conn.execute("UPDATE usuarios SET role=? WHERE id=?", (novo_role, id_usuario))
    conn.commit()
    conn.close()


def db_excluir_usuario(id_usuario: int):
    """Remove um usuário do sistema pelo ID."""
    conn = _conn()
    conn.execute("DELETE FROM usuarios WHERE id=?", (id_usuario,))
    conn.execute("DELETE FROM usuarios WHERE id=", (id_usuario,))
    conn.commit()
    conn.close()


# =============================================================================
# Funções CRUD — Clientes
# =============================================================================

def db_inserir_cliente(nome, telefone, endereco, email, cpf, cidade):
    """Cadastra um novo cliente."""
    conn = _conn()
    conn.execute(
        "INSERT INTO clientes (nome,telefone,endereco,email,cpf,cidade,criado_em) VALUES (?,?,?,?,?,?,?)",
        (nome, telefone, endereco, email, cpf, cidade, data_hora_atual())
    )
    conn.commit()
    conn.close()


def db_buscar_clientes(termo=""):
    """
    Busca clientes por nome, CPF, telefone, email, endereço ou cidade.
    Sem termo, retorna os 30 mais recentes.
    """
    conn = _conn()
    if termo:
        rows = conn.execute(
            """SELECT id,nome,telefone,email,cpf FROM clientes
               WHERE nome LIKE ? OR cpf LIKE ? OR telefone LIKE ?
                  OR email LIKE ? OR endereco LIKE ? OR cidade LIKE ?
               ORDER BY id DESC""",
            tuple(f"%{termo}%" for _ in range(6))
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id,nome,telefone,email,cpf FROM clientes ORDER BY id DESC LIMIT 30"
        ).fetchall()
    conn.close()
    return rows


def db_excluir_cliente(id_cliente: int):
    """Remove um cliente pelo ID."""
    conn = _conn()
    conn.execute("DELETE FROM clientes WHERE id=?", (id_cliente,))
    conn.commit()
    conn.close()


# =============================================================================
# Funções CRUD — Funcionários
# =============================================================================

def db_inserir_funcionario(nome, telefone, cargo, email, cpf, salario):
    """Cadastra um novo funcionário."""
    conn = _conn()
    conn.execute(
        "INSERT INTO funcionarios (nome,telefone,cargo,email,cpf,salario,criado_em) VALUES (?,?,?,?,?,?,?)",
        (nome, telefone, cargo, email, cpf, salario, data_hora_atual())
    )
    conn.commit()
    conn.close()


def db_buscar_funcionarios(termo=""):
    """
    Busca funcionários por nome, cargo, telefone, email ou CPF.
    Sem termo, retorna os 30 mais recentes.
    """
    conn = _conn()
    if termo:
        # CORREÇÃO: 5 colunas na cláusula WHERE → 5 parâmetros
        rows = conn.execute(
            """SELECT id,nome,cargo,telefone FROM funcionarios
               WHERE nome LIKE ? OR cargo LIKE ? OR telefone LIKE ?
                  OR email LIKE ? OR cpf LIKE ?
               ORDER BY id DESC""",
            tuple(f"%{termo}%" for _ in range(5))
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id,nome,cargo,telefone FROM funcionarios ORDER BY id DESC LIMIT 30"
        ).fetchall()
    conn.close()
    return rows


def db_excluir_funcionario(id_funcionario: int):
    """Remove um funcionário pelo ID."""
    conn = _conn()
    conn.execute("DELETE FROM funcionarios WHERE id=?", (id_funcionario,))
    conn.commit()
    conn.close()


# =============================================================================
# Funções CRUD — Frota (Veículos)
# =============================================================================

def db_inserir_veiculo(marca, modelo, ano, placa, km, valor_compra, preco, cor, cambio, flex, imagem=""):
    """Cadastra um novo veículo na frota."""
    nome = f"{marca} {modelo}".strip()
    conn = _conn()
    conn.execute(
        """INSERT INTO frota (marca,modelo,nome,ano,placa,km,valor_compra,preco,
                              cor,cambio,flex,imagem,criado_em)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (marca, modelo, nome, ano, placa, km, valor_compra, preco,
         cor, cambio, flex, imagem, data_hora_atual())
    )
    conn.commit()
    conn.close()


def db_buscar_frota(termo=""):
    """
    Busca veículos por nome, placa, cor, marca ou modelo.
    Retorna: (id, nome, ano, km, preco, cor, cambio, flex, imagem, placa)
    """
    conn = _conn()
    if termo:
        rows = conn.execute(
            """SELECT id,nome,ano,km,preco,cor,cambio,flex,imagem,placa FROM frota
               WHERE nome LIKE ? OR placa LIKE ? OR cor LIKE ?
                  OR marca LIKE ? OR modelo LIKE ?
               ORDER BY id DESC""",
            tuple(f"%{termo}%" for _ in range(5))
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id,nome,ano,km,preco,cor,cambio,flex,imagem,placa FROM frota ORDER BY id DESC LIMIT 60"
        ).fetchall()
    conn.close()
    return rows


def db_excluir_veiculo(id_veiculo: int):
    """Remove um veículo da frota pelo ID."""
    conn = _conn()
    conn.execute("DELETE FROM frota WHERE id=?", (id_veiculo,))
    conn.commit()
    conn.close()


def db_atualizar_status_veiculo(id_veiculo: int, status: str):
    """Atualiza o status de um veículo (ex: 'disponivel', 'vendido', 'em_vistoria')."""
    conn = _conn()
    conn.execute("UPDATE frota SET status=? WHERE id=?", (status, id_veiculo))
    conn.commit()
    conn.close()


# =============================================================================
# Funções CRUD — Agendamentos
# =============================================================================

def db_inserir_agendamento(cliente, data, hora, tipo):
    """Cria um novo agendamento com status Pendente."""
    conn = _conn()
    conn.execute(
        "INSERT INTO agendamentos (cliente,data,hora,tipo,criado_em) VALUES (?,?,?,?,?)",
        (cliente, data, hora, tipo, data_hora_atual())
    )
    conn.commit()
    conn.close()


def db_agendamentos_hoje():
    """Retorna agendamentos do dia atual (formato DD/MM)."""
    hoje = datetime.now().strftime("%d/%m")
    conn = _conn()
    rows = conn.execute(
        "SELECT cliente,hora,tipo,status FROM agendamentos WHERE data LIKE ? ORDER BY hora",
        (f"{hoje}%",)
    ).fetchall()
    conn.close()
    return rows


def db_todos_agendamentos():
    """Retorna os 20 agendamentos mais recentes."""
    conn = _conn()
    rows = conn.execute(
        "SELECT cliente,hora,tipo,status,data FROM agendamentos ORDER BY id DESC LIMIT 20"
    ).fetchall()
    conn.close()
    return rows


def db_atualizar_status_agendamento(id_agendamento: int, status: str):
    """Atualiza o status de um agendamento (Pendente / Confirmado / Concluído)."""
    conn = _conn()
    conn.execute("UPDATE agendamentos SET status=? WHERE id=?", (status, id_agendamento))
    conn.commit()
    conn.close()


def db_excluir_agendamento(id_agendamento: int):
    """Remove um agendamento pelo ID."""
    conn = _conn()
    conn.execute("DELETE FROM agendamentos WHERE id=?", (id_agendamento,))
    conn.commit()
    conn.close()


# =============================================================================
# Funções CRUD — Vistorias
# =============================================================================

def db_inserir_vistoria(carro, placa, responsavel, itens, diagnostico, data):
    """Salva um laudo de vistoria."""
    conn = _conn()
    conn.execute(
        "INSERT INTO vistorias (carro, placa, responsavel, itens, diagnostico, data) VALUES (?,?,?,?,?,?)",
        (carro, placa, responsavel, itens, diagnostico, data)
    )
    conn.commit()
    conn.close()


def db_buscar_vistorias():
    """Retorna todas as vistorias em ordem decrescente de criação."""
    conn = _conn()
    rows = conn.execute(
        "SELECT id, carro, placa, responsavel, itens, diagnostico, data FROM vistorias ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return rows


def db_excluir_vistoria(id_vistoria: int):
    """Remove um registro de vistoria pelo ID."""
    conn = _conn()
    conn.execute("DELETE FROM vistorias WHERE id=?", (id_vistoria,))
    conn.commit()
    conn.close()


# =============================================================================
# Funções CRUD — Financeiro
# =============================================================================

def db_inserir_lancamento(descricao, valor_str, tipo, vencimento):
    """Registra um lançamento financeiro (entrada ou saída)."""
    try:
        valor = converter_moeda(valor_str)
    except (AttributeError, ValueError):
        valor = 0.0
    conn = _conn()
    conn.execute(
        "INSERT INTO financeiro (descricao,valor,tipo,vencimento,criado_em) VALUES (?,?,?,?,?)",
        (descricao, valor, tipo, vencimento, data_hora_atual())
    )
    conn.commit()
    conn.close()


def db_resumo_financeiro():
    """
    Retorna (entradas_total, saidas_total, lista_vencimentos).
    vencimentos: [(descricao, valor, vencimento), ...]
    """
    conn = _conn()
    entradas    = conn.execute("SELECT COALESCE(SUM(valor),0) FROM financeiro WHERE tipo='entrada'").fetchone()[0]
    saidas      = conn.execute("SELECT COALESCE(SUM(valor),0) FROM financeiro WHERE tipo='saida'").fetchone()[0]
    vencimentos = conn.execute(
        "SELECT descricao,valor,vencimento FROM financeiro WHERE tipo='saida' ORDER BY id DESC LIMIT 10"
    ).fetchall()
    conn.close()
    return entradas, saidas, vencimentos


# =============================================================================
# Funções CRUD — Financiamentos
# =============================================================================

def db_inserir_financiamento(veiculo, cliente, valor_veiculo, entrada, parcelas, taxa, valor_parcela, total_financiado):
    """Registra um contrato de financiamento."""
    conn = _conn()
    conn.execute(
        """INSERT INTO financiamentos
           (veiculo,cliente,valor_veiculo,entrada,parcelas,taxa,valor_parcela,total_financiado,criado_em)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (veiculo, cliente, valor_veiculo, entrada, parcelas, taxa, valor_parcela, total_financiado, data_hora_atual())
    )
    conn.commit()
    conn.close()


def db_resumo_financiamentos():
    """Retorna (total_contratos, carteira_total, total_parcelas)."""
    conn = _conn()
    total    = conn.execute("SELECT COUNT(*) FROM financiamentos").fetchone()[0]
    carteira = conn.execute("SELECT COALESCE(SUM(total_financiado),0) FROM financiamentos").fetchone()[0]
    parcelas = conn.execute("SELECT COALESCE(SUM(parcelas),0) FROM financiamentos").fetchone()[0]
    conn.close()
    return total, carteira, parcelas


def db_buscar_financiamentos():
    """Retorna os 30 contratos de financiamento mais recentes."""
    conn = _conn()
    rows = conn.execute(
        """SELECT veiculo,cliente,valor_veiculo,entrada,parcelas,taxa,valor_parcela,total_financiado,criado_em
           FROM financiamentos ORDER BY id DESC LIMIT 30"""
    ).fetchall()
    conn.close()
    return rows


# =============================================================================
# KPIs gerais para Dashboard e ADM
# =============================================================================

def db_kpis():
    """
    Retorna indicadores gerais:
    (total_frota, total_clientes, total_funcionarios, agendamentos_pendentes, total_vistorias)
    """
    conn = _conn()
    frota       = conn.execute("SELECT COUNT(*) FROM frota").fetchone()[0]
    clientes    = conn.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
    funcs       = conn.execute("SELECT COUNT(*) FROM funcionarios").fetchone()[0]
    agend_pend  = conn.execute("SELECT COUNT(*) FROM agendamentos WHERE status='Pendente'").fetchone()[0]
    vistorias   = conn.execute("SELECT COUNT(*) FROM vistorias").fetchone()[0]
    conn.close()
    return frota, clientes, funcs, agend_pend, vistorias



# =============================================================================
# Ponto de entrada — linha de comando
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Criar banco de demonstração para AutoFacilDF")
    parser.add_argument(
        "--medium",
        action="store_true",
        help="Cria banco médio (mais dados) em autofacildf_medium.db",
    )
    args = parser.parse_args()
    create_demo_db(medium=args.medium)