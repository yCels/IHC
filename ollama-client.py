import nest_asyncio
import asyncio
from llama_index.llms.ollama import Ollama
from llama_index.core import Settings
from llama_index.tools.mcp import McpToolSpec, BasicMCPClient
from llama_index.core.agent.workflow import FunctionAgent, ToolCall, ToolCallResult
from llama_index.core.workflow import Context

# Use nest_asyncio para permitir que o loop de eventos aninhado funcione,
# o que é útil em ambientes como notebooks Jupyter.
nest_asyncio.apply()

# Definindo o modelo LLM para "qwen2.5-coder:1.5b"
llm = Ollama(model="qwen2.5-coder:3b", request_timeout=120.0)
Settings.llm = llm

# Prompt do sistema para o agente
PROMPT_SISTEMA = """\
Você é um assistente de IA para Chamada de Ferramentas.

Antes de ajudar, interaja com nossas ferramentas para trabalhar com o banco de dados.
"""

async def obter_agente(ferramentas: McpToolSpec):
    """Cria e retorna um FunctionAgent com as ferramentas fornecidas."""
    ferramentas_list = await ferramentas.to_tool_list_async()
    agente = FunctionAgent(
        name="Agente",
        description="Agente que pode trabalhar com o nosso software de banco de dados.",
        tools=ferramentas_list,
        llm=llm,
        system_prompt=PROMPT_SISTEMA,
    )
    return agente

async def lidar_com_mensagem_usuario(
    conteudo_mensagem: str,
    agente: FunctionAgent,
    contexto_agente: Context,
    verbose: bool = False,
):
    """Lida com a mensagem de um usuário usando o agente."""
    manipulador = agente.run(conteudo_mensagem, ctx=contexto_agente)
    async for evento in manipulador.stream_events():
        if verbose and isinstance(evento, ToolCall):
            print(f"Chamando ferramenta {evento.tool_name} com os kwargs {evento.tool_kwargs}")
        elif verbose and isinstance(evento, ToolCallResult):
            print(f"Ferramenta {evento.tool_name} retornou {evento.tool_output}")

    resposta = await manipulador
    return str(resposta)

async def main():
    # Inicializa o cliente e a especificação de ferramenta do MCP
    mcp_client = BasicMCPClient("http://127.0.0.1:8000/sse")
    mcp_tool = McpToolSpec(client=mcp_client)

    # Obtém o agente
    agente = await obter_agente(mcp_tool)

    # Cria o contexto do agente
    contexto_agente = Context(agente)

    # Exibe as ferramentas disponíveis
    ferramentas_disponiveis = await mcp_tool.to_tool_list_async()
    print("Ferramentas disponíveis:")
    for ferramenta in ferramentas_disponiveis:
        print(f"{ferramenta.metadata.name}: {ferramenta.metadata.description}")

    # Loop principal de interação
    print("\nDigite 'sair' para encerrar")
    while True:
        try:
            entrada_usuario = input("\nDigite sua mensagem: ")
            if entrada_usuario.lower() == "sair":
                break
            
            print(f"\nUsuário: {entrada_usuario}")
            resposta = await lidar_com_mensagem_usuario(entrada_usuario, agente, contexto_agente, verbose=True)
            print(f"Agente: {resposta}")
        
        except KeyboardInterrupt:
            print("\nSaindo...")
            break
        except Exception as e:
            print(f"Erro: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())