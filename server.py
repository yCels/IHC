import sqlite3
import argparse
from mcp.server.fastmcp import FastMCP

# Inicializa o servidor MCP com o nome 'brasileirao-db'
mcp = FastMCP('brasileirao-db')

# Conexão global com o banco de dados
# É importante que a conexão seja criada apenas uma vez
# e gerenciada para evitar abrir/fechar repetidamente.
# Aqui, vamos criar uma função para obter a conexão,
# garantindo que ela seja reutilizada.
_db_connection = None

def get_db_connection():
    global _db_connection
    if _db_connection is None:
        _db_connection = sqlite3.connect('brasileirao.db')
        _db_connection.row_factory = sqlite3.Row # Retorna linhas como objetos que permitem acesso por nome de coluna
    return _db_connection

# Função para criar banco e tabelas se não existirem
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabela de times com estatísticas
    cursor.execute('''
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
    ''')
    
    # Tabela de partidas (opcional)
    cursor.execute('''
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
    ''')
    
    conn.commit()
    return conn, cursor

def validate_sql_query(query: str, expected_type: str) -> bool:
    """Valida se a query SQL é do tipo esperado e não contém comandos perigosos."""
    query_lower = query.lower().strip()
    
    # Verificação básica do tipo de query
    if not query_lower.startswith(expected_type.lower()):
        print(f"Validação falhou: A query não começa com '{expected_type}'. Query: {query}")
        return False
    
    # Prevenção simples contra comandos DDL ou perigosos inesperados
    # Esta é uma validação muito básica e não substitui um parser SQL robusto.
    dangerous_keywords = ["drop", "delete from", "alter", "truncate", "create table"] # 'delete from' é permitido em adicionar_time se for um update
    if expected_type.lower() == "insert" and "delete from" in query_lower:
        # Permite INSERTs que possam conter DELETE FROM como parte de um CTE ou subconsulta, se for o caso
        pass
    elif any(keyword in query_lower for keyword in dangerous_keywords):
        print(f"Validação falhou: Query contém palavras-chave perigosas. Query: {query}")
        return False
        
    return True

# Tool para adicionar um time
@mcp.tool()
def adicionar_time(query: str) -> bool:
    """Adiciona um registro na tabela 'times' usando uma query INSERT."""
    if not validate_sql_query(query, "INSERT"):
        return False
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Erro ao adicionar time: {e}")
        return False
    # Não fechar a conexão aqui, ela será gerenciada globalmente

# Tool para ler dados da tabela times
@mcp.tool()
def ler_times(query: str = "SELECT * FROM times") -> list:
    """Lê dados da tabela 'times' usando uma query SELECT."""
    if not validate_sql_query(query, "SELECT"):
        return []
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        # Retorna resultados diretamente, a conexão não é fechada aqui
        return [dict(row) for row in cursor.fetchall()] # Retorna como lista de dicionários
    except sqlite3.Error as e:
        print(f"Erro ao ler times: {e}")
        return []
    # Não fechar a conexão aqui, ela será gerenciada globalmente

if __name__ == "__main__":
    print("🚀 Iniciando o servidor Brasileirão MCP...")

    # Configuração do parser de argumentos
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--server_type", type=str, default="sse", choices=["sse", "stdio"]
    )
    args = parser.parse_args()

    # Cria o banco de dados e tabelas
    init_db()

    # Executa o servidor MCP
    mcp.run(args.server_type)

