# main.py - NEXUS CORE - A PROVA DE QUEDA - chat nunca da erro 500
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, time

app = FastAPI(title="NEXUS CORE")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Cada import separado - se um falhar, os outros continuam
try:
    from backend.ai_brain import pensar
except Exception as e:
    print("ai_brain falhou, usando simples:", e)
    async def pensar(quem, mensagem, historico=None):
        m = (mensagem or "").lower().strip()
        if m in ["oi", "oii", "ola"]:
            return {"quem": quem, "texto": "Oi, Senhor Josue! Estou aqui, online e pronto.", "fonte": "simples", "tempo_ms": 5}
        return {"quem": quem, "texto": "Estou online, Senhor Josue. Pergunte de novo.", "fonte": "simples", "tempo_ms": 10}

try:
    from backend.orchestrator import criar_projeto_estrutura, detectar_projeto
except Exception:
    def detectar_projeto(m): return False
    def criar_projeto_estrutura(p, quem="FORJA"): return {"tipo": "projeto", "arquivos": {}}

try:
    from backend.email_service import enviar_email, ler_ideias_novas, listar_emails_salvos, analisar_email_detalhado, repassar_para_time, enviar_email_interno, listar_email_interno, salvar_email_recebido
except Exception:
    def enviar_email(para, assunto, texto): return {"sucesso": False, "erro": "Email nao configurado"}
    def ler_ideias_novas(): return []
    def listar_emails_salvos(): return []
    def analisar_email_detalhado(id): return {"ok": False, "erro": "Email nao configurado"}
    def repassar_para_time(id, para): return {"ok": False, "erro": "Email nao configurado"}
    def enviar_email_interno(de, para, assunto, texto): return {"ok": True, "email": {"de": de, "para": para, "assunto": assunto, "texto": texto, "data_hora": "agora"}}
    def listar_email_interno(): return []
    def salvar_email_recebido(de, assunto, texto): return {"id": 1}

try:
    from backend.voice_service import gerar_voz, testar_voz
except Exception as e:
    print("voice_service falhou, usando navegador:", e)
    async def gerar_voz(quem, texto): return {"ok": False, "mensagem": "Voz externa off, usando navegador", "usar_navegador": True}
    async def testar_voz(): return {"ok": False, "mensagem": "Sem voz externa. O navegador fala."}

class ChatIn(BaseModel):
    quem: str = "ORION"
    mensagem: str = ""
class VozIn(BaseModel):
    quem: str = "ORION"
    texto: str = ""
class EmailIn(BaseModel):
    para: str = ""
    assunto: str = ""
    texto: str = ""
class PalavraIn(BaseModel):
    quem: str = "FORJA"
class AnalisarIn(BaseModel):
    id: str = ""
class RepassarIn(BaseModel):
    id: str = ""
    para: list = []
class InternoIn(BaseModel):
    de: str = "Josue"
    para: str = "ORION"
    assunto: str = ""
    texto: str = ""
class ProjetoIn(BaseModel):
    pedido: str = ""
    quem: str = "FORJA"

HIST = []

@app.get("/")
async def home():
    p = "frontend/index.html"
    if os.path.exists(p):
        return FileResponse(p)
    return {"status": "NEXUS CORE online"}

@app.get("/api/ping")
async def ping():
    # Para acordar o servidor - responde em 5ms, sem chamar IA
    return {"ok": True, "status": "acordado"}

@app.get("/api/status")
async def status():
    # Nunca trava - so le as chaves na hora
    meta = bool((os.getenv("META_AI_API_KEY", "") or "").strip())
    gemini = bool((os.getenv("GEMINI_API_KEY", "") or "").strip())
    eleven = bool((os.getenv("ELEVENLABS_API_KEY", "") or "").strip())
    cartesia = bool((os.getenv("CARTESIA_API_KEY", "") or "").strip())
    meta_url = (os.getenv("META_AI_API_URL", "") or "").strip()
    return {"meta": meta, "gemini": gemini, "elevenlabs": eleven, "cartesia": cartesia,
            "meta_url_ok": meta_url.endswith("completions") or meta_url == "",
            "meta_url": meta_url,
            "voz_ativa": "cartesia" if cartesia else ("elevenlabs" if eleven else "navegador"),
            "voz_principal": "cartesia"}

@app.post("/api/chat")
async def chat(d: ChatIn):
    inicio = time.time()
    # NUNCA deixa dar erro 500 - tudo dentro de try
    try:
        # Projeto? Responde com pastas
        try:
            if detectar_projeto(d.mensagem):
                proj = criar_projeto_estrutura(d.mensagem, d.quem)
                texto = "Pronto, Senhor Josue. Criei o projeto em pastas separadas, sem mexer no resto.\n\nPastas: frontend/ (visual), backend/ (cerebro), docs/ (explicacao)\n\nArquivos criados:\n" + "\n".join([f"- {k}" for k in proj["arquivos"].keys()]) + "\n\nQuer que eu mostre o codigo de qual arquivo primeiro? frontend/index.html ou backend/main.py?"
                return {"quem": d.quem, "texto": texto, "fonte": "projeto-pastas", "tempo_ms": int((time.time() - inicio) * 1000), "projeto": proj}
        except Exception:
            pass
        r = await pensar(d.quem, d.mensagem, HIST)
        try:
            HIST.append({"role": "user", "content": d.mensagem})
            HIST.append({"role": "assistant", "content": r["texto"]})
            if len(HIST) > 12:
                HIST.pop(0)
        except Exception:
            pass
        r["tempo_ms"] = int((time.time() - inicio) * 1000)
        return r
    except Exception as e:
        # Mesmo se tudo falhar, responde 200 com explicacao
        return {"quem": d.quem, "texto": f"Estou aqui, Senhor Josue. O servidor esta ligado, mas o cerebro travou por um instante. Erro: {str(e)[:100]}. Tente de novo em 10 segundos que eu respondo.", "fonte": "emergencia-main", "tempo_ms": int((time.time() - inicio) * 1000)}

@app.post("/api/projeto/criar")
async def projeto_criar(d: ProjetoIn):
    try:
        return criar_projeto_estrutura(d.pedido, d.quem)
    except Exception as e:
        return {"tipo": "projeto", "arquivos": {}, "erro": str(e)}

@app.post("/api/reuniao/pedir-palavra")
async def pedir_palavra(d: PalavraIn):
    return {"ok": True, "quem": d.quem, "mensagem": f"{d.quem} pediu a palavra. Orion vai passar."}

@app.post("/api/voz")
async def voz(d: VozIn):
    try:
        return await gerar_voz(d.quem, d.texto)
    except Exception as e:
        return {"ok": False, "mensagem": f"Voz falhou, usando navegador: {e}"}

@app.get("/api/elevenlabs/teste")
async def teste_eleven():
    try:
        return await testar_voz()
    except Exception as e:
        return {"ok": False, "mensagem": str(e)}

@app.get("/api/voz/teste")
async def teste_voz_novo():
    try:
        return await testar_voz()
    except Exception as e:
        return {"ok": False, "mensagem": str(e)}

@app.get("/api/email/ideias-novas")
async def ideias():
    try:
        return {"ideias": ler_ideias_novas()}
    except Exception:
        return {"ideias": []}

@app.post("/api/email/enviar")
async def email_enviar(d: EmailIn):
    para = d.para or os.getenv("MEU_EMAIL_PESSOAL", "")
    try:
        r = enviar_email(para, d.assunto or "NEXUS CORE - Relatorio", d.texto)
        return r
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}

@app.get("/api/email/listar")
async def email_listar():
    try:
        return {"emails": listar_emails_salvos()}
    except Exception:
        return {"emails": []}

@app.post("/api/email/analisar")
async def email_analisar(d: AnalisarIn):
    try:
        return analisar_email_detalhado(d.id)
    except Exception as e:
        return {"ok": False, "erro": str(e)}

@app.post("/api/email/repassar")
async def email_repassar(d: RepassarIn):
    try:
        return repassar_para_time(d.id, d.para)
    except Exception as e:
        return {"ok": False, "erro": str(e)}

@app.post("/api/email/interno/enviar")
async def email_interno_enviar(d: InternoIn):
    try:
        return enviar_email_interno(d.de, d.para, d.assunto, d.texto)
    except Exception as e:
        return {"ok": False, "erro": str(e)}

@app.get("/api/email/interno/listar")
async def email_interno_listar():
    try:
        return {"emails": listar_email_interno()}
    except Exception:
        return {"emails": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
