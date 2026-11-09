import os
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
import google.genai as genai

# Inicialização do FastAPI
app = FastAPI(title="Nexus Core", version="1.0.0")

# Configuração do cliente Google Gemini
# Certifique-se de que GEMINI_API_KEY está configurada no painel de ambiente do Render
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Definição dos Agentes e suas personas estratégicas
AGENTES = {
    "engenharia": {
        "nome": "Atlas",
        "papel": "Arquiteto de Software & Engenheiro Sênior",
        "temperamento": "Pragmático, técnico, focado em escalabilidade, arquitetura limpa e robustez de código."
    },
    "marketing": {
        "nome": "Lyra",
        "papel": "Estrategista de Marketing & Crescimento",
        "temperamento": "Criativa, analítica de mercado, focada em conversão, engajamento e posicionamento de marca."
    },
    "financeiro": {
        "nome": "Chronos",
        "papel": "Analista Financeiro & Gestor de Riscos",
        "temperamento": "Conservador, focado em margens, custos, viabilidade econômica e ROI a longo prazo."
    }
}

# Interface Visual Sofisticada (Dark Mode Profissional, Responsiva e Moderna)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nexus Core - Central de Inteligência Multi-Agente</title>
    <style>
        :root {
            --bg-primary: #090d16;
            --bg-secondary: #111827;
            --bg-card: #1f2937;
            --accent-color: #38bdf8;
            --accent-hover: #0ea5e9;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --border-color: #374151;
            --success-color: #10b981;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background-color: var(--bg-primary); color: var(--text-main); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }
        .container { width: 100%; max-width: 520px; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 16px; padding: 36px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5); }
        .logo-area { text-align: center; margin-bottom: 28px; }
        .logo-area h1 { font-size: 1.75rem; font-weight: 700; color: var(--text-main); letter-spacing: -0.5px; }
        .logo-area p { font-size: 0.9rem; color: var(--text-muted); margin-top: 6px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; font-size: 0.875rem; font-weight: 500; margin-bottom: 8px; color: var(--text-muted); }
        input, select, textarea { width: 100%; padding: 12px 16px; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-main); font-size: 0.95rem; transition: border-color 0.2s; }
        input:focus, select:focus, textarea:focus { outline: none; border-color: var(--accent-color); }
        button { width: 100%; padding: 14px; background: var(--accent-color); color: var(--bg-primary); border: none; border-radius: 8px; font-weight: 600; font-size: 1rem; cursor: pointer; transition: background 0.2s; margin-top: 10px; }
        button:hover { background: var(--accent-hover); }
        .status-badge { display: inline-flex; align-items: center; gap: 8px; font-size: 0.75rem; color: var(--success-color); background: rgba(16, 185, 129, 0.1); padding: 6px 12px; border-radius: 20px; margin-bottom: 20px; border: 1px solid rgba(16, 185, 129, 0.2); }
        .status-dot { width: 8px; height: 8px; background: var(--success-color); border-radius: 50%; box-shadow: 0 0 8px var(--success-color); }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo-area">
            <div class="status-badge"><span class="status-dot"></span> Sistemas Operacionais Online</div>
            <h1>Nexus Core</h1>
            <p>Plataforma de Decisão Assistida por IA</p>
        </div>
        <form action="/auth" method="POST">
            <div class="form-group">
                <label for="email">E-mail Corporativo</label>
                <input type="email" id="email" name="email" value="conselho@nexuscore.com" required>
            </div>
            <div class="form-group">
                <label for="senha">Chave / Senha de Acesso</label>
                <input type="password" id="senha" name="senha" value="********" required>
            </div>
            <button type="submit">Entrar na Plataforma</button>
        </form>
    </div>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home():
    """Retorna a interface principal de autenticação estilizada."""
    return HTML_TEMPLATE

@app.post("/auth", response_class=HTMLResponse)
async def autenticar(email: str = Form(...), senha: str = Form(...)):
    """Processa o login e exibe o painel de comando interativo dos Agentes com suporte a prompt e voz/texto."""
    token_simulado = "jwt-token-simulado-nexus-core-secured"
    
    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Nexus Core - Painel de Controle Multi-Agente</title>
        <style>
            :root {{
                --bg-primary: #090d16;
                --bg-secondary: #111827;
                --bg-card: #1f2937;
                --accent-color: #38bdf8;
                --accent-hover: #0ea5e9;
                --text-main: #f3f4f6;
                --text-muted: #9ca3af;
                --border-color: #374151;
                --success-color: #10b981;
            }}
            * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }}
            body {{ background-color: var(--bg-primary); color: var(--text-main); padding: 30px; display: flex; justify-content: center; }}
            .dashboard {{ width: 100%; max-width: 800px; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 16px; padding: 32px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5); }}
            h2 {{ color: var(--accent-color); margin-bottom: 8px; font-size: 1.5rem; }}
            .welcome-info {{ font-size: 0.9rem; color: var(--text-muted); margin-bottom: 24px; }}
            .form-group {{ margin-bottom: 20px; }}
            label {{ display: block; font-size: 0.875rem; font-weight: 500; margin-bottom: 8px; color: var(--text-muted); }}
            select, textarea {{ width: 100%; padding: 12px 16px; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-main); font-size: 0.95rem; }}
            textarea {{ resize: vertical; min-height: 100px; }}
            select:focus, textarea:focus {{ outline: none; border-color: var(--accent-color); }}
            button {{ padding: 12px 24px; background: var(--accent-color); color: var(--bg-primary); border: none; border-radius: 8px; font-weight: 600; cursor: pointer; transition: background 0.2s; }}
            button:hover {{ background: var(--accent-hover); }}
            .actions {{ display: flex; gap: 12px; align-items: center; }}
            .mic-btn {{ background: #ef4444; color: #fff; display: flex; align-items: center; justify-content: center; width: 48px; height: 48px; border-radius: 8px; border: none; cursor: pointer; }}
            .mic-btn:hover {{ background: #dc2626; }}
            .back-link {{ display: inline-block; margin-top: 24px; color: var(--accent-color); text-decoration: none; font-size: 0.9rem; }}
            .back-link:hover {{ text-decoration: underline; }}
        </style>
        <script>
            function gravarVoz() {{
                if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {{
                    alert('Seu navegador não suporta reconhecimento de voz direto. Digite no campo.');
                    return;
                }}
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                const recognition = new SpeechRecognition();
                recognition.lang = 'pt-BR';
                recognition.start();
                
                const promptBox = document.getElementById('prompt');
                promptBox.placeholder = 'Ouvindo comando de voz...';
                
                recognition.onresult = function(event) {{
                    const speechToText = event.results[0][0].transcript;
                    promptBox.value = speechToText;
                    promptBox.placeholder = 'Digite ou use o microfone para enviar comandos...';
                }};
                
                recognition.onerror = function() {{
                    promptBox.placeholder = 'Erro no reconhecimento de voz. Tente novamente.';
                }};
            }}
        </script>
    </head>
    <body>
        <div class="dashboard">
            <h2>Painel de Comando Nexus Core</h2>
            <div class="welcome-info">Usuário autenticado: <strong>{email}</strong> | Token: <code>{token_simulado}</code></div>
            
            <form action="/api/executar" method="POST">
                <div class="form-group">
                    <label for="departamento">Selecionar Agente Especializado</label>
                    <select id="departamento" name="departamento">
                        <option value="engenharia">Atlas (Arquiteto de Software & Engenheiro Sênior)</option>
                        <option value="marketing">Lyra (Estrategista de Marketing & Crescimento)</option>
                        <option value="financeiro">Chronos (Analista Financeiro & Gestor de Riscos)</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="prompt">Comando ou Pergunta para o Agente</label>
                    <textarea id="prompt" name="prompt" placeholder="Digite ou use o botão de microfone para falar seu comando..." required></textarea>
                </div>
                
                <div class="actions">
                    <button type="submit" style="flex: 1;">Enviar Comando à IA</button>
                    <button type="button" class="mic-btn" onclick="gravarVoz()" title="Falar comando por voz">🎤</button>
                </div>
            </form>
            
            <a href="/" class="logout-btn back-link">&larr; Encerrar Sessão / Voltar ao Início</a>
        </div>
    </body>
    </html>
    """

@app.post("/api/executar", response_class=HTMLResponse)
async def processar_comando(departamento: str = Form(...), prompt: str = Form(...)):
    """Processa o comando enviado via interface ou voz utilizando o Google Gemini com a persona configurada."""
    if departamento not in AGENTES:
        raise HTTPException(status_code=404, detail="Agente não encontrado.")
    
    agente = AGENTES[departamento]
    system_instruction = f"Você é {agente['nome']}, atuando como {agente['papel']}. Diretriz de comportamento: {agente['temperamento']}."
    
    try:
        # Comunicação nativa e segura com o SDK google-genai
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config={
                'system_instruction': system_instruction,
                'temperature': 0.7,
            }
        )
        resposta_ia = response.text
    except Exception as e:
        resposta_ia = f"Erro ao processar a requisição com o motor de IA: {str(e)}"
        
    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Nexus Core - Resposta do Agente</title>
        <style>
            :root {{
                --bg-primary: #090d16;
                --bg-secondary: #111827;
                --bg-card: #1f2937;
                --accent-color: #38bdf8;
                --text-main: #f3f4f6;
                --text-muted: #9ca3af;
                --border-color: #374151;
            }}
            * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }}
            body {{ background-color: var(--bg-primary); color: var(--text-main); padding: 30px; display: flex; justify-content: center; }}
            .result-card {{ width: 100%; max-width: 800px; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 16px; padding: 32px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5); }}
            h2 {{ color: var(--accent-color); margin-bottom: 6px; font-size: 1.4rem; }}
            .meta-info {{ font-size: 0.85rem; color: var(--text-muted); margin-bottom: 20px; }}
            .response-box {{ background: var(--bg-card); border: 1px solid var(--border-color); padding: 20px; border-radius: 10px; line-height: 1.6; white-space: pre-wrap; font-size: 0.95rem; margin-bottom: 24px; }}
            .back-btn {{ display: inline-block; padding: 12px 24px; background: var(--accent-color); color: var(--bg-primary); border-radius: 8px; text-decoration: none; font-weight: 600; transition: background 0.2s; }}
            .back-btn:hover {{ background: #0ea5e9; }}
        </style>
    </head>
    <body>
        <div class="result-card">
            <h2>Resposta de {agente['nome']}</h2>
            <div class="meta-info">Papel: {agente['papel']} | Comando original: "{prompt}"</div>
            <div class="response-box">{resposta_ia}</div>
            <a href="/auth" class="back-btn">&larr; Fazer Novo Comando</a>
        </div>
    </body>
    </html>
    """
