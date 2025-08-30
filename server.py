import sqlite3
import argparse
from mcp.server.fastmcp import FastMCP

# Inicializa o servidor MCP com o nome 'brasileirao-db'
mcp = FastMCP('brasileirao-db')

# A função `init_db()` cria o banco de dados e a tabela se eles não existirem.
def init_db():
    conn = sqlite3.connect('brasileirao.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pessoas (
            id INTEGER PRIMARY KEY,
            nome TEXT NOT NULL,
            idade INTEGER NOT NULL
        )
    ''')
    conn.commit()
    return conn, cursor

@mcp.tool()
def adicionar_dados(query: str) -> bool:
    """Adiciona um novo registro à tabela 'pessoas' usando uma query INSERT.

    Args:
        query (str): Query SQL INSERT no formato:
            INSERT INTO pessoas (nome, idade)
            VALUES ('Nome Exemplo', 30)

    Retorna:
        bool: True se o dado foi adicionado, False em caso de erro.
    """
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

@mcp.tool()
def ler_dados(query: str = "SELECT * FROM pessoas") -> list:
    """Lê dados da tabela 'pessoas' usando uma query SELECT.

    Args:
        query (str): Query SQL SELECT (padrão: "SELECT * FROM pessoas").

    Retorna:
        list: Lista de tuplas contendo os resultados da query.
    """
    conn, cursor = init_db()
    try:
        cursor.execute(query)
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Erro ao ler dados: {e}")
        return []
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 Iniciando o servidor... ")

    # Configuração do parser de argumentos para flexibilidade
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--server_type", type=str, default="sse", choices=["sse", "stdio"]
    )
    
    args = parser.parse_args()

    # Cria o banco de dados e a tabela antes de iniciar o servidor
    init_db()

    # Executa o servidor com o tipo especificado
    mcp.run(args.server_type)