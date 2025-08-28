import sqlite3
from mcp.server.fastmcp import FastMCP

# Inicializando o servidor MCP
mcp = FastMCP("sqlite-demo")

@mcp.tool()
def adicionar_dados(query: str) -> bool:
    """Executa uma query INSERT para adicionar um registro"""
    conn = sqlite3.connect("demo.db")
    conn.execute(query)
    conn.commit()
    conn.close()  # Corrigido o método `close` para fechar a conexão
    return True

@mcp.tool()
def ler_dados(query: str = "SELECT * FROM pessoas") -> list:
    """Executa uma query SELECT e retorna todos os registros"""
    conn = sqlite3.connect("demo.db")
    resultados = conn.execute(query).fetchall()
    conn.close()  # Corrigido o método `close` para fechar a conexão
    return resultados

if __name__ == "__main__":
    print("Iniciando o servidor...")
