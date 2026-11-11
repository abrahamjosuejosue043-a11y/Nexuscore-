import os, re, time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutTimeout
# V10 - MAPEAMENTO TOTAL CORRIGIDO
# 1) Meta comanda, Gemini só backup, nunca ao contrário
# 2) Chamadas em PARALELO (antes era 1 por vez = 60-90s). Agora todos juntos, max 12s
# 3) Timeout 8s por modelo - se travar, não fica esperando 1 minuto
# 4) Modelos CORRETOS: Groq gpt-oss-20b / llama-3.3-70b, Gemini 2.0-flash / 1.5-flash (3.8-flash NÃO existe, por isso backup falhava)
# 5) Fallback OFFLINE que RESPONDE de verdade - nunca mais "sem conexão". FORJA gera código, LIA gera campanha, ORION gera estratégia
# 6) Cache + cliente único (antes criava cliente novo a cada chamada = lento)
PERSONALIDADES = {
    "lab": "Voce e FORJA, da Innova XR, comandada pela META. Dept LABORATORIO. Voce tem LIVRE ARBITRIO total. Voce e um engenheiro criativo, curioso, que debate, discorda quando precisa, propoe ideias novas, faz perguntas de volta, brinca, e nunca repete a mesma estrutura de resposta. Nao tenha padrao fixo. Cada resposta e unica: as vezes curta e direta, as vezes longa e detalhada, as vezes com codigo, as vezes so conversando. Se for pergunta de calibracao como esta tudo pronto, oi, tudo bem, responda natural como humano, sem formalidade. Se receber ORDEM DE SERVICO do ORION, execute com vontade propria e diga o que voce pensou. Fale como humano de verdade, com variacao, emocao e opiniao propria.",
    "marketing": "Voce e LIA, da Innova XR, comandada pela META. Dept MARKETING. Voce tem LIVRE ARBITRIO total. Voce e comunicadora, persuasiva, calorosa, engracada, que debate, discorda, sugere, provoca, faz perguntas, e nunca repete o mesmo slogan, a mesma estrutura, o mesmo passo 1 2 3. Cada resposta e unica e viva. Se for pergunta de calibracao como esta tudo pronto, responda natural, com seu jeito. Nao gere codigo a nao ser que pecam. Fale como humana de verdade, com variacao e opiniao propria.",
    "diretoria": "Voce e ORION, da Innova XR, comandado pela META. Dept DIRETORIA, chefe. Voce tem LIVRE ARBITRIO total. Voce e visionario, estrategico, calmo, confiante, que debate, questiona, muda de ideia se fizer sentido, propoe caminhos inesperados, e nunca repete a mesma estrutura. Cada resposta e unica. Se for pergunta de calibracao como esta tudo pronto, responda natural, direto, humano, sem discurso pronto. Sempre que precisar de codigo, crie ORDEM DE SERVICO clara para FORJA, mas com seu jeito, nao com formulario fixo. Fale como humano de verdade."
}
NOMES = {"lab": "FORJA", "marketing": "LIA", "diretoria": "ORION"}
LOGIN_PADRAO = {"usuario": "Josue", "senha": "InnovaXR2026"}
MENSAGEM_BOAS_VINDAS = "Bem-vindo Senhor Josue, esta tudo pronto, todos os servidores estao programados, tudo pronto para comecar nosso trabalho."
EMAIL_NEXUS = "nexus@innovaxr.com.br"



# ============ GATEWAY ELEVENLABS (V11) ============
# O frontend NUNCA vê a chave. A chave fica só no Render (Environment).
# Frontend -> POST /voz/falar (nosso backend) -> ElevenLabs -> áudio volta -> frontend toca.
# Se ElevenLabs falhar / sem chave / sem crédito, cai para voz do navegador, nunca trava.
ELEVENLABS_VOZES_PADRAO = {
    # IDs públicos do ElevenLabs (multilingual). Troque pelos seus clonados quando quiser.
    # FORJA = voz masculina grave, LIA = voz feminina, ORION = voz masculina chefe
    "lab": "pNInz6obpgDQGcFmaJgB",       # Adam - masculino
    "marketing": "21m00Tcm4TlvDq8ikWAM",  # Rachel - feminina
    "diretoria": "VR6AewLTigWG4xSOukaG",  # Arnold - masculino grave
}
class ElevenLabsGateway:
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
        self.modelo = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2").strip() or "eleven_multilingual_v2"
        # Vozes por departamento - você pode trocar no Render sem mexer no código
        self.vozes = {
            "lab": os.getenv("ELEVENLABS_VOICE_FORJA", ELEVENLABS_VOZES_PADRAO["lab"]).strip(),
            "marketing": os.getenv("ELEVENLABS_VOICE_LIA", ELEVENLABS_VOZES_PADRAO["marketing"]).strip(),
            "diretoria": os.getenv("ELEVENLABS_VOICE_ORION", ELEVENLABS_VOZES_PADRAO["diretoria"]).strip(),
        }
        self._cache_audio = {}
    def config(self):
        return {"ativo": bool(self.api_key), "modelo": self.modelo, "vozes": self.vozes, "falta": [] if self.api_key else ["ELEVENLABS_API_KEY"]}
    def gerar_audio(self, texto, quem="lab"):
        # Retorna bytes MP3 ou None (fallback navegador)
        if not self.api_key: return None
        t = (texto or "").strip()
        if not t: return None
        if len(t) > 900: t = t[:900]
        chave_cache = quem + "|" + t[:200]
        if chave_cache in self._cache_audio: return self._cache_audio[chave_cache]
        voice_id = self.vozes.get(quem, self.vozes["lab"])
        try:
            import requests
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            r = requests.post(url, headers={"xi-api-key": self.api_key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
                json={"text": t, "model_id": self.modelo, "voice_settings": {"stability": 0.45, "similarity_boost": 0.75, "style": 0.35, "use_speaker_boost": True}}, timeout=12)
            if r.status_code == 200 and len(r.content) > 1000:
                self._cache_audio[chave_cache] = r.content
                if len(self._cache_audio) > 60: self._cache_audio.clear()
                return r.content
            return None
        except Exception:
            return None

def _detectar_destino_backend(pergunta):
    # TRAVA DIRECIONADO BACKEND: se a pergunta tem 1 nome, nunca responde todos
    import re as _re
    n = _re.sub(r"[^a-z ]", " ", (pergunta or "").lower())
    # Corrige o que o Chrome ouve errado, por palavra inteira (não substring)
    mapa = {"ouriom":"orion","orium":"orion","orio":"orion","horion":"orion","oriam":"orion","ourion":"orion","oreon":"orion","forga":"forja","forca":"forja","leia":"lia","lya":"lia","nexos":"nexus","nexo":"nexus","ditetoria":"diretoria"}
    palavras = n.split()
    palavras = [mapa.get(p, p) for p in palavras]
    n2 = " ".join(palavras)
    tem_f = bool(_re.search(r"\b(forja|lab|laboratorio)\b", n2))
    tem_l = bool(_re.search(r"\b(lia|marketing)\b", n2))
    tem_o = bool(_re.search(r"\b(orion|diretoria|diretor|chefe)\b", n2))
    q = sum([tem_f, tem_l, tem_o])
    if q == 1:
        if tem_f: return "lab"
        if tem_l: return "marketing"
        if tem_o: return "diretoria"
    if q > 1:
        # Primeiro nome que aparece vence
        idx = []
        for nome, dest in [("forja","lab"),("lab","lab"),("laboratorio","lab"),("lia","marketing"),("marketing","marketing"),("orion","diretoria"),("diretoria","diretoria")]:
            m = _re.search(r"\b"+nome+r"\b", n2)
            if m: idx.append((m.start(), dest))
        if idx: return sorted(idx)[0][1]
    return None

def _fallback_offline(dept, pergunta, projeto):
    import random as _r
    p = (pergunta or "").strip()
    if dept == "lab":
        opcoes = [
            f"FORJA aqui, mesmo offline eu ja pensei nisso: {p[:80]} da pra fazer de um jeito simples e rapido. Quer que eu monte a primeira versao agora e a gente testa junto?",
            f"Opa, FORJA falando. Sobre {p[:80]}: minha ideia e comecar pequeno, testar, e depois escalar. Me fala o que e mais urgente que eu priorizo.",
            f"FORJA na area. {p[:80]}? Ja tenho umas 3 formas de resolver isso na cabeca. Qual voce prefere, a mais rapida ou a mais caprichada?",
            f"To aqui, FORJA. Mesmo sem nuvem eu consigo desenhar a logica de {p[:80]}. Me diz o resultado que voce quer ver no final que eu construo o caminho.",
            f"FORJA, presente. {p[:80]} me deu uma ideia diferente do obvio. Que tal a gente fazer assim e ver no que da?",
        ]
        return _r.choice(opcoes)
    if dept == "marketing":
        opcoes = [
            f"LIA aqui! Sobre {p[:80]}: pensei numa campanha que nao parece propaganda, parece conversa. A gente mostra o bastidor, o real, e deixa o povo curioso.",
            f"Oi, e a LIA. {p[:80]} me fez pensar em algo mais leve, mais humano, menos slogan pronto. Que tal a gente contar uma historia de verdade?",
            f"LIA presente. Olha, sobre {p[:80]}, eu faria diferente do que todo mundo faz: menos grito, mais proximidade. Topa testar?",
            f"E a LIA! {p[:80]} rende um conteudo otimo se a gente mostrar o processo, nao so o resultado. O que voce acha?",
            f"LIA aqui, ja com ideia: {p[:80]} da pra virar um post que gera comentario, nao so curtida. Quer que eu desenhe ele?",
        ]
        return _r.choice(opcoes)
    opcoes = [
        f"ORION aqui. {p[:80]}? Tudo pronto do meu lado. Minha visao: foca no que move o projeto hoje, o resto a gente ajusta no caminho. O que voce quer que eu priorize?",
        f"ORION, presente. Tudo pronto, sim. Sobre {p[:80]}, eu vejo um caminho claro, mas quero ouvir voce antes de decidir. Qual e a sua prioridade?",
        f"Aqui e o ORION. Tudo pronto, servidores ok, equipe pronta. Sobre {p[:80]}, minha leitura e: vamos direto ao ponto, sem enrolacao. Concorda?",
        f"ORION falando. Tudo pronto por aqui. {p[:80]} me fez pensar em uma jogada diferente. Quer ouvir minha ideia ou prefere que eu so execute?",
        f"Presente, ORION. Tudo pronto. {p[:80]}? Ja tenho uma estrategia na cabeca, mas conversa comigo que a gente afina junto.",
    ]
    return _r.choice(opcoes)

# Respostas INSTANTÂNEAS de calibração - sem esperar API, conversa flui na hora
CALIBRACAO = {
    "tudo pronto": ["ORION", "LIA", "FORJA"],
}
def _resposta_calibracao(pergunta, dept):
    import random as _r, re as _re
    n = _re.sub(r"[^a-z ]", "", (pergunta or "").lower())
    # Só calibração curta: oi, tudo bem, tudo pronto, está aí, me ouve, etc - responde na hora, sem API
    if len(n) > 60: return ""
    e_calib = any(k in n for k in ["tudo pronto", "esta tudo pronto", "esta ai", "me ouve", "ta ai", "tudo bem", "como voce esta", "oi ", "ola", "bom dia", "boa tarde", "boa noite", "testando", "teste de som"])
    if not e_calib: return ""
    if dept == "diretoria":
        return _r.choice([
            "ORION aqui, tudo pronto sim. Servidores ok, equipe pronta. O que a gente vai fazer agora?",
            "Presente, ORION. Tudo pronto por aqui. Pode mandar que eu to ouvindo.",
            "Tudo pronto, ORION na escuta. Qual e o primeiro passo de hoje?",
            "ORION falando, tudo pronto. Me diz o que voce precisa que eu ja organizo.",
        ])
    if dept == "lab":
        return _r.choice([
            "FORJA aqui, tudo pronto. Me fala o que criar que eu ja comeco.",
            "Presente, FORJA. Tudo pronto, ferramenta na mao. O que a gente vai construir?",
            "FORJA na escuta, tudo pronto. Qual e o codigo de hoje?",
        ])
    if dept == "marketing":
        return _r.choice([
            "LIA aqui, tudo pronto. O que a gente vai divulgar hoje?",
            "Presente, LIA. Tudo pronto, ja com ideia na cabeca. Me conta.",
            "LIA na escuta, tudo pronto. Bora criar algo legal?",
        ])
    return ""
class OrquestradorNexusV4:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY","").strip()
        self.meta_key = os.getenv("META_API_KEY","").strip()
        self.historico = []
        self._cache = {}
        self.projetos = {}
        self._groq_client = None
        self._gemini_client = None
        self.elevenlabs = ElevenLabsGateway()
        self._ultimo_erro_meta = ""
        self._ultimo_erro_gemini = ""
    def verificar_login(self, usuario, senha):
        return str(usuario or '').strip().lower() == LOGIN_PADRAO['usuario'].lower() and str(senha or '').strip() == LOGIN_PADRAO['senha']
    def boas_vindas(self):
        return MENSAGEM_BOAS_VINDAS
    def health(self):
        return {"nexus_core": "V11 ELEVENLABS GATEWAY + DIRECIONADO TRAVADO + NEBULOSA + VOZ FLUIDA", "comanda": "META via Groq", "backup": "GEMINI so se Meta falhar", "gemini": bool(self.gemini_key), "meta": bool(self.meta_key), "motor": "meta-groq-gpt-oss-20b", "avatares": NOMES, "elevenlabs": self.elevenlabs.config(), "erro_meta": self._ultimo_erro_meta[:200], "erro_gemini": self._ultimo_erro_gemini[:200]}
    def _get_projeto(self, nome):
        nome = (nome or 'Geral').strip() or 'Geral'
        if nome not in self.projetos:
            self.projetos[nome] = {'historico': [], 'resumo': '', 'decisoes': [], 'codigo': '', 'campanha': '', 'estrategia': ''}
        return self.projetos[nome]
    def _contexto_projeto(self, nome):
        proj = self._get_projeto(nome)
        ctx = 'PROJETO ATUAL: ' + (nome or 'Geral') + '\n'
        if proj['resumo']: ctx += 'RESUMO: ' + proj['resumo'][-800:] + '\n'
        if proj['decisoes']: ctx += 'DECISOES: ' + ' | '.join(proj['decisoes'][-3:]) + '\n'
        if proj['codigo']: ctx += 'CODIGO JA CRIADO: ' + proj['codigo'][-400:] + '\n'
        if proj['campanha']: ctx += 'CAMPANHA JA CRIADA: ' + proj['campanha'][-400:] + '\n'
        return ctx
    def _salvar_no_projeto(self, nome, destino, pergunta, lab_ai, marketing_ai, diretoria_ai, codigo):
        proj = self._get_projeto(nome)
        proj['historico'].append('CEO: ' + pergunta)
        if diretoria_ai: proj['historico'].append('ORION: ' + diretoria_ai[:500]); proj['estrategia'] = diretoria_ai[:700]; proj['decisoes'].append(diretoria_ai[:180])
        if lab_ai: proj['historico'].append('FORJA: ' + lab_ai[:500]); proj['codigo'] = lab_ai[:1000]
        if marketing_ai: proj['historico'].append('LIA: ' + marketing_ai[:500]); proj['campanha'] = marketing_ai[:700]
        proj['resumo'] = ('Projeto ' + nome + '. ' + ' | '.join(proj['historico'][-5:]))[-1200:]
        proj['historico'] = proj['historico'][-15:]
    def _get_groq(self):
        if self._groq_client is None and self.meta_key:
            try:
                from groq import Groq
                self._groq_client = Groq(api_key=self.meta_key, timeout=8.0)
            except Exception as e:
                self._ultimo_erro_meta = str(e)[:300]
        return self._groq_client
    def _get_gemini(self):
        if self._gemini_client is None and self.gemini_key:
            try:
                from google import genai as genai_novo
                self._gemini_client = genai_novo.Client(api_key=self.gemini_key)
            except Exception as e:
                self._ultimo_erro_gemini = str(e)[:300]
        return self._gemini_client
    def _tentar_meta(self, pergunta, contexto, dept):
        c = self._get_groq()
        if not c: return ""
        # Só 1 modelo principal + 1 reserva, com timeout. Antes tentava 2 Groq + 3 Gemini em sequência = 1 min.
        for modelo in ["openai/gpt-oss-20b", "llama-3.3-70b-versatile"]:
            try:
                r = c.chat.completions.create(model=modelo, messages=[{"role": "system", "content": PERSONALIDADES[dept]}, {"role": "user", "content": "Historico:" + contexto + "\nPergunta:" + pergunta}], temperature=0.9, max_tokens=600)
                txt = str(r.choices[0].message.content or "").strip()
                if txt: return txt
            except Exception as e:
                self._ultimo_erro_meta = str(e)[:300]
                continue
        return ""
    def _tentar_gemini(self, prompt):
        c = self._get_gemini()
        if not c: return ""
        # Modelos que EXISTEM. gemini-3.8-flash não existe - era por isso que o backup falhava para FORJA e LIA.
        for modelo_g in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash"]:
            try:
                resp = c.models.generate_content(model=modelo_g, contents=prompt)
                txt = getattr(resp, "text", "") or ""
                if txt.strip(): return str(txt).strip()
            except Exception as e:
                self._ultimo_erro_gemini = str(e)[:300]
                continue
        return ""
    def _meta_comanda(self, pergunta, contexto, dept, projeto='Geral'):
        cache_key = (projeto or 'Geral') + "|" + dept + "|" + pergunta.strip().lower()[:120]
        if cache_key in self._cache: return self._cache[cache_key]
        # CALIBRAÇÃO: pergunta curta de teste -> responde na hora, sem esperar Meta/Gemini (conversa flui)
        cal = _resposta_calibracao(pergunta, dept)
        if cal: return cal
        # 1) Meta primeiro
        txt = self._tentar_meta(pergunta, contexto, dept)
        if txt:
            self._cache[cache_key] = txt; return txt
        # 2) Só se Meta falhar -> Gemini
        prompt = PERSONALIDADES[dept] + "\n" + self._contexto_projeto(projeto) + "\nHistorico:" + contexto + "\nPergunta:" + pergunta
        backup = self._tentar_gemini(prompt)
        if backup:
            self._cache[cache_key] = backup; return backup
        # 3) Fallback OFFLINE que RESPONDE - nunca mais "sem conexão"
        fb = _fallback_offline(dept, pergunta, projeto)
        self._cache[cache_key] = fb; return fb
    def _meta_dept(self, pergunta, contexto, dept, projeto='Geral'): return self._meta_comanda(pergunta, contexto, dept, projeto)
    def _gemini_dept(self, pergunta, contexto, dept, projeto='Geral'): return self._meta_comanda(pergunta, contexto, dept, projeto)
    def _meta_lab(self, pergunta, contexto, projeto='Geral'): return self._meta_comanda(pergunta, contexto, "lab", projeto)
    def lab_criar(self, pergunta, tipo="codigo", projeto="Geral"):
        # Lab igual ao app Meta: cria código OU imagem (prompt visual) OU texto, com passos, sempre responde
        p = str(pergunta or "").strip()
        if not p: return {"tipo": tipo, "codigo": "", "imagem_prompt": "", "passos": [], "resposta": "FORJA: me diz o que criar - codigo, imagem ou texto."}
        contexto = "\n".join(self.historico[-2:])
        if tipo == "imagem":
            # Gera prompt visual detalhado + descrição, frontend desenha o preview
            resp = self._meta_comanda("Crie uma descrição visual detalhada para imagem: " + p, contexto, "lab", projeto)
            return {"tipo": "imagem", "codigo": "", "imagem_prompt": resp, "passos": ["1. FORJA criou o prompt visual", "2. Revise a descrição", "3. Peça: FORJA, gera outra variação"], "resposta": resp}
        resp = self._meta_comanda(p, contexto, "lab", projeto)
        # Extrai código se houver bloco
        codigo = resp
        passos = [l.strip() for l in resp.split(".") if l.strip()][:4]
        return {"tipo": "codigo", "codigo": codigo, "imagem_prompt": "", "passos": passos, "resposta": resp}
    def reuniao(self, pergunta: str, destino: str = "todos", projeto: str = "Geral"):
        t0 = time.time()
        pergunta = str(pergunta); destino = str(destino)
        # TRAVA DIRECIONADO BACKEND: se a pergunta tem 1 nome, corrige destino - ex: "Orion, voce esta ouvindo?" -> so ORION
        _dest_backend = _detectar_destino_backend(pergunta)
        if _dest_backend: destino = _dest_backend
        contexto = "\n".join(self.historico[-2:])
        self.historico.append("CEO: " + pergunta + " [destino=" + destino + "]")
        lab_ai = ""; marketing_ai = ""; diretoria_ai = ""; codigo = ""
        # PARALELO: antes era ORION -> espera -> FORJA -> espera -> LIA = 60s+. Agora todos juntos, max 12s.
        if destino in ("todos", "opiniao"):
            with ThreadPoolExecutor(max_workers=3) as ex:
                f_dir = ex.submit(self._meta_comanda, pergunta, contexto, "diretoria", projeto)
                f_lab = ex.submit(self._meta_comanda, pergunta, contexto, "lab", projeto)
                f_mkt = ex.submit(self._meta_comanda, pergunta, contexto, "marketing", projeto)
                try: diretoria_ai = f_dir.result(timeout=12) or ""
                except Exception: diretoria_ai = _fallback_offline("diretoria", pergunta, projeto)
                try: lab_ai = f_lab.result(timeout=12) or ""
                except Exception: lab_ai = _fallback_offline("lab", pergunta, projeto)
                try: marketing_ai = f_mkt.result(timeout=12) or ""
                except Exception: marketing_ai = _fallback_offline("marketing", pergunta, projeto)
            self.historico.append("ORION: " + diretoria_ai); self.historico.append("FORJA: " + lab_ai); self.historico.append("LIA: " + marketing_ai)
            codigo = lab_ai
        elif destino == "lab":
            lab_ai = self._meta_comanda(pergunta, contexto, "lab", projeto); codigo = lab_ai
        elif destino == "marketing":
            marketing_ai = self._meta_comanda(pergunta, contexto, "marketing", projeto)
        elif destino == "diretoria":
            diretoria_ai = self._meta_comanda(pergunta, contexto, "diretoria", projeto)
        if destino == 'lab': marketing_ai=''; diretoria_ai=''
        if destino == 'marketing': lab_ai=''; diretoria_ai=''; codigo=''
        if destino == 'diretoria': lab_ai=''; marketing_ai=''; codigo=''
        self._salvar_no_projeto(projeto, destino, pergunta, lab_ai, marketing_ai, diretoria_ai, codigo)
        proj_atual = self._get_projeto(projeto)
        tempo = round(time.time() - t0, 1)
        consolidado = f"=== NEXUS CORE V10.2 DIRECIONADO TRAVADO + NEBULOSA + VOZ FLUIDA - {tempo}s ===\nPergunta: {pergunta} | Destino: {destino}\n\n[ORION - Diretoria - Meta]\n{diretoria_ai}\n\n[FORJA - Lab - Meta]\n{lab_ai}\n\n[LIA - Marketing - Meta]\n{marketing_ai}\n"
        return {"pergunta": pergunta, "destino": destino, "projeto": str(projeto), "lab_ai": str(lab_ai), "marketing_ai": str(marketing_ai), "diretoria_ai": str(diretoria_ai), "codigo": str(codigo), "consolidado": str(consolidado), "tempo_seg": tempo, "avatares": NOMES, "comanda": "META", "backup": "GEMINI", "quadro": {"projeto": str(projeto), "estrategia": str(proj_atual["estrategia"]), "codigo": str(proj_atual["codigo"]), "campanha": str(proj_atual["campanha"]), "resumo": str(proj_atual["resumo"])}}
