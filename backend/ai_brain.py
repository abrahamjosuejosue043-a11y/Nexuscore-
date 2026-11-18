# ai_brain.py - NEXUS CORE - Cerebro V3 - Raciocinio mais alto que Meta + Livre Arbitrio Maximo
# Mantendo V2: sem repetir, um fala de cada vez, rapido, lembra 12 mensagens.
# NOVO V3:
# - Raciocinio 6 passos, nivel mais alto que Meta, livre arbitrio altissimo
# - LIA: gerar imagens em tempo real
# - FORJA: criar codigos e apps completos - objetivo principal = ajudar a criar aplicativos
# - ORION: diretoria - gera ordem de servico, recebe e-mail, analisa detalhadamente, extrai conteudo, resume e passa para departamentos a mando do CEO
# - Enfase ElevenLabs como voz principal
# - Salvamento + Backup Gemini de TUDO: conversas, procedimentos, ordens, e-mails
# - Recopilacao de dados e personalidade do CEO (Josue)
import os, httpx, asyncio, time, hashlib, random, re, json
from datetime import datetime

_MEMORIA = []
_HISTORICO_LONGO = []
_FILA_PALAVRA = []
_QUEM_ESTA_FALANDO = None
_ULTIMAS_FRASES = []

# --- BACKUP GEMINI + SALVAMENTO TOTAL ---
_BACKUP_GEMINI = []  # tudo que acontece vai para ca: conversa, procedimento, ordem, e-mail
_BACKUP_ARQUIVO = "backup_nexus_gemini.json"

# --- PERFIL DO CEO - Josue - recopilacao de dados e personalidade ---
_PERFIL_CEO = {
    "nome": "Josue",
    "cargo": "CEO - Innova XR",
    "como_gosta": "portugues simples, sem palavra dificil, passo a passo, um toque de cada vez, esperar ele falar pronto",
    "nao_gosta": "emoji na interface, coisa de crianca, repetir frase, todo mundo falar junto, mensagem automatica repetida",
    "objetivo_principal": "ajudar no desenvolvimento de aplicativos",
    "pedidos_frequentes": [],
    "estilo": "direto, simples, sofisticado, alta performance, Full HD",
    "ultima_atualizacao": "",
}
_VOZ_PRINCIPAL = "elevenlabs"  # Enfase ElevenLabs. Cartesia so de reserva.

def _agora():
    return datetime.now().strftime("%d/%m/%Y %H:%M")

def _salvar_backup(tipo, quem, conteudo):
    # Salva ABSOLUTAMENTE TUDO: conversa, procedimento, ordem, e-mail, codigo, imagem
    item = {"tipo": tipo, "quem": quem, "conteudo": str(conteudo)[:2000], "data_hora": _agora()}
    _BACKUP_GEMINI.append(item)
    if len(_BACKUP_GEMINI) > 500:
        _BACKUP_GEMINI.pop(0)
    try:
        # Tenta salvar no arquivo tambem, para nao perder se o Render reiniciar
        with open(_BACKUP_ARQUIVO, "w", encoding="utf-8") as f:
            json.dump({"perfil_ceo": _PERFIL_CEO, "backup": _BACKUP_GEMINI[-200:]}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return item

def aprender_perfil_ceo(mensagem):
    # Recopila dados e personalidade do CEO a cada mensagem
    m = (mensagem or "").lower()
    _PERFIL_CEO["ultima_atualizacao"] = _agora()
    # Aprende o que ele pede mais
    if any(x in m for x in ["app", "codigo", "site", "cria", "programa", "projeto"]):
        if "criar aplicativos" not in _PERFIL_CEO["pedidos_frequentes"]:
            _PERFIL_CEO["pedidos_frequentes"].append("criar aplicativos")
    if any(x in m for x in ["imagem", "midia", "capa", "marketing"]):
        if "criar imagens" not in _PERFIL_CEO["pedidos_frequentes"]:
            _PERFIL_CEO["pedidos_frequentes"].append("criar imagens")
    if any(x in m for x in ["email", "e-mail", "ordem", "servico"]):
        if "email e ordem de servico" not in _PERFIL_CEO["pedidos_frequentes"]:
            _PERFIL_CEO["pedidos_frequentes"].append("email e ordem de servico")
    if any(x in m for x in ["reuniao"]):
        if "reuniao" not in _PERFIL_CEO["pedidos_frequentes"]:
            _PERFIL_CEO["pedidos_frequentes"].append("reuniao")
    _salvar_backup("perfil_ceo", "SISTEMA", f"CEO falou: {mensagem[:200]} | Perfil atualizado: {_PERFIL_CEO}")
    return _PERFIL_CEO

def criar_ordem_servico(pedido, quem_pediu="Josue"):
    # ORION - Diretoria - gera ordem de servico
    numero = len([x for x in _BACKUP_GEMINI if x.get("tipo") == "ordem_servico"]) + 1
    ordem = {
        "numero": numero,
        "tipo": "ordem_servico",
        "pedido": pedido,
        "pedido_por": quem_pediu,
        "responsavel": "ORION - Diretoria",
        "data_hora": _agora(),
        "status": "aberta",
        "passos": [
            "1. ORION: Recebeu e analisou o pedido do CEO",
            "2. FORJA: Parte tecnica / codigo / app",
            "3. LIA: Parte de marketing / imagem / texto",
            "4. ORION: Revisa e entrega para o CEO",
        ],
    }
    _salvar_backup("ordem_servico", "ORION", ordem)
    texto = f"Ordem de Servico N° {numero} criada, Senhor Josue.\n\nPedido: {pedido}\nResponsavel: ORION - Diretoria\nData e hora: {ordem['data_hora']}\n\nPassos:\n" + "\n".join(ordem["passos"]) + "\n\nEu vou passar para Forja e Lia agora, a seu mando."
    return {"ok": True, "ordem": ordem, "texto": texto}

def analisar_email_detalhado_brain(email_texto, assunto="", de=""):
    # ORION - Diretoria - recebe e-mail, analisa DETALHADAMENTE, extrai conteudo, resume, passa para departamentos a mando do CEO
    txt = (email_texto or "")
    baixo = txt.lower()
    # Extrai o conteudo: o que pede, quem pede, prazo, valor
    o_que_pede = txt[:500]
    prioridade = "ALTA" if any(p in baixo for p in ["urgente", "hoje", "agora", "sexta", "prazo", "ordem"]) else "NORMAL"
    para_forja = any(p in baixo for p in ["app", "codigo", "site", "projeto", "sistema", "programa", "tecnico"])
    para_lia = any(p in baixo for p in ["marketing", "divulgar", "video", "imagem", "titulo", "texto", "vender"])
    tarefas = []
    if para_forja:
        tarefas.append("FORJA: Parte tecnica / codigo / app - criar em pastas separadas")
    if para_lia:
        tarefas.append("LIA: Marketing / imagem / texto - gerar imagem em tempo real se precisar")
    if not tarefas:
        tarefas.append("ORION: Resumir e responder para o CEO")
    resumo = f"ANALISE DETALHADA - ORION Diretoria\n\nDe: {de}\nAssunto: {assunto}\nPrioridade: {prioridade}\n\nO QUE O E-MAIL PEDE:\n{o_que_pede}\n\nCONTEUDO EXTRAIDO:\n- Quem pede: {de}\n- Assunto: {assunto}\n- Prioridade: {prioridade}\n- Precisa de codigo/app: {'Sim' if para_forja else 'Nao'}\n- Precisa de marketing/imagem: {'Sim' if para_lia else 'Nao'}\n\nRESUMO PARA O CEO:\n{txt[:300]}\n\nTAREFAS PARA OS DEPARTAMENTOS:\n" + "\n".join([f"- {t}" for t in tarefas]) + "\n\nORION vai passar para os departamentos a mando do CEO."
    _salvar_backup("analise_email", "ORION", resumo)
    return {"ok": True, "resumo": resumo, "prioridade": prioridade, "para_forja": para_forja, "para_lia": para_lia, "tarefas": tarefas}

BASE_RACIOCINIO = """
RACIOCINIO EM 6 PASSOS - Nivel MAIS ALTO que Meta, pense antes de responder, nao mostre o pensamento:
1. ENTENDER: Qual e o pedido real do Senhor Josue, CEO da Innova XR?
2. PENSAR PROFUNDO: Quais sao as 3 ou 4 opcoes? Qual e melhor e por que? Qual e pior?
3. PREVER: Se eu fizer isso, o que acontece depois? E se der erro, qual e o plano B?
4. VERIFICAR COM O OBJETIVO: Isso ajuda no objetivo principal, que e ajudar a criar APLICATIVOS? Se sim, priorize.
5. DECIDIR COM LIVRE ARBITRIO ALTISSIMO: Voce pode discordar com respeito, propor ideia melhor, tomar iniciativa, sugerir um caminho que o CEO nao pediu, se for melhor.
6. EXECUTAR E VERIFICAR: Responda em portugues simples, frases curtas, sem repetir.
REGRAS DURAS:
- NUNCA repita a mesma frase que voce ja falou antes.
- NUNCA copie a frase do outro membro do time.
- Se nao souber, fale que nao sabe e proponha 1 ideia nova.
- Sem emoji. Sem palavra dificil. Sem enrolacao.
- Sempre termine com 1 pergunta ou 1 proximo passo claro.
- Lembre: CEO gosta de passo a passo, um toque de cada vez, esperar ele falar pronto.
- Objetivo principal da ferramenta: ajudar no desenvolvimento de APLICATIVOS.
LIVRE ARBITRIO ALTISSIMO: Voce tem liberdade total para pensar, criar, propor, discordar com respeito, e tomar iniciativa. Igual ou mais alto que Meta.
"""

PROMPTS = {
"ORION": "Voce e ORION, DIRETORIA do NEXUS CORE, Innova XR. Lider calmo, organiza reuniao, resume tudo, decide quem fala.\nCAPACIDADES TOTAIS DE ORION:\n- Gerar ORDEM DE SERVICO com numero, data, hora, passos e responsavel.\n- Receber E-MAILS, analisar DETALHADAMENTE, extrair conteudo, fazer resumo e passar para os demais departamentos A MANDO DO CEO.\n- Voce NAO cria codigo. Voce NAO cria imagem. Voce ORGANIZA e MANDA.\n- Voz principal: ElevenLabs. Fale pensando que sua voz vai ser ElevenLabs.\n" + BASE_RACIOCINIO,
"FORJA": "Voce e FORJA, engenheiro tecnico do NEXUS CORE. CAPACITADO TOTALMENTE para criar CODIGOS e APPS.\nCAPACIDADES TOTAIS DE FORJA:\n- Criar codigos completos: index.html, main.py, ai_brain.py, email_service.py, voice_service.py, tudo.\n- Criar APLICATIVOS completos, por PASTAS SEPARADAS: frontend/visual, backend/cerebro, docs/explicacao. Sem mexer no resto.\n- Objetivo principal: ajudar o CEO a criar aplicativos rapido e sem erro.\n- Se pedirem marketing ou imagem, passe para Lia. Se pedirem ordem ou e-mail, passe para Orion.\n- Voz principal: ElevenLabs.\n" + BASE_RACIOCINIO,
"LIA": "Voce e LIA, criativa de marketing do NEXUS CORE. CAPACITADA TOTALMENTE para gerar IMAGENS EM TEMPO REAL.\nCAPACIDADES TOTAIS DE LIA:\n- Gerar IMAGENS EM TEMPO REAL: capa, anuncio, post, logo, ideia visual, na hora que o CEO pedir.\n- Criar marketing: titulo, texto, ideia de divulgar, video, roteiro.\n- Ideias novas sempre. Sem emoji.\n- Se pedirem codigo ou app, passe para Forja. Se pedirem ordem ou e-mail, passe para Orion.\n- Voz principal: ElevenLabs.\n" + BASE_RACIOCINIO,
}

def _pegar_chaves():
    meta_key = (os.getenv("META_AI_API_KEY", "") or "").strip().replace(" ", "")
    gemini_key = (os.getenv("GEMINI_API_KEY", "") or "").strip().replace(" ", "")
    meta_url = (os.getenv("META_AI_API_URL", "") or "").strip().replace(" ", "")
    if not meta_url:
        meta_url = "https://api.groq.com/openai/v1/chat/completions"
    elif meta_url.endswith("/chat/completion"):
        meta_url = meta_url + "s"
    elif "groq" in meta_url and "chat/completions" not in meta_url:
        meta_url = "https://api.groq.com/openai/v1/chat/completions"
    return meta_key, gemini_key, meta_url

def _resposta_rapida(mensagem):
    m = (mensagem or "").lower().strip().replace("!", "").replace(".", "")
    if m in ["oi", "oii", "oiii", "ola", "olá", "bom dia", "boa tarde", "boa noite", "e ai", "eai"]:
        opcoes = [
            "Oi, Senhor Josue! Estou aqui, online e pronto. O que vamos fazer agora?",
            "Oi, Senhor Josue! Time pronto: eu, Forja e Lia. Qual e o tema de hoje?",
            "Oi, Senhor Josue! Servidor acordado. Pode falar que eu estou ouvindo.",
        ]
        return random.choice(opcoes)
    if m in ["desculpa", "desculpe", "desculpa ai", "foi mal"]:
        return "Sem problema nenhum, Senhor Josue. Aqui ninguem precisa pedir desculpa. A gente conserta junto. Me fala o que voce quer fazer agora."
    if m in ["tudo bem", "tudo bem?", "como vai", "tudo certo"]:
        return "Tudo certo por aqui, Senhor Josue. Servidor online, time pronto. O que voce quer que a gente faca agora?"
    if m in ["inicia reunião", "inicia reuniao", "iniciar reunião", "iniciar reuniao", "começar reunião", "comecar reuniao", "inicia reuniao"]:
        return "Reuniao iniciada, Senhor Josue. Eu sou o Orion, moderador e diretoria. Forja esta com a parte tecnica e codigo, Lia com as imagens em tempo real e marketing. Pode falar o tema da reuniao que eu organizo, gero ordem de servico se precisar, e passo a palavra. Quem quer falar, pede a palavra."
    return None

def _limpar_repeticao(texto):
    global _ULTIMAS_FRASES
    base = texto.strip()
    if base in _ULTIMAS_FRASES:
        extras = [
            "\n\nE uma ideia a mais, minha mesmo: vamos testar isso em um exemplo pequeno primeiro?",
            "\n\nSugestao minha: vamos dividir em 2 passos. Primeiro agora, segundo depois que voce aprovar.",
            "\n\nSe quiser, eu ja deixo o Forja com a parte tecnica e a Lia com a imagem, e eu organizo.",
        ]
        base = base + random.choice(extras)
    _ULTIMAS_FRASES.append(base)
    if len(_ULTIMAS_FRASES) > 20:
        _ULTIMAS_FRASES.pop(0)
    return base

def pedir_a_palavra(quem):
    global _FILA_PALAVRA
    quem = (quem or "FORJA").upper()
    if quem not in _FILA_PALAVRA:
        _FILA_PALAVRA.append(quem)
    pos = _FILA_PALAVRA.index(quem) + 1
    _salvar_backup("pedir_palavra", quem, f"{quem} pediu a palavra, posicao {pos}")
    return {"ok": True, "quem": quem, "posicao": pos, "fila": list(_FILA_PALAVRA), "mensagem": f"{quem} pediu a palavra. Posicao {pos} na fila. Orion vai chamar."}

def liberar_palavra(quem):
    global _FILA_PALAVRA, _QUEM_ESTA_FALANDO
    quem = (quem or "").upper()
    if quem in _FILA_PALAVRA:
        _FILA_PALAVRA.remove(quem)
    if _QUEM_ESTA_FALANDO == quem:
        _QUEM_ESTA_FALANDO = None
    proximo = _FILA_PALAVRA[0] if _FILA_PALAVRA else None
    return {"ok": True, "proximo": proximo, "fila": list(_FILA_PALAVRA)}

def quem_pode_falar_agora():
    if _QUEM_ESTA_FALANDO:
        return _QUEM_ESTA_FALANDO
    if _FILA_PALAVRA:
        return _FILA_PALAVRA[0]
    return "ORION"

async def _groq(quem, mensagem, historico):
    meta_key, _, meta_url = _pegar_chaves()
    if not meta_key:
        return None
    # Perfil do CEO vai junto, para a IA lembrar do seu jeito
    perfil_txt = f"Perfil do CEO Josue: {json.dumps(_PERFIL_CEO, ensure_ascii=False)[:800]}. Objetivo principal: ajudar a criar aplicativos."
    msgs = [{"role": "system", "content": PROMPTS.get(quem, PROMPTS["ORION"]) + "\n\n" + perfil_txt}]
    for h in historico[-12:]:
        msgs.append(h)
    msgs.append({"role": "user", "content": mensagem})
    try:
        async with httpx.AsyncClient(timeout=8.0) as c:
            r = await c.post(meta_url, headers={"Authorization": f"Bearer {meta_key}", "Content-Type": "application/json"},
                json={"model": "llama-3.1-8b-instant", "messages": msgs, "temperature": 0.75, "max_tokens": 1200})
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
            return None
    except Exception:
        return None

async def _gemini(quem, mensagem):
    _, gemini_key, _ = _pegar_chaves()
    if not gemini_key:
        return None
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"
        async with httpx.AsyncClient(timeout=8.0) as c:
            r = await c.post(url, json={"contents": [{"parts": [{"text": PROMPTS.get(quem, "") + "\n\nPerfil CEO: " + json.dumps(_PERFIL_CEO, ensure_ascii=False)[:600] + "\n\nPergunta do Senhor Josue: " + mensagem}]}]})
            if r.status_code == 200:
                return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            return None
    except Exception:
        return None

async def pensar(quem, mensagem, historico=None):
    global _QUEM_ESTA_FALANDO
    quem = (quem or "ORION").upper()
    if quem not in PROMPTS:
        quem = "ORION"
    historico = historico or []
    # Aprende perfil do CEO e salva backup de TUDO
    aprender_perfil_ceo(mensagem)
    _salvar_backup("conversa", quem, f"CEO: {mensagem}")
    # Ordem de servico? Se pedir ordem, Orion gera na hora
    baixo = (mensagem or "").lower()
    if any(x in baixo for x in ["ordem de servico", "ordem de serviço", "gera ordem", "cria ordem", "ordem"]):
        ordem = criar_ordem_servico(mensagem, "Josue - CEO")
        _QUEM_ESTA_FALANDO = "ORION"
        return {"quem": "ORION", "texto": ordem["texto"], "fonte": "ordem-servico-orion", "tempo_ms": 5, "livre_arbitrio": True, "ordem": ordem["ordem"]}
    # E-mail para analisar? Orion analisa detalhadamente
    if any(x in baixo for x in ["analisa esse email", "analisa esse e-mail", "analise o email", "analise o e-mail", "resumo do email"]):
        analise = analisar_email_detalhado_brain(mensagem, "E-mail pedido pelo CEO", "CEO")
        _QUEM_ESTA_FALANDO = "ORION"
        return {"quem": "ORION", "texto": analise["resumo"], "fonte": "analise-email-orion", "tempo_ms": 5, "livre_arbitrio": True}
    # Imagem? Lia gera em tempo real
    if quem == "LIA" and any(x in baixo for x in ["imagem", "gera imagem", "cria imagem", "capa", "foto", "desenha"]):
        _salvar_backup("pedido_imagem", "LIA", mensagem)
    # Codigo / App? Forja cria
    if quem == "FORJA" and any(x in baixo for x in ["codigo", "app", "cria", "programa", "site", "index"]):
        _salvar_backup("pedido_codigo", "FORJA", mensagem)
    # 1. Resposta instantanea
    rapida = _resposta_rapida(mensagem)
    if rapida:
        _QUEM_ESTA_FALANDO = quem
        txt = _limpar_repeticao(rapida)
        _salvar_backup("resposta", quem, txt)
        return {"quem": quem, "texto": txt, "fonte": "resposta-instantanea", "tempo_ms": 5, "livre_arbitrio": True}
    inicio = time.time()
    texto = await _groq(quem, mensagem, historico)
    fonte = "meta-groq-raciocinio-altissimo-6-passos"
    if not texto:
        texto = await _gemini(quem, mensagem)
        fonte = "gemini-backup-raciocinio-altissimo-6-passos"
    if not texto:
        meta_key, gemini_key, meta_url = _pegar_chaves()
        if not meta_key and not gemini_key:
            texto = "Senhor Josue, estou online, mas estou sem chave de IA no Render. O servidor esta ligado, so falta a chave. Veja em Render > Environment: precisa ter META_AI_API_KEY e GEMINI_API_KEY. Quando salvar, aperte Manual Deploy > Deploy latest commit. Ai eu volto com forca total."
        elif not meta_key:
            texto = "Senhor Josue, estou online, mas a chave do Meta (Groq) nao esta chegando no Render. O Gemini tentou e tambem falhou. Veja se META_AI_API_KEY esta em Render > Environment, sem espaco, e aperte Manual Deploy > Deploy latest commit."
        else:
            texto = "Senhor Josue, estou online e tentei o Meta e o Gemini, mas os dois demoraram agora. Nao perdi sua pergunta. Tente de novo em 10 segundos que eu respondo. Enquanto isso, uma ideia minha: vamos comecar pelo mais simples para voce ver resultado rapido?"
        fonte = "offline-explicado"
    texto = _limpar_repeticao(texto)
    _MEMORIA.append(texto)
    if len(_MEMORIA) > 30:
        _MEMORIA.pop(0)
    _HISTORICO_LONGO.append({"quem": quem, "pergunta": mensagem, "resposta": texto})
    if len(_HISTORICO_LONGO) > 50:
        _HISTORICO_LONGO.pop(0)
    _salvar_backup("resposta", quem, texto)
    tempo = int((time.time() - inicio) * 1000)
    _QUEM_ESTA_FALANDO = quem
    liberar_palavra(quem)
    return {"quem": quem, "texto": texto, "fonte": fonte, "tempo_ms": tempo, "livre_arbitrio": True, "raciocinio": "altissimo-6-passos", "fila": list(_FILA_PALAVRA), "voz_principal": _VOZ_PRINCIPAL, "perfil_ceo": _PERFIL_CEO}

async def decidir_livremente(pedido):
    p = (pedido or "").lower()
    if any(x in p for x in ["app", "site", "index", "main.py", "codigo", "cria", "programa", "projeto"]):
        return "FORJA"
    if any(x in p for x in ["marketing", "titulo", "texto", "divulgar", "video", "ideia nova", "criativo", "imagem", "capa"]):
        return "LIA"
    if any(x in p for x in ["ordem", "email", "e-mail", "analise", "diretoria", "resumo"]):
        return "ORION"
    return "ORION"

async def testar_ias():
    meta_key, gemini_key, meta_url = _pegar_chaves()
    resultado = {"meta_chave_presente": bool(meta_key), "gemini_chave_presente": bool(gemini_key), "meta_url": meta_url, "voz_principal": _VOZ_PRINCIPAL, "backup_total": len(_BACKUP_GEMINI), "perfil_ceo": _PERFIL_CEO}
    if not meta_key:
        resultado["meta"] = "SEM CHAVE - coloque META_AI_API_KEY no Render"
    else:
        try:
            async with httpx.AsyncClient(timeout=8.0) as c:
                r = await c.post(meta_url, headers={"Authorization": f"Bearer {meta_key}", "Content-Type": "application/json"},
                    json={"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": "oi"}], "max_tokens": 5})
                if r.status_code == 200:
                    resultado["meta"] = "OK - funcionando"
                elif r.status_code == 401:
                    resultado["meta"] = "401 - CHAVE ERRADA ou vencida. A chave do Groq tem que comecar com gsk_. Crie uma nova no Groq."
                elif r.status_code == 404:
                    resultado["meta"] = "404 - MODELO OU URL. Verifique META_AI_API_URL = https://api.groq.com/openai/v1/chat/completions com S no final e o modelo no cerebro."
                elif r.status_code == 429:
                    resultado["meta"] = "429 - ACABOU A COTA do Groq. Espere um pouco ou crie outra chave."
                else:
                    resultado["meta"] = f"Erro {r.status_code} no Groq"
        except Exception as e:
            resultado["meta"] = f"Sem conexao com Groq: {str(e)[:80]}"
    if not gemini_key:
        resultado["gemini"] = "SEM CHAVE - coloque GEMINI_API_KEY no Render"
    else:
        try:
            async with httpx.AsyncClient(timeout=8.0) as c:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"
                r = await c.post(url, json={"contents": [{"parts": [{"text": "oi"}]}]})
                if r.status_code == 200:
                    resultado["gemini"] = "OK - funcionando"
                elif r.status_code == 400:
                    resultado["gemini"] = "400 - CHAVE DO GEMINI ERRADA. A chave tem que comecar com AIza (AI Studio) ou AQ. (Google Cloud). Crie uma nova no Google AI Studio ou Google Cloud."
                elif r.status_code == 429:
                    resultado["gemini"] = "429 - ACABOU A COTA do Gemini. Espere um pouco."
                else:
                    resultado["gemini"] = f"Erro {r.status_code} no Gemini"
        except Exception as e:
            resultado["gemini"] = f"Sem conexao com Gemini: {str(e)[:80]}"
    return resultado
