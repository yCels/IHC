from llama_index.llms.ollama import Ollama
from llama_index.core import Settings
from llama_index.tools.mcp import McpToolSpec
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms import Context
from llama_index.llms.event import ToolCall, ToolCallResult
from llama_index.tools.mcp import BasicMCPClient  # Importando corretamente o cliente MCP

# Definindo o modelo LLM para "qwen-coder:2.5"
llm = Ollama(model="qwen-coder:2.5", request_timeout=120.0)
Settings.llm = llm

# Definindo o prompt do sistema
PROMPT_SISTEMA = """\
Você é um assistente de IA para Chamada de Ferramentas.
Antes de ajudar, interaja com nossas ferramentas para trabalhar com o banco de dados.
"""

# Função para obter o agente
async def obter_agente(ferramentas: McpToolSpec):
    ferramentas = await ferramentas.to_tool_list_async()
    agente = FunctionAgent(
        nome="Agente",
        descricao="Agente que interage com seu banco de dados",
        ferramentas=ferramentas,
        llm=llm,
        sistema_prompt=PROMPT_SISTEMA
    )
    return agente

# Função para lidar com as mensagens do usuário
async def lidar_com_mensagem_usuario(
    conteudo_mensagem: str,
    agente: FunctionAgent,
    contexto_agente: Context,
    verbose: bool = False,
):
    manipulador = agente.run(conteudo_mensagem, ctx=contexto_agente)
    async for evento in manipulador.stream_events():
        if verbose and isinstance(evento, ToolCall):
            print(f"Chamando ferramenta {evento.tool_name}")
        elif verbose and isinstance(evento, ToolCallResult):
            print(f"Ferramenta {evento.tool_name} retornou {evento.tool_output}")
    resposta = await manipulador
    return str(resposta)

# Inicializando o cliente MCP
mcp_client = BasicMCPClient("http://127.0.0.1:8000/sse")  # A URL do servidor MCP
mcp_tool = McpToolSpec(client=mcp_client)

# Obtendo o agente
agente = await obter_agente(mcp_tool)
contexto = Context(agente)

# Loop principal para interação com o usuário
while True:
    msg = input("> ")
    if msg.lower() == "sair":
        break
    resp = await lidar_com_mensagem_usuario(msg, agente, contexto)
    print("Agente:", resp)
