import nest_asyncio
import asyncio
from llama_index.llms.ollama import Ollama
from llama_index.core import Settings
from llama_index.tools.mcp import McpToolSpec, BasicMCPClient
from mcp.types import CallToolResult
import json
import re
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.align import Align
from rich.text import Text

nest_asyncio.apply()

# Configura o Ollama
llm = Ollama(model="qwen2.5-coder:3b", request_timeout=120.0)
Settings.llm = llm

# Console Rich
console = Console()

# Prompt melhorado para traduzir português para SQL
PROMPT_TRADUCAO = """\
Você é um especialista em traduzir português para queries SQL. 
Traduza a solicitação do usuário para uma query SQL válida.

Regras IMPORTANTES:
1. Use apenas a tabela 'times' com colunas: id, nome, estado, pontos, vitorias, empates, derrotas, saldo_gols
2. Para SELECT: use WHERE nome LIKE '%Time%' para buscar times específicos
3. Para ordenação: use ORDER BY pontos DESC
4. Para INSERT: use INSERT INTO times (colunas) VALUES (valores)
5. Retorne APENAS a query SQL, sem a palavra "sql", sem explicações, sem código markdown
6. A query deve terminar com ponto e vírgula

Exemplos de SELECT:
Input: "Mostre todos os times"
Output: SELECT * FROM times ORDER BY pontos DESC;

Input: "Mostre o nome e pontos do Flamengo"
Output: SELECT nome, pontos FROM times WHERE nome LIKE '%Flamengo%';

Input: "Quais times têm mais de 50 pontos?"
Output: SELECT nome, pontos FROM times WHERE pontos > 50 ORDER BY pontos DESC;

Input: "Mostre a classificação com vitórias e derrotas"
Output: SELECT nome, pontos, vitorias, empates, derrotas FROM times ORDER BY pontos DESC;

Exemplos de INSERT:
Input: "Adicione o time Palmeiras do estado São Paulo com 60 pontos"
Output: INSERT INTO times (nome, estado, pontos) VALUES ('Palmeiras', 'São Paulo', 60);

Input: "Adicione o Cruzeiro de Minas Gerais com 45 pontos, 15 vitórias, 0 empates, 5 derrotas e saldo de gols 10"
Output: INSERT INTO times (nome, estado, pontos, vitorias, empates, derrotas, saldo_gols) VALUES ('Cruzeiro', 'Minas Gerais', 45, 15, 0, 5, 10);

Input: "Crie um novo time chamado Botafogo"
Output: INSERT INTO times (nome) VALUES ('Botafogo');

Agora traduza: 
"""

async def traduzir_para_sql(texto_portugues):
    """Usa o Ollama para traduzir português para SQL"""
    try:
        prompt_completo = PROMPT_TRADUCAO + texto_portugues + "\nOutput: "
        resposta = await llm.acomplete(prompt_completo)
        sql = resposta.text.strip()
        
        # Limpa a resposta - remove a palavra "sql" e qualquer markdown
        sql = re.sub(r'(?i)^sql\s*', '', sql)  # Remove "sql" no início
        sql = re.sub(r'["`]', '', sql)  # Remove aspas
        sql = re.sub(r'```.*?\n', '', sql)  # Remove blocos de código markdown
        sql = re.sub(r'```', '', sql)  # Remove restante de markdown
        
        # Garante que termina com ponto e vírgula
        if not sql.endswith(';'):
            sql = sql + ';'
        
        # Remove espaços extras
        sql = ' '.join(sql.split())
        
        console.log(f"[bold cyan]SQL gerado[/]: {sql}")
        return sql
        
    except Exception as e:
        print(f"❌ Erro na tradução: {e}")
        return None

def processar_resultado(resultado):
    """Processa o resultado retornado pela ferramenta"""
    try:
        if (hasattr(resultado, 'raw_output') and 
            isinstance(resultado.raw_output, CallToolResult)):
            
            call_result = resultado.raw_output
            times = []
            
            if call_result.content:
                for item in call_result.content:
                    if hasattr(item, 'text'):
                        try:
                            dados = json.loads(item.text)
                            times.append(dados)
                        except json.JSONDecodeError:
                            # Tenta extrair manualmente se não for JSON
                            print(f"⚠️  Resultado não é JSON: {item.text}")
                            # Tenta extrair dados do texto
                            if 'nome' in item.text and 'pontos' in item.text:
                                lines = item.text.strip().split('\n')
                                time_data = {}
                                for line in lines:
                                    if ':' in line:
                                        key, value = line.split(':', 1)
                                        key = key.strip().strip('"{ }')
                                        value = value.strip().strip('", ')
                                        time_data[key] = value
                                if time_data:
                                    times.append(time_data)
            
            return times
        
        return []
        
    except Exception as e:
        print(f"❌ Erro ao processar resultado: {e}")
        return []

def _render_tabela_times(times: list[dict], titulo: str | None = None) -> None:
    """Renderiza uma tabela responsiva dos times usando Rich."""
    if not times:
        console.print(Panel("Nenhum dado para exibir.", title="📭 Vazio", border_style="red"))
        return

    # Coletar todas as colunas encontradas
    todas_colunas: set[str] = set()
    for item in times:
        if isinstance(item, dict):
            todas_colunas.update(item.keys())

    colunas = sorted(todas_colunas)

    # Criar tabela
    table = Table(
        title=titulo,
        box=box.SIMPLE_HEAVY,
        show_lines=False,
        header_style="bold white on dark_green",
        style="white",
        expand=True,
        pad_edge=False,
    )

    # Detectar colunas numéricas para alinhar à direita
    def _is_number(value: object) -> bool:
        try:
            float(str(value).replace(',', '.'))
            return True
        except Exception:
            return False

    # Adicionar colunas
    for col in colunas:
        sample_value = next((row.get(col) for row in times if isinstance(row, dict) and col in row), "")
        justify = "right" if _is_number(sample_value) else "left"
        table.add_column(col.upper(), no_wrap=False, overflow="fold", justify=justify)

    # Adicionar linhas
    for row in times:
        values = []
        for col in colunas:
            val = row.get(col, "") if isinstance(row, dict) else ""
            # Converter None para string vazia e garantir tipo str
            if val is None:
                val = ""
            text = Text(str(val))
            values.append(text)
        table.add_row(*values)

    console.print(table)

async def main():
    # Inicializa o cliente MCP
    mcp_client = BasicMCPClient("http://127.0.0.1:8000/sse")
    mcp_tool = McpToolSpec(client=mcp_client)

    # Encontra as ferramentas
    ferramentas = await mcp_tool.to_tool_list_async()
    ler_dados_tool = None
    adicionar_dados_tool = None
    
    for tool in ferramentas:
        if tool.metadata.name == "ler_dados":
            ler_dados_tool = tool
        elif tool.metadata.name == "adicionar_dados":
            adicionar_dados_tool = tool

    if not ler_dados_tool:
        print("Erro: Ferramenta 'ler_dados' não encontrada!")
        return
    
    if not adicionar_dados_tool:
        print("Erro: Ferramenta 'adicionar_dados' não encontrada!")
        return

    console.rule("⚽ [bold green]Assistente do Brasileirão[/]", style="green")
    console.print(Panel(
        Align.left("""
Exemplos de consultas (SELECT):
- Mostre todos os times
- Quais são os pontos do Flamengo?
- Mostre a classificação completa
- Times com mais de 50 pontos

Exemplos de inserções (INSERT):
- Adicione o time Palmeiras do estado São Paulo
- Crie um novo time chamado Botafogo
- Adicione o Cruzeiro com 45 pontos e 15 vitórias

Digite 'sair' para encerrar
""".strip(), vertical="top"), title="Como usar", border_style="green", expand=True))

    while True:
        try:
            entrada = input("Sua pergunta: ").strip()
            if entrada.lower() == "sair":
                break
            
            if not entrada:
                continue
            
            # Traduz português para SQL
            console.print("🔄 Traduzindo para SQL...", style="cyan")
            query_sql = await traduzir_para_sql(entrada)
            
            if not query_sql:
                console.print("❌ Não foi possível traduzir para SQL.", style="bold red")
                continue
            
            # Verifica se é uma operação INSERT
            if query_sql.strip().upper().startswith('INSERT'):
                console.print("⚡ Executando inserção...", style="yellow")
                resultado = await adicionar_dados_tool.acall(query=query_sql)
                
                # Processa o resultado do INSERT
                if (hasattr(resultado, 'raw_output') and 
                    isinstance(resultado.raw_output, CallToolResult)):
                    
                    call_result = resultado.raw_output
                    if call_result.content:
                        for item in call_result.content:
                            if hasattr(item, 'text'):
                                console.print(Panel.fit(f"✅ {item.text}", border_style="green", title="Resultado"))
                else:
                    console.print(Panel.fit("✅ Operação realizada com sucesso!", border_style="green", title="OK"))
                    
            else:
                # Executa a query SELECT
                console.print("⚡ Executando consulta...", style="yellow")
                resultado = await ler_dados_tool.acall(query=query_sql)
                times = processar_resultado(resultado)
                
                # Exibe os resultados
                if times:
                    console.rule(f"🎯 Resultados para: {entrada}", style="cyan")
                    if times and isinstance(times[0], dict):
                        _render_tabela_times(times, titulo="Classificação / Resultados")
                    else:
                        # Fallback para lista simples
                        for i, time in enumerate(times, 1):
                            console.print(f"{i}. {time}")
                            
                else:
                    console.print(Panel("""
📭 Nenhum resultado encontrado.
💡 Possíveis causas:
 - O time não existe no banco
 - A query não retornou resultados
 - Problema no processamento dos dados
""".strip(), border_style="red", title="Sem dados"))
            
            console.print()
            
        except Exception as e:
            console.print(f"❌ Erro: {e}", style="bold red")

if __name__ == "__main__":
    asyncio.run(main())
## linil viado