import sqlite3

con = sqlite3.connect("data/brasileirao.db")
cur = con.cursor()

# Criar tabela de times com estatísticas
cur.execute("""
CREATE TABLE IF NOT EXISTS times (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    estado TEXT,
    pontos INTEGER DEFAULT 0,
    vitorias INTEGER DEFAULT 0,
    empates INTEGER DEFAULT 0,
    derrotas INTEGER DEFAULT 0,
    saldo_gols INTEGER DEFAULT 0
)
""")

# Criar tabela de partidas
cur.execute("""
CREATE TABLE IF NOT EXISTS partidas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data DATE NOT NULL,
    mandante_id INTEGER NOT NULL,
    visitante_id INTEGER NOT NULL,
    gols_mandante INTEGER,
    gols_visitante INTEGER,
    FOREIGN KEY (mandante_id) REFERENCES times(id),
    FOREIGN KEY (visitante_id) REFERENCES times(id)
)
""")

con.commit()
con.close()