
"""
CEREBRO 1 - GEMINI (Google)
Usado por: Diretoria e Publicidade
Faz: organizar, resumir, criar OS, criar nome, slogan e campanha
Chave no Render: GEMINI_API_KEY - nunca cola a chave aqui no codigo
Porta certa: generativelanguage.googleapis.com
"""
import os, requests

def chamar_gemini(pergunta):
    chave = os.getenv("GEMINI_API_KEY", "").strip()
    if not chave:
        return "[GEMINI] Sem chave. Coloca GEMINI_API_KEY no Render."
    modelo = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={chave}"
    corpo = {"contents": [{"parts": [{"text": pergunta}]}]}
    r = requests.post(url, json=corpo, timeout=30)
    if r.status_code != 200:
        raise Exception(f"Gemini erro {r.status_code}: {r.text[:300]}")
    dados = r.json()
    try:
        return dados["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return str(dados)[:1000]

if __name__ == "__main__":
    print(chamar_gemini("Crie uma Ordem de Servico para um app de lista de tarefas"))
