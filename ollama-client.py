import nest_asyncio
import asyncio
from llama_index.llms.ollama import Ollama
from llama_index.core import Settings
from llama_index.tools.mcp import McpToolSpec, BasicMCPClient
from mcp.types import CallToolResult
import json
import re

nest_asyncio.apply()

# Configura o Ollama
llm = Ollama(model="qwen2.5-coder:3b", request_timeout=120.0)
Settings.llm = llm

# Prompt melhorado para traduzir português para SQL
PROMPT_TRADUCAO = """\
Você é um especialista em traduzir português para queries SQL. 
Traduza a solicitação do usuário para uma query SQL válida.

Regras IMPORTANTES:
1. Use apenas a tabela 'times' com colunas: id, nome, estado, pontos, vitorias, empates, derrotas, saldo_gols
2. Sempre use WHERE nome LIKE '%Time%' para buscar times específicos
3. Para ordenação, use ORDER BY pontos DESC
4. Retorne APENAS a query SQL, sem a palavra "sql", sem explicações, sem código markdown
5. A query deve terminar com ponto e vírgula

Exemplos:
Input: "Mostre todos os times"
Output: SELECT * FROM times ORDER BY pontos DESC;

Input: "Mostre o nome e pontos do Flamengo"
Output: SELECT nome, pontos FROM times WHERE nome LIKE '%Flamengo%';

Input: "Quais times têm mais de 50 pontos?"
Output: SELECT nome, pontos FROM times WHERE pontos > 50 ORDER BY pontos DESC;

Input: "Mostre a classificação com vitórias e derrotas"
Output: SELECT nome, pontos, vitorias, empates, derrotas FROM times ORDER BY pontos DESC;

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
        
        print(f"🔍 SQL gerado: {sql}")
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

async def main():
    # Inicializa o cliente MCP
    mcp_client = BasicMCPClient("http://127.0.0.1:8000/sse")
    mcp_tool = McpToolSpec(client=mcp_client)

    # Encontra a ferramenta ler_dados
    ferramentas = await mcp_tool.to_tool_list_async()
    ler_dados_tool = None
    for tool in ferramentas:
        if tool.metadata.name == "ler_dados":
            ler_dados_tool = tool
            break

    if not ler_dados_tool:
        print("Erro: Ferramenta 'ler_dados' não encontrada!")
        return

    print("⚽ Assistente do Brasileirão - Digite em Português!")
    print("Exemplos:")
    print("- Mostre todos os times")
    print("- Quais são os pontos do Flamengo?")
    print("- Mostre a classificação completa")
    print("- Times com mais de 50 pontos")
    print("Digite 'sair' para encerrar\n")

    while True:
        try:
            entrada = input("Sua pergunta: ").strip()
            if entrada.lower() == "sair":
                break
            
            if not entrada:
                continue
            
            # Traduz português para SQL
            print("🔄 Traduzindo para SQL...")
            query_sql = await traduzir_para_sql(entrada)
            
            if not query_sql:
                print("❌ Não foi possível traduzir para SQL.")
                continue
            
            # Executa a query SQL
            print("⚡ Executando consulta...")
            resultado = await ler_dados_tool.acall(query=query_sql)
            times = processar_resultado(resultado)
            
            # Exibe os resultados
            if times:
                print(f"\n🎯 Resultados para: '{entrada}'")
                print("=" * 50)
                
                # Formata a tabela
                if times and isinstance(times[0], dict):
                    # Pega todas as colunas disponíveis
                    todas_colunas = set()
                    for time in times:
                        todas_colunas.update(time.keys())
                    
                    colunas = sorted(todas_colunas)
                    headers = [col.upper() for col in colunas]
                    
                    # Imprime cabeçalho
                    header_line = " | ".join(f"{header:<15}" for header in headers)
                    print(header_line)
                    print("-" * (len(headers) * 16))
                    
                    # Imprime dados
                    for time in times:
                        linha = [str(time.get(col, '')) for col in colunas]
                        data_line = " | ".join(f"{valor:<15}" for valor in linha)
                        print(data_line)
                else:
                    for i, time in enumerate(times, 1):
                        print(f"{i}. {time}")
                        
            else:
                print("📭 Nenhum resultado encontrado.")
                print("💡 Possíveis causas:")
                print("   - O time não existe no banco")
                print("   - A query não retornou resultados")
                print("   - Problema no processamento dos dados")
            
            print()
            
        except Exception as e:
            print(f"❌ Erro: {e}")

if __name__ == "__main__":
    asyncio.run(main())