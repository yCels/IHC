import sqlite3
import argparse
from mcp.server.fastmcp import FastMCP

mcp = FastMCP('brasileirao-db')

def init_db():
    """Inicializa o banco de dados e retorna (conn, cursor)"""
    try:
        conn = sqlite3.connect('brasileirao.db')
        cursor = conn.cursor()
        
        # Cria a tabela se não existir
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
        
    except Exception as e:
        print(f"Erro ao inicializar banco: {e}")
        # Retorna None para ambos em caso de erro
        return None, None

@mcp.tool()
def ler_dados(query: str = "SELECT * FROM times") -> list:
    """Lê dados da tabela 'times' usando uma query SELECT."""
    conn, cursor = init_db()
    
    # Verifica se a conexão foi estabelecida corretamente
    if conn is None or cursor is None:
        return ["Erro: Não foi possível conectar ao banco de dados"]
    
    try:
        cursor.execute(query)
        resultados = cursor.fetchall()
        
        # Converter para lista de dicionários
        colunas = [desc[0] for desc in cursor.description]
        return [dict(zip(colunas, row)) for row in resultados]
        
    except sqlite3.Error as e:
        return [f"Erro SQL: {e}"]
    finally:
        if conn:
            conn.close()

@mcp.tool()
def adicionar_dados(query: str) -> str:
    """Adiciona um novo registro à tabela 'times'."""
    conn, cursor = init_db()
    
    # Verifica se a conexão foi estabelecida corretamente
    if conn is None or cursor is None:
        return "Erro: Não foi possível conectar ao banco de dados"
    
    try:
        cursor.execute(query)
        conn.commit()
        return "Dados adicionados com sucesso"
    except sqlite3.Error as e:
        return f"Erro ao adicionar dados: {e}"
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🚀 Iniciando servidor MCP do Brasileirão...")
    
    # Inicializa o banco de dados
    conn, cursor = init_db()
    if conn and cursor:
        print("✅ Banco de dados inicializado com sucesso!")
        conn.close()
    else:
        print("❌ Erro ao inicializar banco de dados")
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--server_type", type=str, default="sse", choices=["sse", "stdio"])
    args = parser.parse_args()

    print(f"🌐 Servidor rodando em modo {args.server_type}")
    mcp.run(args.server_type)