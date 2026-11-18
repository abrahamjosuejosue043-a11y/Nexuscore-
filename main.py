# main.py - NEXUS CORE - A PONTE QUE VINCULA TUDO - V3
# Vincula:
# - frontend/index.html (tela salva - sem emoji, sofisticado, mic escondido, fundo IA)
# - backend/ai_brain.py (cerebro V3 salvo - raciocinio 6 passos, livre arbitrio altissimo, Orion diretoria, Forja codigo, Lia imagem tempo real, backup Gemini, perfil CEO)
# - backend/orchestrator.py (o que comanda o cerebro V3 salvo - comandar_cerebro liga tudo)
# - backend/email_service.py (e-mail - Orion le primeiro, analisa, passa para time)
# - backend/voice_service.py (voz - ElevenLabs principal, Cartesia reserva)
# Objetivo principal: ajudar no desenvolvimento de aplicativos.
# Nunca da erro 500. Sempre responde 200 com explicacao.
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, time

app = FastAPI(title="NEXUS CORE")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- Importa o CEREBRO V3 - tenta 2 jeitos para nao cair no simples a toa ---
_ERRO_CEREBRO = ""
try:
    from backend.ai_brain import pensar, testar_ias, criar_ordem_servico, analisar_email_detalhado_brain, _BACKUP_GEMINI, _PERFIL_CEO
except Exception as e1:
    print("ai_brain falhou no 1o jeito, tentando 2o jeito:", e1)
    try:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
        from ai_brain import pensar, testar_ias, criar_ordem_servico, analisar_email_detalhado_brain, _BACKUP_GEMINI, _PERFIL_CEO
    except Exception as e2:
        print("ai_brain falhou nos 2 jeitos, usando simples:", e2)
        _ERRO_CEREBRO = str(e2)[:200]
        _BACKUP_GEMINI = []
        _PERFIL_CEO = {"nome": "Josue", "cargo": "CEO - Innova XR"}
        async def testar_ias():
            return {"meta": f"ERRO IMPORT CEREBRO: {_ERRO_CEREBRO} - veja log do Render", "gemini": f"ERRO IMPORT CEREBRO: {_ERRO_CEREBRO} - veja log do Render"}
    async def pensar(quem, mensagem, historico=None):
        m = (mensagem or "").lower().strip()
        if m in ["oi", "oii", "ola"]:
            return {"quem": quem, "texto": "Oi, Senhor Josue! Estou aqui, online e pronto.", "fonte": "simples", "tempo_ms": 5}
        return {"quem": quem, "texto": "Estou online, Senhor Josue. Pergunte de novo.", "fonte": "simples", "tempo_ms": 10}
    def criar_ordem_servico(pedido, quem_pediu="Josue"):
        return {"ok": True, "texto": f"Ordem criada para: {pedido}", "ordem": {"numero": 1, "pedido": pedido}}
    def analisar_email_detalhado_brain(texto, assunto="", de=""):
        return {"ok": True, "resumo": f"Analise: {texto[:200]}", "prioridade": "NORMAL"}

# --- Importa o ORQUESTRADOR V3 - o que comanda o cerebro ---
try:
    from backend.orchestrator import criar_projeto_estrutura, detectar_projeto, comandar_cerebro, decidir_quem_fala
except Exception as e:
    print("orchestrator falhou, usando simples:", e)
    def detectar_projeto(m): return False
    def decidir_quem_fala(m): return "ORION"
    def comandar_cerebro(m):
        return {"quem": "ORION", "acao": "conversar", "detalhes": {}, "voz_principal": "elevenlabs"}
    def criar_projeto_estrutura(p, quem="FORJA"): return {"tipo": "projeto", "arquivos": {}}

# --- Importa E-MAIL ---
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

# --- Importa VOZ - ElevenLabs principal ---
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
class OrdemIn(BaseModel):
    pedido: str = ""
    quem: str = "Josue"

HIST = []

@app.get("/")
async def home():
    p = "frontend/index.html"
    if os.path.exists(p):
        return FileResponse(p)
    return {"status": "NEXUS CORE online"}

@app.get("/api/ai/teste")
async def ai_teste():
    try:
        return await testar_ias()
    except Exception as e:
        return {"meta": f"Erro teste: {e}", "gemini": "Erro teste"}

@app.get("/api/ping")
async def ping():
    return {"ok": True, "status": "acordado"}

@app.get("/api/status")
async def status():
    meta = bool((os.getenv("META_AI_API_KEY", "") or "").strip())
    gemini = bool((os.getenv("GEMINI_API_KEY", "") or "").strip())
    eleven = bool((os.getenv("ELEVENLABS_API_KEY", "") or "").strip())
    cartesia = bool((os.getenv("CARTESIA_API_KEY", "") or "").strip())
    meta_url = (os.getenv("META_AI_API_URL", "") or "").strip()
    return {"meta": meta, "gemini": gemini, "elevenlabs": eleven, "cartesia": cartesia,
            "meta_url_ok": meta_url.endswith("completions") or meta_url == "",
            "meta_url": meta_url,
            "voz_ativa": "elevenlabs" if eleven else ("cartesia" if cartesia else "navegador"),
            "voz_principal": "elevenlabs",
            "objetivo": "ajudar no desenvolvimento de aplicativos",
            "backup_total": len(_BACKUP_GEMINI),
            "perfil_ceo": _PERFIL_CEO.get("nome", "Josue") if isinstance(_PERFIL_CEO, dict) else "Josue"}

@app.post("/api/chat")
async def chat(d: ChatIn):
    inicio = time.time()
    try:
        # PASSO 1: ORQUESTRADOR comanda - decide quem fala e o que fazer
        try:
            plano = comandar_cerebro(d.mensagem)
            quem_certo = plano.get("quem", d.quem)
            acao = plano.get("acao", "conversar")
        except Exception:
            plano = {"quem": d.quem, "acao": "conversar"}
            quem_certo = d.quem
            acao = "conversar"
        # PASSO 2: Se for projeto, FORJA cria por pastas - via orquestrador
        if acao == "criar_projeto":
            try:
                proj = criar_projeto_estrutura(d.mensagem, quem_certo)
                texto = "Pronto, Senhor Josue. Criei o projeto em pastas separadas, sem mexer no resto.\n\nPastas: frontend/ (visual), backend/ (cerebro), docs/ (explicacao)\n\nArquivos criados:\n" + "\n".join([f"- {k}" for k in proj["arquivos"].keys()]) + "\n\nQuer que eu mostre o codigo de qual arquivo primeiro? frontend/index.html ou backend/main.py?"
                return {"quem": quem_certo, "texto": texto, "fonte": "projeto-pastas-orquestrador", "tempo_ms": int((time.time() - inicio) * 1000), "projeto": proj, "plano": plano, "voz_principal": "elevenlabs"}
            except Exception:
                pass
        # PASSO 3: Se for ordem de servico, ORION diretoria gera
        if acao == "ordem_servico":
            try:
                ordem = criar_ordem_servico(d.mensagem, "Josue - CEO")
                return {"quem": "ORION", "texto": ordem["texto"], "fonte": "ordem-servico-orion", "tempo_ms": int((time.time() - inicio) * 1000), "ordem": ordem.get("ordem"), "plano": plano, "voz_principal": "elevenlabs"}
            except Exception:
                pass
        # PASSO 4: Se for e-mail para analisar, ORION analisa detalhadamente
        if acao == "analisar_email":
            try:
                analise = analisar_email_detalhado_brain(d.mensagem, "E-mail pedido pelo CEO", "CEO")
                return {"quem": "ORION", "texto": analise["resumo"], "fonte": "analise-email-orion", "tempo_ms": int((time.time() - inicio) * 1000), "plano": plano, "voz_principal": "elevenlabs"}
            except Exception:
                pass
        # PASSO 5: Se for imagem, LIA - avisa que vai gerar em tempo real
        if acao == "gerar_imagem":
            # Deixa o cerebro responder, mas ja com o plano da Lia
            pass
        # PASSO 6: CEREBRO pensa - com quem certo do orquestrador
        r = await pensar(quem_certo, d.mensagem, HIST)
        try:
            HIST.append({"role": "user", "content": d.mensagem})
            HIST.append({"role": "assistant", "content": r["texto"]})
            if len(HIST) > 24:
                HIST.pop(0)
                HIST.pop(0)
        except Exception:
            pass
        r["tempo_ms"] = int((time.time() - inicio) * 1000)
        r["plano"] = plano
        r["voz_principal"] = "elevenlabs"
        return r
    except Exception as e:
        return {"quem": d.quem, "texto": f"Estou aqui, Senhor Josue. O servidor esta ligado, mas o cerebro travou por um instante. Erro: {str(e)[:100]}. Tente de novo em 10 segundos que eu respondo.", "fonte": "emergencia-main", "tempo_ms": int((time.time() - inicio) * 1000)}

@app.post("/api/projeto/criar")
async def projeto_criar(d: ProjetoIn):
    try:
        return criar_projeto_estrutura(d.pedido, d.quem)
    except Exception as e:
        return {"tipo": "projeto", "arquivos": {}, "erro": str(e)}

@app.post("/api/ordem/criar")
async def ordem_criar(d: OrdemIn):
    # ORION diretoria gera ordem de servico
    try:
        ordem = criar_ordem_servico(d.pedido, d.quem or "Josue - CEO")
        return {"ok": True, "ordem": ordem.get("ordem"), "texto": ordem["texto"]}
    except Exception as e:
        return {"ok": False, "erro": str(e)}

@app.post("/api/cerebro/comandar")
async def cerebro_comandar(d: ChatIn):
    # Mostra o plano do orquestrador - para voce ver quem ele mandou fazer o que
    try:
        plano = comandar_cerebro(d.mensagem)
        return {"ok": True, "plano": plano}
    except Exception as e:
        return {"ok": False, "erro": str(e)}

@app.get("/api/backup/listar")
async def backup_listar():
    # Backup Gemini - tudo salvo
    try:
        return {"total": len(_BACKUP_GEMINI), "backup": _BACKUP_GEMINI[-50:]}
    except Exception:
        return {"total": 0, "backup": []}

@app.get("/api/perfil/ceo")
async def perfil_ceo():
    try:
        return {"ok": True, "perfil": _PERFIL_CEO}
    except Exception:
        return {"ok": False, "perfil": {"nome": "Josue"}}

@app.post("/api/reuniao/pedir-palavra")
async def pedir_palavra(d: PalavraIn):
    # Liga com a fila do cerebro
    try:
        from backend.ai_brain import pedir_a_palavra
        return pedir_a_palavra(d.quem)
    except Exception:
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
        return {"emails": ler_ideias_novas()}
    except Exception as e:
        print("Erro listar email:", e)
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
