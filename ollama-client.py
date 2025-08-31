import nest_asyncio
import asyncio
import pandas as pd
from llama_index.llms.ollama import Ollama
from llama_index.core import Settings
from llama_index.tools.mcp import McpToolSpec, BasicMCPClient
from llama_index.core.agent.workflow import FunctionAgent, ToolCall, ToolCallResult
from llama_index.core.workflow import Context
import re
import unicodedata # Importar unicodedata

nest_asyncio.apply()

# Configura o modelo Ollama
llm = Ollama(model="qwen2.5-coder:1.5b", request_timeout=120.0)
Settings.llm = llm

# Função para remover acentos
def remover_acentos(texto):
    nfkd_form = unicodedata.normalize('NFKD', texto)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

# Prompt de sistema
PROMPT_SISTEMA = """\
Você é um assistente de IA para Chamada de Ferramentas.
Antes de ajudar, interaja com nossas ferramentas para trabalhar com o banco de dados.
Use apenas colunas existentes: id, nome, estado, pontos, vitorias, empates, derrotas, saldo_gols.
Se a pergunta for sobre "pontuação", "vitórias", "empates", "derrotas" ou "saldo de gols" de um time, **sempre retorne os campos relevantes incluindo o nome do time e o campo da estatística solicitada**.
"""

# Cria o agente
async def obter_agente(ferramentas: McpToolSpec):
    ferramentas_list = await ferramentas.to_tool_list_async()
    agente = FunctionAgent(
        name="Agente",
        description="Agente que trabalha com o banco de dados do Brasileirão.",
        tools=ferramentas_list,
        llm=llm,
        system_prompt=PROMPT_SISTEMA,
    )
    return agente

def processar_retorno(content, colunas=None):
    """
    Converte o retorno da ferramenta MCP em DataFrame corretamente.
    - content: lista de dicionários (quando vem do ler_times) ou lista de TextContent
               (se vier de outras ferramentas que ainda retornam TextContent)
    - colunas: lista de nomes das colunas (opcional)
    """
    # Verifica se o conteúdo já é uma lista de dicionários (novo formato do ler_times)
    if isinstance(content, list) and all(isinstance(item, dict) for item in content):
        if not content: # Se a lista de dicionários estiver vazia
            return pd.DataFrame(columns=colunas if colunas else ["Resultado"])
        return pd.DataFrame(content, columns=colunas if colunas else content[0].keys())

    texts = []
    if isinstance(content, str):
        # Se for uma string, extrai os textos usando regex (compatibilidade com formato antigo)
        texts = re.findall(r"text='(.*?)'", content)
    elif isinstance(content, list):
        # Se for uma lista (e não de dicionários), assume TextContent ou similar
        texts = [c.text if hasattr(c, "text") else str(c) for c in content]

    # Se não houver coluna especificada ou nenhum texto extraído, retorna com 'Resultado'
    if colunas is None or not colunas or not texts:
        # Se não há textos, retorna um DataFrame vazio com a coluna 'Resultado'
        if not texts:
            return pd.DataFrame(columns=["Resultado"])
        return pd.DataFrame(texts, columns=["Resultado"])

    num_colunas = len(colunas)
    if num_colunas == 0:
        # Evita divisão por zero se colunas estiver vazia (embora já tratada acima)
        return pd.DataFrame(texts, columns=["Resultado"])

    # Agrupa os textos em linhas conforme o número de colunas
    # Certifica-se de que o número de textos seja um múltiplo do número de colunas
    if len(texts) % num_colunas != 0:
        print(f"Aviso: O número de textos ({len(texts)}) não é um múltiplo exato do número de colunas esperadas ({num_colunas}). Isso pode levar a um DataFrame incompleto.")
        # Para evitar erros de índice, ajusta o tamanho da lista de textos para o maior múltiplo possível
        texts = texts[:(len(texts) // num_colunas) * num_colunas]

    linhas = [texts[i:i + num_colunas] for i in range(0, len(texts), num_colunas)]

    df = pd.DataFrame(linhas, columns=colunas)
    return df


# Lida com a mensagem do usuário
async def lidar_com_mensagem_usuario(conteudo_mensagem: str, agente: FunctionAgent, contexto_agente: Context, verbose: bool = False):
    manipulador = agente.run(conteudo_mensagem, ctx=contexto_agente)
    resultado_final = None
    current_columns = None # Variável para armazenar os nomes das colunas

    async for evento in manipulador.stream_events():
        if verbose and isinstance(evento, ToolCall):
            print(f"Chamando ferramenta {evento.tool_name} com os kwargs {evento.tool_kwargs}")
            # Extrair nomes das colunas da query SQL
            query = evento.tool_kwargs.get('query', '')
            match = re.search(r'SELECT (.*?) FROM', query, re.IGNORECASE)
            if match:
                columns_str = match.group(1).strip()
                current_columns = [col.strip() for col in columns_str.split(',')]
            else:
                current_columns = None # Reset se a query não contiver SELECT
        # Mover a lógica de processamento do ToolCallResult para fora da condição 'if verbose'
        if isinstance(evento, ToolCallResult):
            if verbose:
                print(f"Ferramenta {evento.tool_name} retornou {evento.tool_output}")
            if hasattr(evento.tool_output, 'content'): # Verifica se existe o atributo 'content'
                # Passar os nomes das colunas para processar_retorno
                # O conteúdo real que queremos processar está em evento.tool_output.content
                # E ele já deve vir estruturado (lista de dicionários) do server.py
                df = processar_retorno(evento.tool_output.content, colunas=current_columns) # Passa o conteúdo direto
                resultado_final = df

    # Prioriza o resultado da ferramenta se ele foi obtido
    if resultado_final is not None:
        # Mapeamento de palavras-chave para colunas do banco de dados e formatos de frase
        statistic_map = {
            "pontuacao": {"column": "pontos", "phrase": "tem {} pontos."},
            "vitorias": {"column": "vitorias", "phrase": "tem {} vitórias."},
            "empates": {"column": "empates", "phrase": "tem {} empates."},
            "derrotas": {"column": "derrotas", "phrase": "tem {} derrotas."},
            "saldo de gols": {"column": "saldo_gols", "phrase": "tem saldo de gols de {}."}
        }

        for keyword, info in statistic_map.items():
            if keyword in conteudo_mensagem.lower() and info["column"] in resultado_final.columns:
                team_name_match = re.search(fr'{keyword}\s+([\w\s-]+)', conteudo_mensagem.lower())
                team_name = None
                if team_name_match:
                    team_name = team_name_match.group(1).strip()  # Manter o nome original para exibição
                    normalized_team_name = remover_acentos(team_name).lower()  # Normalizar para comparação

                if team_name and "nome" in resultado_final.columns:
                    normalized_df_names = resultado_final["nome"].apply(lambda x: remover_acentos(str(x)).lower())
                    matching_rows = resultado_final[normalized_df_names == normalized_team_name]

                    if not matching_rows.empty:
                        statistic_value = matching_rows[info["column"]].iloc[0]
                        return f"{team_name.title()} {info["phrase"].format(statistic_value)}"

        # Se não encontrar uma palavra-chave específica ou o time, retornar a tabela completa ou mensagem de erro
        if not resultado_final.empty:
            return resultado_final
        else:
            return "Nenhum time encontrado para a sua consulta ou estatística específica."

    # Se nenhuma ferramenta produziu um resultado final DataFrame, obter a resposta textual do agente
    resposta = await manipulador
    return str(resposta)

# Loop principal
async def main():
    mcp_client = BasicMCPClient("http://127.0.0.1:8000/sse")
    mcp_tool = McpToolSpec(client=mcp_client)
    agente = await obter_agente(mcp_tool)
    contexto_agente = Context(agente)

    ferramentas_disponiveis = await mcp_tool.to_tool_list_async()
    print("Ferramentas disponíveis:")
    for ferramenta in ferramentas_disponiveis:
        print(f"{ferramenta.metadata.name}: {ferramenta.metadata.description}")

    print("\nDigite 'sair' para encerrar")
    while True:
        try:
            entrada_usuario = input("\nDigite sua mensagem: ")
            if entrada_usuario.lower() == "sair":
                break

            print(f"\nUsuário: {entrada_usuario}")
            resposta = await lidar_com_mensagem_usuario(entrada_usuario, agente, contexto_agente, verbose=False)

            if isinstance(resposta, pd.DataFrame):
                if resposta.empty:
                    print("\nNenhum time encontrado na tabela.")
                else:
                    print("\nTabela de Times:")
                    print(resposta.to_string(index=False))
            else:
                print(f"Agente: {resposta}")

        except KeyboardInterrupt:
            print("\nSaindo...")
            break
        except Exception as e:
            print(f"Erro: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
