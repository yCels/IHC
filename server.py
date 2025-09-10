import sqlite3
import argparse
from mcp.server.fastmcp import FastMCP

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
    """Adiciona um novo registro à tabela 'times'."""
    conn, cursor = init_db()
    try:
        cursor.execute(query)
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Erro ao adicionar dados: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 Iniciando o servidor... ")
    
    # Primeiro, inicializa o banco para garantir que existe
    init_db()
    print("✅ Banco de dados inicializado com sucesso!")
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--server_type", type=str, default="sse", choices=["sse", "stdio"])
    args = parser.parse_args()

    mcp.run(args.server_type)