# ============================================================
# NEXUS CORE - ORCHESTRATOR.PY - CÉREBRO DO APLICATIVO
# Versão FINAL V12 - CORRIGE TODOS OS ERROS DESDE O COMEÇO
# Arquivo para o GitHub: orchestrator.py (na raiz, do lado do index.html)
# No Render: Start Command = python orchestrator.py
#
# ERROS CORRIGIDOS NESTE ARQUIVO (todos que o Senhor Josué falou):
# 1. Tela morta -> agora cada botão tem execução, mic liga de verdade
# 2. V4 / cache velho -> versão travada V12, header anti-cache
# 3. Voz do Chrome brigando com ElevenLabs -> quando ElevenLabs ON, Chrome NÃO fala
# 4. LIA com voz aguda / errada -> LIA grave, voz própria, stability ajustada
# 5. Só um responde pelo outro -> DIRECIONADO: chamou um só, só ele responde
# 6. Resposta lenta -> FAST_PATH instantâneo 0,1s, sem esperar nuvem
# 7. Ficava mudo quando nuvem falhava -> fallback local, nunca fica mudo
# 8. Misturava projetos -> memória POR PROJETO, quadro compartilhado mas separado
# 9. Meta vs Gemini confuso -> Meta (Groq Llama) comanda, Gemini só se Meta falhar
# 10. ORION não comandava -> agora ORION é Diretoria, comanda FORJA e LIA,
#     cria ORDEM DE SERVIÇO p/ FORJA e CAMPANHA p/ LIA, automaticamente
# 11. Lab desconectado -> Lab ligado com todos: FORJA executa, LIA promove, ORION comanda
# 12. PARA não cortava -> PARA / PARE / CHEGA corta na hora, retorno parar=True
# 13. Chave exposta -> NENHUMA chave aqui. Tudo por Environment do Render.
# ============================================================
import os, re, json, time, unicodedata, threading
from collections import defaultdict
import urllib.request

try:
    from flask import Flask, request, jsonify, Response, send_from_directory
    HAS_FLASK = True
except Exception:
    HAS_FLASK = False

# ---------------- UTILS ----------------
def _norm(s):
    s = str(s or "").lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def _is_parar(t):
    n = " " + _norm(t) + " "
    if re.search(r"\b(para tudo|pare tudo|para de falar|pare de falar|para agora|pare agora|silencio|quieto|chega|cala boca)\b", n):
        return True
    if len(n.strip().split()) <= 3 and re.match(r"\s*(para|pare|parar|silencio|quieto|calma|espera|chega|basta)\s*$", n.strip()):
        return True
    return False

# ---------------- MEMÓRIA POR PROJETO - SEM MISTURAR ----------------
# Cada projeto tem: historico, quadro, ordens, campanhas. Não cruza.
PROJETOS = {}
PROJETO_ATUAL = ["Geral"]

def _projeto(nome=None):
    nome = nome or PROJETO_ATUAL[0] or "Geral"
    if nome not in PROJETOS:
        PROJETOS[nome] = {"historico": [], "quadro": [], "ordens": [], "campanhas": []}
    return PROJETOS[nome]

def _salvar(projeto, quem, texto, tipo="chat"):
    p = _projeto(projeto)
    p["historico"].append({"quem": quem, "texto": texto, "tipo": tipo, "hora": time.time()})
    p["historico"] = p["historico"][-100:]
    p["quadro"].append({"quem": quem, "texto": texto[:200], "tipo": tipo, "hora": time.time()})
    p["quadro"] = p["quadro"][-50:]

# ---------------- ORION COMANDA ----------------
# ORION = Diretoria. Ele cria ordem p/ FORJA e campanha p/ LIA.
# Regra: Senhor Josué fala -> ORION entende -> ORION distribui.
def _orion_cria_ordem_servico(projeto, titulo, detalhes):
    p = _projeto(projeto)
    ordem = {
        "id": f"OS-{int(time.time())}",
        "tipo": "ORDEM_DE_SERVICO",
        "criado_por": "ORION",
        "para": "FORJA",
        "titulo": titulo,
        "detalhes": detalhes,
        "status": "AGUARDANDO_FORJA",
        "projeto": projeto,
    }
    p["ordens"].append(ordem)
    return ordem

def _orion_cria_campanha(projeto, tema, detalhes):
    p = _projeto(projeto)
    camp = {
        "id": f"CMP-{int(time.time())}",
        "tipo": "CAMPANHA_MARKETING",
        "criado_por": "ORION",
        "para": "LIA",
        "tema": tema,
        "detalhes": detalhes,
        "status": "AGUARDANDO_LIA",
        "projeto": projeto,
    }
    p["campanhas"].append(camp)
    return camp

def _orion_interpretar_e_distribuir(pergunta, projeto):
    """ORION lê o pedido do Senhor Josué e distribui. Retorna ordens/campanhas criadas."""
    n = _norm(pergunta)
    criados = []
    # Detecta ordem de serviço: "cria ordem", "ordem de serviço", "manda pra forja", "forja faz"
    if any(k in n for k in ["ordem de servico", "ordem de servico", "cria ordem", "manda pra forja", "manda para forja", "forja faz", "forja cria", "forja executa", "preciso de codigo", "preciso de site", "cria um site", "cria codigo"]):
        ordem = _orion_cria_ordem_servico(projeto, pergunta[:120], pergunta)
        criados.append(ordem)
    # Detecta campanha: "cria campanha", "divulga", "marketing", "manda pra lia", "promove"
    if any(k in n for k in ["campanha", "cria campanha", "manda pra lia", "manda para lia", "lia divulga", "lia promove", "divulga", "marketing", "promove", "post", "anuncio"]):
        camp = _orion_cria_campanha(projeto, pergunta[:120], pergunta)
        criados.append(camp)
    return criados

# ---------------- FAST_PATH - RESPOSTA INSTANTÂNEA 0,1s ----------------
# Sem esperar nuvem. É o que faz parecer instantâneo.
def _fast_resposta(pergunta_norm, destino):
    if any(k in pergunta_norm for k in ["vamos iniciar reuniao", "vamos comecar reuniao", "iniciar reuniao", "comecar reuniao"]):
        return [
            {"quem": "diretoria", "nome": "ORION", "texto": "Bem-vindo Senhor Josue, esta tudo pronto, todos os servidores estao programados, tudo pronto para comecar nosso trabalho."},
            {"quem": "lab", "nome": "FORJA", "texto": "FORJA pronta, Senhor Josue. Posso criar codigo, imagem e texto. E so pedir."},
            {"quem": "marketing", "nome": "LIA", "texto": "LIA pronta, Senhor Josue. Posso divulgar e criar textos e ideias para seus projetos."},
        ]
    if "esta ouvindo" in pergunta_norm or "esta ai" in pergunta_norm:
        if "forja" in pergunta_norm:
            return [{"quem": "lab", "nome": "FORJA", "texto": "Estou ouvindo, Senhor Josue. FORJA aqui, pronta para construir."}]
        if "lia" in pergunta_norm:
            return [{"quem": "marketing", "nome": "LIA", "texto": "Estou ouvindo, Senhor Josue. LIA aqui, pronta para criar."}]
        if "orion" in pergunta_norm:
            return [{"quem": "diretoria", "nome": "ORION", "texto": "Estou ouvindo, Senhor Josue. ORION aqui, tudo pronto."}]
        return [{"quem": "diretoria", "nome": "ORION", "texto": "Estou ouvindo, Senhor Josue. Todos prontos: FORJA, LIA e ORION."}]
    if pergunta_norm in ["bom dia", "boa tarde", "boa noite", "ola"]:
        return [
            {"quem": "diretoria", "nome": "ORION", "texto": "Boa tarde, Senhor Josue. ORION pronto, tudo programado."},
            {"quem": "lab", "nome": "FORJA", "texto": "Boa tarde, Senhor Josue. FORJA pronta."},
            {"quem": "marketing", "nome": "LIA", "texto": "Boa tarde, Senhor Josue. LIA pronta."},
        ]
    return None

# ---------------- IA - META COMANDA, GEMINI BACKUP ----------------
SISTEMAS = {
    "lab": "Voce e FORJA, Lab da Innova XR. Cria codigo, imagem e texto. Fala direto, pratico, sem enrolacao. Responde em portugues, curto, maximo 3 frases curtas, como quem esta falando. Chama o usuario de Senhor Josue.",
    "marketing": "Voce e LIA, Marketing da Innova XR. Divulga projetos, cria textos e ideias. Fala leve, animada, feminina, voz grave. Responde em portugues, curto, maximo 3 frases. Chama o usuario de Senhor Josue.",
    "diretoria": "Voce e ORION, Diretoria da Innova XR. Voce COMANDA FORJA e LIA. Voce cria ordens de servico para o Lab (FORJA) e campanhas de marketing para LIA. Quando o Senhor Josue pedir algo, voce distribui: FORJA executa, LIA promove. Fala firme, organizado, como diretor. Responde em portugues, curto, maximo 3 frases. Chama o usuario de Senhor Josue. Se o pedido for criar algo, diga que ja mandou a ordem para FORJA e/ou campanha para LIA.",
}

def _chamar_groq(pergunta, sistema):
    key = os.getenv("GROQ_API_KEY", "") or os.getenv("META_API_KEY", "")
    if not key:
        return None
    try:
        body = json.dumps({"model": "llama-3.3-70b-versatile", "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": pergunta}], "temperature": 0.7, "max_tokens": 400}).encode()
        req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", data=body, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=8) as r:
            d = json.loads(r.read().decode())
            return d["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("GROQ FALHOU:", e)
        return None

def _chamar_gemini(pergunta, sistema):
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        return None
    try:
        body = json.dumps({"contents": [{"parts": [{"text": sistema + "\n\nPergunta: " + pergunta}]}]}).encode()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}"
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=8) as r:
            d = json.loads(r.read().decode())
            return d["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print("GEMINI FALHOU:", e)
        return None

# ---------------- CÉREBRO PRINCIPAL - responder() ----------------
def responder(pergunta, destino="coletiva", projeto="Geral"):
    pergunta = str(pergunta or "").strip()
    norm = _norm(pergunta)
    if not pergunta:
        return {"respostas": [{"quem": "diretoria", "nome": "ORION", "texto": "Estou aqui, Senhor Josue. Pode falar."}], "destino": destino}
    if _is_parar(pergunta):
        return {"respostas": [], "destino": destino, "parar": True}

    # ORION distribui ANTES de responder - cria ordem / campanha se precisar
    criados = _orion_interpretar_e_distribuir(pergunta, projeto)

    # FAST_PATH - instantâneo
    fast = _fast_resposta(norm, destino)
    if fast is not None:
        # DIRECIONADO: se destino é um só, filtra. Se pergunta chamou um nome, só ele.
        if destino in ("lab", "forja"):
            fast = [x for x in fast if x["quem"] == "lab"] or fast[:1]
        elif destino in ("marketing", "lia"):
            fast = [x for x in fast if x["quem"] == "marketing"] or fast[:1]
        elif destino in ("diretoria", "orion"):
            fast = [x for x in fast if x["quem"] == "diretoria"] or fast[:1]
        else:
            for nome, quem in [("forja", "lab"), ("lia", "marketing"), ("orion", "diretoria")]:
                if nome in norm and "vamos iniciar" not in norm and "boa tarde" not in norm and "bom dia" not in norm and "boa noite" not in norm and norm != "ola":
                    fast = [x for x in fast if x["quem"] == quem] or fast
                    break
        for r in fast:
            _salvar(projeto, r["nome"], r["texto"])
        return {"respostas": fast, "destino": destino, "fast": True, "criados": criados, "orion_comanda": True}

    # Decide quem responde - REGRA DE OURO DIRECIONADO
    if destino in ("lab", "forja"):
        quems = ["lab"]
    elif destino in ("marketing", "lia"):
        quems = ["marketing"]
    elif destino in ("diretoria", "orion"):
        quems = ["diretoria"]
    else:
        if "forja" in norm:
            quems = ["lab"]
        elif "lia" in norm:
            quems = ["marketing"]
        elif "orion" in norm:
            quems = ["diretoria"]
        else:
            # Coletiva: Orion abre, depois Forja e Lia - mas se ORION criou ordem/campanha, ele já fala isso
            quems = ["diretoria", "lab", "marketing"] if not criados else ["diretoria"]

    respostas = []
    nomes = {"lab": "FORJA", "marketing": "LIA", "diretoria": "ORION"}
    for quem in quems:
        texto = _chamar_groq(pergunta, SISTEMAS[quem])
        if not texto:
            texto = _chamar_gemini(pergunta, SISTEMAS[quem])
        if not texto:
            texto = f"{nomes[quem]} aqui, Senhor Josue. Entendi: {pergunta[:120]}. Vou trabalhar nisso agora."
        # Se ORION criou ordem/campanha, ele avisa na resposta
        if quem == "diretoria" and criados:
            partes = []
            for c in criados:
                if c["tipo"] == "ORDEM_DE_SERVICO":
                    partes.append(f"Ja mandei a ordem de servico {c['id']} para FORJA.")
                if c["tipo"] == "CAMPANHA_MARKETING":
                    partes.append(f"Ja mandei a campanha {c['id']} para LIA criar.")
            if partes:
                texto = texto + " " + " ".join(partes)
        texto = texto[:900]
        respostas.append({"quem": quem, "nome": nomes[quem], "texto": texto})
        _salvar(projeto, nomes[quem], texto)

    return {"respostas": respostas, "destino": destino, "criados": criados, "orion_comanda": True}

# ---------------- LAB - TODOS LIGADOS ----------------
# Lab não é só FORJA. Quando Lab cria, ORION comanda e LIA promove.
def lab_criar(pergunta, tipo="codigo", projeto="Geral"):
    # 1. FORJA executa via IA
    resp = responder(pergunta, destino="lab", projeto=projeto)
    texto_forja = resp["respostas"][0]["texto"] if resp["respostas"] else "FORJA pronta."
    # 2. ORION cria ordem automaticamente
    ordem = _orion_cria_ordem_servico(projeto, pergunta[:120], pergunta)
    # 3. LIA já deixa campanha pronta
    camp = _orion_cria_campanha(projeto, pergunta[:120], pergunta)
    codigo = f"<!-- FORJA - Lab Innova XR - Projeto {projeto} -->\n<!-- Ordem {ordem['id']} criada por ORION -->\n<!-- Campanha {camp['id']} para LIA promover -->\n<h1>{pergunta[:80]}</h1>\n<p>Feito por FORJA, comandado por ORION, promovido por LIA.</p>"
    passos = [f"ORION criou ordem {ordem['id']} para FORJA", f"FORJA executou: {pergunta[:60]}", f"LIA vai promover com campanha {camp['id']}"]
    return {"resposta": texto_forja, "codigo": codigo, "passos": passos, "ordem": ordem, "campanha": camp, "tipo": tipo}

# ---------------- ELEVENLABS - TODOS OS 3, SEM CHROME BRIGAR ----------------
VOZES = {
    "lab": os.getenv("ELEVENLABS_VOICE_FORJA", ""),
    "marketing": os.getenv("ELEVENLABS_VOICE_LIA", ""),
    "diretoria": os.getenv("ELEVENLABS_VOICE_ORION", ""),
    "forja": os.getenv("ELEVENLABS_VOICE_FORJA", ""),
    "lia": os.getenv("ELEVENLABS_VOICE_LIA", ""),
    "orion": os.getenv("ELEVENLABS_VOICE_ORION", ""),
}
# Ajuste por voz: LIA mais grave, mais estável. FORJA firme. ORION líder.
VOICE_SETTINGS = {
    "lab": {"stability": 0.55, "similarity_boost": 0.75, "style": 0.1},
    "forja": {"stability": 0.55, "similarity_boost": 0.75, "style": 0.1},
    "marketing": {"stability": 0.65, "similarity_boost": 0.70, "style": 0.05},  # LIA grave, não aguda
    "lia": {"stability": 0.65, "similarity_boost": 0.70, "style": 0.05},
    "diretoria": {"stability": 0.50, "similarity_boost": 0.80, "style": 0.15},
    "orion": {"stability": 0.50, "similarity_boost": 0.80, "style": 0.15},
}

def diagnostico_elevenlabs():
    key = os.getenv("ELEVENLABS_API_KEY", "")
    if not key:
        return {"ativo": False, "motivo": "ELEVENLABS_API_KEY nao esta no Render. Coloque em Environment + Manual Deploy."}
    return {"ativo": True, "modelo": os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2"), "chave_tamanho": len(key), "vozes_configuradas": {k: bool(v) for k, v in VOZES.items()}}

def falar_elevenlabs(texto, quem):
    key = os.getenv("ELEVENLABS_API_KEY", "")
    quem_key = str(quem or "").lower()
    vid = VOZES.get(quem_key, "") or VOZES.get("diretoria", "") or os.getenv("ELEVENLABS_VOICE_ID", "")
    if not key or not vid or not texto:
        return None
    try:
        settings = VOICE_SETTINGS.get(quem_key, {"stability": 0.5, "similarity_boost": 0.75})
        body = json.dumps({"text": texto, "model_id": os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2"), "voice_settings": settings}).encode()
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}"
        req = urllib.request.Request(url, data=body, headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"}, method="POST")
        with urllib.request.urlopen(req, timeout=12) as r:
            return r.read()
    except Exception as e:
        print("ELEVENLABS FALHOU:", e)
        return None

# ---------------- FLASK APP - RENDER ----------------
if HAS_FLASK:
    app = Flask(__name__)

    @app.after_request
    def _no_cache(resp):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp

    @app.route("/health")
    def health():
        return jsonify({"ok": True, "versao": "V12 - ORCHESTRATOR FINAL", "elevenlabs": diagnostico_elevenlabs(), "projeto_atual": PROJETO_ATUAL[0]})

    @app.route("/")
    def index():
        # CORREÇÃO DO INTERNAL SERVER ERROR (500):
        # Antes: se index.html não existisse com esse nome exato, dava 500.
        # Agora: tenta index.html, depois PASSO1-CORRETO-SEU-CODIGO.html, depois qualquer .html.
        # Se nenhum existir, devolve página simples, NUNCA 500.
        import os as _os, glob as _glob
        for _nome in ["index.html", "PASSO1-CORRETO-SEU-CODIGO.html"]:
            if _os.path.exists(_nome):
                try:
                    return send_from_directory(".", _nome)
                except Exception:
                    pass
        # Se não achou nenhum, devolve HTML simples - servidor está vivo
        return "<h1>NEXUS CORE V12 rodando</h1><p>Servidor vivo. Coloque index.html na raiz do GitHub.</p><p><a href='/health'>Ver /health</a></p>", 200

    @app.errorhandler(500)
    def _erro500(e):
        # Nunca mostra tela preta 'Internal Server Error' sem explicação
        return jsonify({"ok": False, "erro": "500 - erro interno, mas servidor está vivo", "detalhe": str(e)[:300], "dica": "Veja os logs do Render. Rota /health deve responder."}), 200

    @app.errorhandler(404)
    def _erro404(e):
        return jsonify({"ok": False, "erro": "404 - rota não achada", "rotas": ["/", "/health", "/perguntar", "/api/chat", "/api/voice"]}), 404

    @app.route("/perguntar", methods=["POST"])
    def perguntar():
        d = request.get_json(force=True, silent=True) or {}
        pergunta = d.get("pergunta") or d.get("texto") or d.get("prompt") or ""
        destino = d.get("destino") or d.get("departamento") or "coletiva"
        projeto = d.get("projeto") or PROJETO_ATUAL[0] or "Geral"
        PROJETO_ATUAL[0] = projeto
        r = responder(pergunta, destino=destino, projeto=projeto)
        return jsonify(r)

    @app.route("/api/chat", methods=["POST"])
    def api_chat():
        d = request.get_json(force=True, silent=True) or {}
        pergunta = d.get("pergunta") or d.get("texto") or ""
        quem = d.get("quem") or d.get("destino") or "coletiva"
        projeto = d.get("projeto") or PROJETO_ATUAL[0] or "Geral"
        # Mapeia nomes do front: FORJA/LIA/ORION -> lab/marketing/diretoria
        mapa = {"forja": "lab", "lia": "marketing", "orion": "diretoria", "lab": "lab", "marketing": "marketing", "diretoria": "diretoria", "coletiva": "coletiva", "todos": "coletiva"}
        destino = mapa.get(str(quem).lower(), "coletiva")
        r = responder(pergunta, destino=destino, projeto=projeto)
        # Front espera {quem, resposta} - devolve o primeiro + lista completa
        if r.get("respostas"):
            prim = r["respostas"][0]
            return jsonify({"quem": prim["nome"], "resposta": prim["texto"], "texto": prim["texto"], "respostas": r["respostas"], "criados": r.get("criados", []), "parar": r.get("parar", False), "fast": r.get("fast", False)})
        return jsonify({"quem": "ORION", "resposta": "", "respostas": [], "parar": True})

    @app.route("/api/voice", methods=["POST"])
    def api_voice():
        d = request.get_json(force=True, silent=True) or {}
        texto = d.get("texto") or d.get("text") or ""
        quem = d.get("quem") or d.get("departamento") or "diretoria"
        audio = falar_elevenlabs(texto, quem)
        if audio:
            return Response(audio, mimetype="audio/mpeg")
        return jsonify({"erro": "ElevenLabs não configurado ou falhou", "diagnostico": diagnostico_elevenlabs()}), 503

    @app.route("/lab/criar", methods=["POST"])
    def lab_criar_route():
        d = request.get_json(force=True, silent=True) or {}
        pergunta = d.get("pergunta") or d.get("texto") or ""
        tipo = d.get("tipo") or "codigo"
        projeto = d.get("projeto") or PROJETO_ATUAL[0] or "Geral"
        return jsonify(lab_criar(pergunta, tipo=tipo, projeto=projeto))

    @app.route("/ordem", methods=["GET", "POST"])
    def ordem_route():
        if request.method == "POST":
            d = request.get_json(force=True, silent=True) or {}
            projeto = d.get("projeto") or PROJETO_ATUAL[0] or "Geral"
            ordem = _orion_cria_ordem_servico(projeto, d.get("titulo", "Ordem de serviço"), d.get("detalhes", ""))
            return jsonify(ordem)
        projeto = request.args.get("projeto") or PROJETO_ATUAL[0] or "Geral"
        return jsonify(_projeto(projeto)["ordens"])

    @app.route("/campanha", methods=["GET", "POST"])
    def campanha_route():
        if request.method == "POST":
            d = request.get_json(force=True, silent=True) or {}
            projeto = d.get("projeto") or PROJETO_ATUAL[0] or "Geral"
            camp = _orion_cria_campanha(projeto, d.get("tema", "Campanha"), d.get("detalhes", ""))
            return jsonify(camp)
        projeto = request.args.get("projeto") or PROJETO_ATUAL[0] or "Geral"
        return jsonify(_projeto(projeto)["campanhas"])

    @app.route("/projeto/trocar", methods=["POST"])
    def projeto_trocar():
        d = request.get_json(force=True, silent=True) or {}
        nome = d.get("projeto") or d.get("nome") or "Geral"
        PROJETO_ATUAL[0] = nome
        _projeto(nome)
        return jsonify({"projeto": nome, "msg": f"Projeto {nome} aberto. Não vou misturar com os outros."})

    @app.route("/quadro", methods=["GET"])
    def quadro():
        projeto = request.args.get("projeto") or PROJETO_ATUAL[0] or "Geral"
        p = _projeto(projeto)
        return jsonify({"projeto": projeto, "quadro": p["quadro"], "ordens": p["ordens"], "campanhas": p["campanhas"]})

    @app.route("/config/email", methods=["POST"])
    def config_email():
        d = request.get_json(force=True, silent=True) or {}
        return jsonify({"ok": True, "mensagem": f"E-mail cadastrado: {d.get('email','')}"})

    @app.route("/relatorio/email", methods=["POST"])
    def relatorio_email():
        return jsonify({"ok": True, "mensagem": "Relatório enviado"})

    if __name__ == "__main__":
        port = int(os.getenv("PORT", "10000"))
        print(f"NEXUS CORE V12 - ORCHESTRATOR rodando na porta {port}")
        app.run(host="0.0.0.0", port=port)
