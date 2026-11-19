
"""
CEREBRO 2 - META (Llama via Groq)
Usado por: Programacao
Faz: criar codigo por pastas, arquivo por arquivo, sem modificar antigos
Chave no Render: GROQ_API_KEY - essa e a chave da Meta, que mora no Groq
Porta certa: api.groq.com
"""
import os, requests

def chamar_meta(pergunta):
    chave = os.getenv("GROQ_API_KEY", "").strip()
    if not chave:
        return "[META] Sem chave. Coloca GROQ_API_KEY no Render."
    modelo = os.getenv("META_MODEL", "llama-3.1-8b-instant")
    url = "https://api.groq.com/openai/v1/chat/completions"
    cabecalho = {"Authorization": f"Bearer {chave}", "Content-Type": "application/json"}
    corpo = {
        "model": modelo,
        "messages": [
            {"role": "system", "content": "Voce e a Programacao do Nexus Core. Responda em portugues simples, com codigo separado por pastas, arquivo por arquivo, sem modificar arquivos antigos."},
            {"role": "user", "content": pergunta}
        ],
        "temperature": 0.3
    }
    r = requests.post(url, headers=cabecalho, json=corpo, timeout=30)
    if r.status_code != 200:
        raise Exception(f"Meta via Groq erro {r.status_code}: {r.text[:300]}")
    dados = r.json()
    return dados["choices"][0]["message"]["content"]

if __name__ == "__main__":
    print(chamar_meta("Crie o index.html de um app de lista de tarefas"))
