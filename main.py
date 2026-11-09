import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import google.generativeai as genai

# Configuração da API do Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

app = FastAPI(title="Nexus Core - IA Interface")

class PromptRequest(BaseModel):
    agent: str
    prompt: str

# HTML completo encapsulado corretamente dentro de string Python (evita o SyntaxError)
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nexus Core - Sala de Conferência IA</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        /* Estilos personalizados mantidos sem erro de sintaxe */
        ::-webkit-scrollbar {
            width: 6px;
        }
        ::-webkit-scrollbar-track {
            background: #0f172a;
        }
        ::-webkit-scrollbar-thumb {
            background: #334155;
            border-radius: 3px;
        }
        .speaking-glow {
            box-shadow: 0 0 20px rgba(59, 130, 246, 0.6);
            border-color: #3b82f6 !important;
        }
    </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col font-sans">
    <header class="border-b border-slate-800 bg-slate-900/50 px-6 py-4 flex items-center justify-between">
        <div class="flex items-center gap-3">
            <div class="w-3 h-3 rounded-full bg-emerald-500 animate-pulse"></div>
            <h1 class="text-xl font-bold tracking-tight bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
                Nexus Core - Sala de Conferência em Tempo Real
            </h1>
        </div>
        <div class="text-sm text-slate-400">Status: <span class="text-emerald-400">Online</span></div>
    </header>

    <main class="flex-1 p-6 flex flex-col gap-6 max-w-7xl mx-auto w-full">
        <!-- Grid de Agentes (Estilo Google Meet) -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1 min-h-[400px]">
            <div id="card-atlas" class="bg-slate-900 border border-slate-800 rounded-2xl p-6 flex flex-col justify-between relative overflow-hidden transition-all duration-300">
                <div class="flex items-center justify-between">
                    <span class="text-xs font-semibold px-2.5 py-1 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">Atlas</span>
                    <i data-lucide="cpu" class="w-5 h-5 text-blue-400"></i>
                </div>
                <div class="my-auto text-center py-8">
                    <div class="w-20 h-20 bg-blue-600/20 rounded-full mx-auto flex items-center justify-center border border-blue-500/30 mb-3">
                        <i data-lucide="code-2" class="w-10 h-10 text-blue-400"></i>
                    </div>
                    <h3 class="font-bold text-lg">Arquitetura & Código</h3>
                </div>
                <p class="text-xs text-slate-400 text-center">Modelo: Gemini 2.0 Flash</p>
            </div>

            <div id="card-chronos" class="bg-slate-900 border border-slate-800 rounded-2xl p-6 flex flex-col justify-between relative overflow-hidden transition-all duration-300">
                <div class="flex items-center justify-between">
                    <span class="text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Chronos</span>
                    <i data-lucide="shield-alert" class="w-5 h-5 text-emerald-400"></i>
                </div>
                <div class="my-auto text-center py-8">
                    <div class="w-20 h-20 bg-emerald-600/20 rounded-full mx-auto flex items-center justify-center border border-emerald-500/30 mb-3">
                        <i data-lucide="line-chart" class="w-10 h-10 text-emerald-400"></i>
                    </div>
                    <h3 class="font-bold text-lg">Análise de Riscos & Finanças</h3>
                </div>
                <p class="text-xs text-slate-400 text-center">Modelo: Gemini 2.0 Flash</p>
            </div>
        </div>

        <!-- Área de Comando -->
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row gap-4">
            <select id="agentSelect" class="bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="atlas">Atlas (Arquitetura)</option>
                <option value="chronos">Chronos (Finanças)</option>
            </select>
            <input type="text" id="promptInput" placeholder="Digite seu comando..." class="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500">
            <button onclick="sendCommand()" class="bg-blue-600 hover:bg-blue-500 text-white font-medium px-6 py-2 rounded-lg text-sm transition-colors flex items-center justify-center gap-2">
                <i data-lucide="send" class="w-4 h-4"></i> Enviar
            </button>
        </div>

        <!-- Output do Log -->
        <div id="outputLog" class="bg-slate-900/60 border border-slate-800 rounded-xl p-4 text-sm font-mono text-slate-300 min-h-[120px] max-h-[200px] overflow-y-auto">
            <p class="text-slate-500">> Aguardando comandos...</p>
        </div>
    </main>

    <script>
        lucide.createIcons();

        async function sendCommand() {
            const agent = document.getElementById('agentSelect').value;
            const prompt = document.getElementById('promptInput').value;
            const outputLog = document.getElementById('outputLog');

            if (!prompt.trim()) return;

            outputLog.innerHTML += `<p class="text-blue-400">> [Usuário -> ${agent.toUpperCase()}]: ${prompt}</p>`;
            document.getElementById('promptInput').value = '';

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ agent, prompt })
                });

                const data = await response.json();
                if (response.ok) {
                    outputLog.innerHTML += `<p class="text-emerald-400 font-sans my-1">> [${agent.toUpperCase()}]: ${data.response}</p>`;
                } else {
                    outputLog.innerHTML += `<p class="text-red-400">> Erro: ${data.detail || 'Falha ao processar'}</p>`;
                }
            } catch (err) {
                outputLog.innerHTML += `<p class="text-red-400">> Erro de conexão com a API</p>`;
            }
            outputLog.scrollTop = outputLog.scrollHeight;
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    return HTML_CONTENT

@app.post("/api/chat")
async def chat_endpoint(request: PromptRequest):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Chave de API do Gemini não configurada no servidor.")
    
    try:
        # Atualizado para o modelo suportado gemini-2.0-flash
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        system_context = f"Você é o agente {request.agent.upper()} atuando na plataforma Nexus Core. Responda de forma concisa e profissional."
        response = model.generate_content(f"{system_context}\n\nPergunta do usuário: {request.prompt}")
        
        return {"response": response.text}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
