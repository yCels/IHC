import sqlite3
from mcp.server.fastmcp import FastMCP

# Inicializando o servidor MCP
mcp = FastMCP("brasileirao-sqlite")

@mcp.tool()
def adicionar_dados(query: str) -> bool:
    """Executa uma query INSERT para adicionar um registro"""
    with sqlite3.connect("brasileirao.db") as conn:  # Usando 'with' para garantir que a conexão será fechada automaticamente
        conn.execute(query)
        conn.commit()
    return True

@mcp.tool()
def ler_dados(query: str = "SELECT * FROM pessoas") -> list:
    """Executa uma query SELECT e retorna todos os registros"""
    with sqlite3.connect("brasileirao.db") as conn:  # Usando 'with' para garantir que a conexão será fechada automaticamente
        resultados = conn.execute(query).fetchall()
    return resultados

if __name__ == "__main__":
    print("Iniciando o servidor...")
