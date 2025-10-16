import nest_asyncio
import asyncio
from llama_index.llms.ollama import Ollama
from llama_index.core import Settings
from llama_index.tools.mcp import McpToolSpec, BasicMCPClient
from mcp.types import CallToolResult
import json
import re
# Importações do Rich são mantidas para logging no console
from rich.console import Console
from rich.panel import Panel
# --- NOVAS DEPENDÊNCIAS DO TELEGRAM E WHISPER ---
from telebot.async_telebot import AsyncTeleBot
import whisper
import tempfile
import os
# A importação 'subprocess' foi removida, pois não é mais necessária.
# --------------------------------------------------

nest_asyncio.apply()

# Configura o Ollama (mantido)
llm = Ollama(model="qwen2.5-coder:3b", request_timeout=120.0)
# Settings.llm será definido após o carregamento das ferramentas.

# Console Rich (para logs e inicialização)
console = Console()

# --- CONFIGURAÇÕES DO TELEGRAM ---
# ⚠️ TOKEN MANTIDO COMO FORNECIDO
TELEGRAM_TOKEN = "<chavedobotdotelegram>"
bot = AsyncTeleBot(TELEGRAM_TOKEN, parse_mode='Markdown') # Usamos Markdown para formatação
# --------------------------------

# Prompt melhorado para traduzir português para SQL (Mantido inalterado)
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

# As ferramentas serão definidas globalmente após a inicialização no main.
ler_dados_tool = None
adicionar_dados_tool = None

# --- FUNÇÕES DE UTILIDADE ---

async def traduzir_para_sql(texto_portugues: str) -> str:
    """Usa o Ollama para traduzir português para SQL (Mantido)"""
    try:
        prompt_completo = PROMPT_TRADUCAO + texto_portugues + "\nOutput: "
        resposta = await llm.acomplete(prompt_completo)
        sql = resposta.text.strip()
        
        # Limpa a resposta - remove a palavra "sql" e qualquer markdown
        sql = re.sub(r'(?i)^sql\s*', '', sql) # Remove "sql" no início
        sql = re.sub(r'["`]', '', sql) # Remove aspas
        sql = re.sub(r'```.*?\n', '', sql) # Remove blocos de código markdown
        sql = re.sub(r'```', '', sql) # Remove restante de markdown
        
        # Garante que termina com ponto e vírgula
        if not sql.endswith(';'):
            sql = sql + ';'
        
        # Remove espaços extras
        sql = ' '.join(sql.split())
        
        console.log(f"[bold cyan]SQL gerado[/]: {sql}")
        return sql
        
    except Exception as e:
        console.print(f"❌ Erro na tradução: {e}", style="bold red")
        return ""

def processar_resultado(resultado: CallToolResult) -> list:
    """Processa o resultado retornado pela ferramenta (Mantido)"""
    try:
        if (hasattr(resultado, 'raw_output') and 
            isinstance(resultado.raw_output, CallToolResult)):
            
            call_result = resultado.raw_output
            times = []
            
            if call_result.content:
                for item in call_result.content:
                    if hasattr(item, 'text'):
                        try:
                            # A ferramenta retorna uma lista JSON, então carregamos a lista
                            dados = json.loads(item.text)
                            # Se for uma lista, estendemos
                            if isinstance(dados, list):
                                times.extend(dados)
                            # Se for um único dicionário (ou falha na lista), adicionamos.
                            else:
                                times.append(dados)

                        except json.JSONDecodeError:
                            pass
            
            return times
            
        return []
        
    except Exception as e:
        console.print(f"❌ Erro ao processar resultado: {e}", style="bold red")
        return []

def _render_tabela_times(times: list[dict], titulo: str | None = None) -> None:
    # Esta função é apenas para o console, mantida mas não usada pelo bot
    pass
    
# --- FUNÇÃO DE TRANSCRIÇÃO WHISPER ---

def whisper_transcribe(filepath: str, model_name="small") -> str:
    """
    Função para realizar ASR em um arquivo de áudio. (Mantido)
    """
    try:
        # Nota: O Whisper lida com arquivos OGG nativamente se o FFmpeg/dependências
        # estiverem corretamente instalados no ambiente.
        model = whisper.load_model(model_name)
        result = model.transcribe(filepath, language="pt") # Assume português
        return result["text"]
    except Exception as e:
        console.print(f"❌ Erro na transcrição Whisper: {e}", style="bold red")
        # Se você tiver problemas aqui, o erro pode ser a falta de dependências do Whisper 
        # para decodificar OGG (como FFmpeg/opus-tools/etc).
        return f"❌ Erro ao transcrever: {e}"

# --- NOVO: FUNÇÃO DE FORMATAÇÃO PARA TEXTO SIMPLES (Mantido) ---

def formatar_texto_simples_para_telegram(data: list, pergunta: str) -> str:
    """Converte lista de dicionários (item único) em uma resposta formatada em Markdown V2. (Mantido)"""
    if not data or not isinstance(data[0], dict):
        return "Nenhum dado encontrado."
    
    primeiro_item = data[0]
    
    # Inicia a resposta
    output = f"🎯 *Resultado para:* _{pergunta}_\n\n"
    
    for key, value in primeiro_item.items():
        # Formata a chave para leitura (ex: saldo_gols -> Saldo Gols)
        display_key = key.replace('_', ' ').title()
        # Usa Markdown V2: *Negrito* e `Monospaço`
        output += f"• *{display_key}:* `{value}`\n"
        
    return output


# --- FUNÇÃO DE FORMATAÇÃO PARA TABELA (para resultados complexos) (Mantido) ---

def formatar_tabela_para_telegram(data: list) -> str:
    """Converte lista de dicionários em uma string formatada em Markdown V2 (bloco de código). (Mantido)"""
    if not data or not isinstance(data[0], dict):
        return "Nenhum dado para exibir."
    
    # Define os cabeçalhos das colunas
    headers = ["Nome", "UF", "Pts", "V", "E", "D", "SG"]
    
    data_lines = []
    for row in data:
        # Pega as colunas relevantes e formata para alinhamento em monospaço
        nome = str(row.get("nome", ""))[:10].ljust(10)
        estado = str(row.get("estado", "")).ljust(2)
        pontos = str(row.get("pontos", 0)).rjust(3)
        vitorias = str(row.get("vitorias", 0)).rjust(1)
        empates = str(row.get("empates", 0)).rjust(1)
        derrotas = str(row.get("derrotas", 0)).rjust(1)
        saldo_gols = str(row.get("saldo_gols", 0)).rjust(2)
        
        line = f"{nome} | {estado} | {pontos} | {vitorias} | {empates} | {derrotas} | {saldo_gols}"
        data_lines.append(line)

    # Cria a tabela em formato de bloco de código Markdown (Markdown V2)
    table_str = "```\n"
    table_str += " | ".join(headers) + "\n"
    table_str += "-|-".join(["-" * len(h) for h in headers]) + "\n"
    table_str += "\n".join(data_lines)
    table_str += "\n```"
    return table_str

# --- LÓGICA PRINCIPAL ASSÍNCRONA DO BOT (COM VISUALIZAÇÃO DINÂMICA) (Mantido) ---

async def processar_pergunta_assincrona(pergunta: str, chat_id: int):
    """
    Encapsula toda a lógica de LLM/SQL e envia os resultados de volta para o Telegram. (Mantido)
    """
    global ler_dados_tool, adicionar_dados_tool

    if ler_dados_tool is None or adicionar_dados_tool is None:
        await bot.send_message(chat_id, "❌ Erro de inicialização: As ferramentas do MCP não foram carregadas.")
        return
    
    await bot.send_message(chat_id, f"Pergunta recebida: *{pergunta}*")
    await bot.send_message(chat_id, "🔄 Traduzindo para SQL...", disable_notification=True)

    try:
        # 1. Tradução para SQL
        query_sql = await traduzir_para_sql(pergunta)
        
        if not query_sql:
            await bot.send_message(chat_id, "❌ Não foi possível traduzir a pergunta para uma query SQL válida. Tente ser mais específico.")
            return

        await bot.send_message(chat_id, f"📝 Query SQL gerada:\n`{query_sql}`", disable_notification=True)
        query_sql = query_sql.strip()

        # 2. Execução da Query
        if query_sql.upper().startswith('INSERT'):
            # Executa a query INSERT (Lógica mantida)
            await bot.send_message(chat_id, "⚡ Executando inserção...", disable_notification=True)
            resultado: CallToolResult = await adicionar_dados_tool.acall(query=query_sql)
            
            response_text = "Operação concluída. Detalhes: "
            if (hasattr(resultado, 'raw_output') and 
                isinstance(resultado.raw_output, CallToolResult) and 
                resultado.raw_output.content and 
                hasattr(resultado.raw_output.content[0], 'text')):
                response_text += resultado.raw_output.content[0].text
            else:
                response_text += "Resposta da ferramenta não formatada."
            
            await bot.send_message(chat_id, f"✅ {response_text}")
            
        else:
            # Executa a query SELECT
            await bot.send_message(chat_id, "⚡ Executando consulta...", disable_notification=True)
            resultado: CallToolResult = await ler_dados_tool.acall(query=query_sql)
            times = processar_resultado(resultado)
            
            # 3. Exibe os resultados com Lógica Dinâmica
            if times:
                primeiro_item = times[0]
                num_linhas = len(times)
                # Garante que é um dicionário antes de contar colunas
                num_colunas = len(primeiro_item) if primeiro_item and isinstance(primeiro_item, dict) else 0

                # **LÓGICA DINÂMICA:**
                # Critério: 1 linha E 3 ou menos colunas (Resposta pontual)
                if num_linhas == 1 and num_colunas <= 3:
                    # Formato de Texto Simples
                    output_markdown = formatar_texto_simples_para_telegram(times, pergunta)
                else:
                    # Formato de Tabela (Para classificações ou resultados complexos)
                    output_markdown = formatar_tabela_para_telegram(times)
                    
                await bot.send_message(chat_id, output_markdown)
            else:
                await bot.send_message(chat_id, "📭 Nenhum resultado encontrado. Verifique a query ou se o time existe no banco.")
        
    except Exception as e:
        await bot.send_message(chat_id, f"❌ Erro durante o processamento:\n`{e}`")


# --- HANDLERS DO TELEGRAM ---

# Handler para mensagens de texto (Mantido)
@bot.message_handler(func=lambda message: True)
async def handle_text(message):
    if message.text:
        await processar_pergunta_assincrona(message.text, message.chat.id)

# Handler para mensagens de voz (SIMPLIFICADO)
@bot.message_handler(content_types=['voice'])
async def handle_voice(message):
    await bot.send_message(message.chat.id, "🎤 Mensagem de voz recebida. Transcrevendo...")
    
    # Agora só precisamos do caminho do arquivo OGG
    temp_file_path = None 
    
    try:
        # 1. Obtém o caminho do arquivo no servidor Telegram
        file_info = await bot.get_file(message.voice.file_id)
        
        # 2. Cria e baixa o arquivo de áudio OGG temporariamente (como antes)
        # O Telegram envia voz como OGG Opus, que o Whisper aceita.
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_audio_file:
            temp_file_path = temp_audio_file.name
            
        downloaded_file = await bot.download_file(file_info.file_path)
        
        with open(temp_file_path, 'wb') as f:
            f.write(downloaded_file)
        
        # Log para confirmar que o arquivo OGG foi salvo localmente
        await bot.send_message(message.chat.id, f"💾 Áudio salvo localmente como OGG: `{temp_file_path}`", disable_notification=True)

        # 3. Transcreve o áudio (diretamente do OGG)
        transcribed_text = whisper_transcribe(temp_file_path)

        await bot.send_message(message.chat.id, f"✅ *Transcrição concluída:*\n_{transcribed_text}_")
        
        # 4. Processa a pergunta transcrita
        await processar_pergunta_assincrona(transcribed_text, message.chat.id)

    except Exception as e:
        await bot.send_message(message.chat.id, f"❌ Erro no processamento de voz:\n`{e}`")
    finally:
        # 5. Limpa o arquivo temporário
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            console.log(f"[bold green]Limpo:[/]: {temp_file_path}")

# --- FUNÇÃO PRINCIPAL (Mantida) ---

async def main():
    """
    Função principal que carrega as ferramentas e inicia o polling do bot. (Mantido)
    """
    global ler_dados_tool, adicionar_dados_tool
    
    console.rule("⚽ [bold green]Assistente do Brasileirão Telegram Bot[/]", style="green")
    
    try:
        # ⚠️ CORREÇÃO CRÍTICA APLICADA: Corrigido o endpoint para o nome do MCP
        # Isso resolve o erro '404 Not Found' que você teve anteriormente.
        mcp_client = BasicMCPClient("http://127.0.0.1:8000/sse")
        mcp_spec = McpToolSpec(client=mcp_client)
        
        # Carregar as ferramentas de forma assíncrona
        ferramentas = await mcp_spec.to_tool_list_async()
        
        # Atribuir às variáveis globais
        for tool in ferramentas:
            if tool.metadata.name == "ler_dados":
                ler_dados_tool = tool
            elif tool.metadata.name == "adicionar_dados":
                adicionar_dados_tool = tool
        
        if not ler_dados_tool or not adicionar_dados_tool:
            raise Exception("Ferramentas 'ler_dados' ou 'adicionar_dados' não encontradas!")

        Settings.tools = ferramentas # Define as ferramentas no contexto do LlamaIndex
        
        console.print(Panel.fit("✅ Ferramentas MCP carregadas com sucesso.", border_style="green", title="MCP"))

    except Exception as e:
        console.print(Panel.fit(f"❌ Erro ao carregar ferramentas MCP: {e}\nCertifique-se de que o 'server.py' está rodando.", border_style="red", title="Erro Crítico"))
        return

    # Inicia o bot em modo de 'polling'
    try:
        console.print(Panel.fit(f"🚀 Bot inicializado! Procure por @seu_bot_name no Telegram.", border_style="green", title="Pronto"))
        await bot.polling(none_stop=True)
    except Exception as e:
        console.print(f"❌ Erro no polling do bot: {e}", style="bold red")

if __name__ == "__main__":
    asyncio.run(main())