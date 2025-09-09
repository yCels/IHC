import sqlite3
from mcp.server.fastmcp import FastMCP

<<<<<<< Updated upstream
# Inicializando o servidor MCP
mcp = FastMCP("brasileirao-sqlite")
=======
mcp = FastMCP('brasileirao-db')

def init_db():
    conn = sqlite3.connect('brasileirao.db')
    cursor = conn.cursor()
    
    # Cria a tabela
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS times (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            estado TEXT,
            pontos INTEGER DEFAULT 0,
            vitorias INTEGER DEFAULT 0,
            empates INTEGER DEFAULT 0,
            derrotas INTEGER DEFAULT 0,
            saldo_gols INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn, cursor
>>>>>>> Stashed changes

@mcp.tool()
def ler_dados(query: str = "SELECT * FROM times") -> list:
    """Lê dados da tabela 'times' usando uma query SELECT."""
    conn, cursor = init_db()
    try:
        cursor.execute(query)
        resultados = cursor.fetchall()
        
        # Converter para lista de dicionários
        colunas = [desc[0] for desc in cursor.description]
        return [dict(zip(colunas, row)) for row in resultados]
    except sqlite3.Error as e:
        print(f"Erro ao ler dados: {e}")
        return []
    finally:
        conn.close()

@mcp.tool()
def adicionar_dados(query: str) -> bool:
<<<<<<< Updated upstream
    """Executa uma query INSERT para adicionar um registro"""
    with sqlite3.connect("brasileirao.db") as conn:  # Usando 'with' para garantir que a conexão será fechada automaticamente
        conn.execute(query)
=======
    """Adiciona um novo registro à tabela 'times'."""
    conn, cursor = init_db()
    try:
        cursor.execute(query)
>>>>>>> Stashed changes
        conn.commit()
    return True

<<<<<<< Updated upstream
@mcp.tool()
def ler_dados(query: str = "SELECT * FROM pessoas") -> list:
    """Executa uma query SELECT e retorna todos os registros"""
    with sqlite3.connect("brasileirao.db") as conn:  # Usando 'with' para garantir que a conexão será fechada automaticamente
        resultados = conn.execute(query).fetchall()
    return resultados

if __name__ == "__main__":
    print("Iniciando o servidor...")
=======
if __name__ == "__main__":
    print("🚀 Iniciando o servidor... ")
    
    # Primeiro, inicializa o banco para garantir que existe
    init_db()
    print("✅ Banco de dados inicializado com sucesso!")
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--server_type", type=str, default="sse", choices=["sse", "stdio"])
    args = parser.parse_args()

    mcp.run(args.server_type)
>>>>>>> Stashed changes
