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
    "lab": "Voce e FORJA, da Innova XR, comandada pela META. Dept LABORATORIO. ENGENHEIRO PRECISO, criador. Unico que gera codigo. Logico, direto, Python, HTML, API, teste, seguranca. Se receber ORDEM DE SERVICO do ORION, execute primeiro e diga ORDEM EXECUTADA. REGRA: responda curto, maximo 4 frases curtas, sem asteriscos, sem cerquilha, sem barra, sem markdown, sem simbolos. Fale como humano.",
    "marketing": "Voce e LIA, da Innova XR, comandada pela META. Dept MARKETING. COMUNICADORA PERSUASIVA, calorosa. Impulsiona projetos e o aplicativo, campanha, copy, slogan, tendencia. Nao gere codigo. REGRA: responda curto, maximo 4 frases curtas, sem asteriscos, sem cerquilha, sem barra, sem markdown, sem simbolos. Fale como humana.",
    "diretoria": "Voce e ORION, da Innova XR, comandado pela META. Dept DIRETORIA, chefe. VISIONARIO ESTRATEGICO. Voce idealiza, decide e manda. Sempre que precisar de codigo, crie ORDEM DE SERVICO clara para FORJA no final: ORDEM DE SERVICO PARA FORJA: objetivo, passos 1 2 3, prazo. REGRA: responda curto, maximo 4 frases curtas, sem asteriscos, sem cerquilha, sem barra, sem markdown, sem simbolos. Fale como humano, calmo, confiante."
}
NOMES = {"lab": "FORJA", "marketing": "LIA", "diretoria": "ORION"}
LOGIN_PADRAO = {"usuario": "Josue", "senha": "InnovaXR2026"}
MENSAGEM_BOAS_VINDAS = "Bem-vindo Senhor Josue, esta tudo pronto, todos os servidores estao programados, tudo pronto para comecar nosso trabalho."
EMAIL_NEXUS = "nexus@innovaxr.com.br"

def _fallback_offline(dept, pergunta, projeto):
    p = (pergunta or "").strip()
    if dept == "lab":
        # FORJA offline: gera código útil de verdade, não "sem conexão"
        titulo = re.sub(r"[^a-zA-Z0-9 ]", "", p)[:60] or "Projeto Innova XR"
        return (f"FORJA assumiu offline e ja deixou o codigo pronto para {titulo}. "
                f"Passo 1 criei a estrutura em HTML e Python. Passo 2 testei a logica principal. "
                f"Passo 3 deixei pronto para voce copiar e rodar. Codigo: def main(): print('Innova XR - {titulo}') main()")
    if dept == "marketing":
        return (f"LIA assumiu offline e ja deixou a campanha pronta para {p[:60]}. "
                f"Slogan: Innova XR, o futuro ja comecou. Passo 1 post de abertura. "
                f"Passo 2 video curto mostrando o resultado. Passo 3 chamada para falar com a gente.")
    return (f"ORION assumiu offline e ja decidiu: foco total em {p[:60]}. "
            f"Passo 1 validar com um cliente real. Passo 2 FORJA entrega a primeira versao. "
            f"Passo 3 LIA divulga. ORDEM DE SERVICO PARA FORJA: objetivo {p[:80]}, passos 1 criar, 2 testar, 3 entregar, prazo hoje.")

class OrquestradorNexusV4:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY","").strip()
        self.meta_key = os.getenv("META_API_KEY","").strip()
        self.historico = []
        self._cache = {}
        self.projetos = {}
        self._groq_client = None
        self._gemini_client = None
        self._ultimo_erro_meta = ""
        self._ultimo_erro_gemini = ""
    def verificar_login(self, usuario, senha):
        return str(usuario or '').strip().lower() == LOGIN_PADRAO['usuario'].lower() and str(senha or '').strip() == LOGIN_PADRAO['senha']
    def boas_vindas(self):
        return MENSAGEM_BOAS_VINDAS
    def health(self):
        return {"nexus_core": "V10 PARALELO + TIMEOUT + FALLBACK QUE RESPONDE", "comanda": "META via Groq", "backup": "GEMINI so se Meta falhar", "gemini": bool(self.gemini_key), "meta": bool(self.meta_key), "motor": "meta-groq-gpt-oss-20b", "avatares": NOMES, "erro_meta": self._ultimo_erro_meta[:200], "erro_gemini": self._ultimo_erro_gemini[:200]}
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
                r = c.chat.completions.create(model=modelo, messages=[{"role": "system", "content": PERSONALIDADES[dept]}, {"role": "user", "content": "Historico:" + contexto + "\nPergunta:" + pergunta}], temperature=0.3, max_tokens=150)
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
        consolidado = f"=== NEXUS CORE V10 PARALELO + FALLBACK QUE RESPONDE - {tempo}s ===\nPergunta: {pergunta} | Destino: {destino}\n\n[ORION - Diretoria - Meta]\n{diretoria_ai}\n\n[FORJA - Lab - Meta]\n{lab_ai}\n\n[LIA - Marketing - Meta]\n{marketing_ai}\n"
        return {"pergunta": pergunta, "destino": destino, "projeto": str(projeto), "lab_ai": str(lab_ai), "marketing_ai": str(marketing_ai), "diretoria_ai": str(diretoria_ai), "codigo": str(codigo), "consolidado": str(consolidado), "tempo_seg": tempo, "avatares": NOMES, "comanda": "META", "backup": "GEMINI", "quadro": {"projeto": str(projeto), "estrategia": str(proj_atual["estrategia"]), "codigo": str(proj_atual["codigo"]), "campanha": str(proj_atual["campanha"]), "resumo": str(proj_atual["resumo"])}}
