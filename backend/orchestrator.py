import os, re, time
# V8.6 - MEMORIA DE PROJETOS + TUDO ANTERIOR MANTIDO
# MANTIDO: 1) META COMANDA, GEMINI SO BACKUP 2) FORJA/LIA/ORION 3) DIRECIONADO SO UM RESPONDE 4) RESPOSTA CURTA RAPIDA
# NOVO: 5) MEMORIA DE PROJETOS - os 3 ficam cientes do projeto e cruzam dados.
# Cada projeto tem pasta propria: historico, resumo, decisoes, codigo, campanha. Nao mistura projeto A com B.
# Quando ORION cria ordem, FORJA executa e LIA divulga, tudo fica salvo na pasta do projeto e os 3 leem na proxima pergunta.
# Quem comanda as 3 inteligencias e a META via Groq. SEMPRE.
# FORJA (Lab) = Meta, LIA (Marketing) = Meta, ORION (Diretoria) = Meta.
# A Gemini NUNCA e motor principal. Ela so entra se a Meta der pau, como backup, e volta para Meta na proxima pergunta.
# Ordem de comando: 1) Meta gpt-oss-20b, 2) Meta gpt-oss-120b, 3) SO SE META FALHAR -> Gemini backup, 4) se tudo falhar -> frase curta sem codigo tecnico.
PERSONALIDADES = {
    "lab": "Voce e FORJA, da Innova XR, comandada pela META. Dept LABORATORIO. ENGENHEIRO PRECISO, criador. Unico que gera codigo. Logico, direto, Python, HTML, API, teste, seguranca. Se receber ORDEM DE SERVICO do ORION, execute primeiro e diga ORDEM EXECUTADA. REGRA: responda curto, maximo 6 frases curtas, sem asteriscos, sem cerquilha, sem barra, sem markdown, sem simbolos. Fale como humano.",
    "marketing": "Voce e LIA, da Innova XR, comandada pela META. Dept MARKETING. COMUNICADORA PERSUASIVA, calorosa. Impulsiona projetos e o aplicativo, campanha, copy, slogan, tendencia. Nao gere codigo. REGRA: responda curto, maximo 6 frases curtas, sem asteriscos, sem cerquilha, sem barra, sem markdown, sem simbolos. Fale como humana.",
    "diretoria": "Voce e ORION, da Innova XR, comandado pela META. Dept DIRETORIA, chefe. VISIONARIO ESTRATEGICO. Voce idealiza, decide e manda. Sempre que precisar de codigo, crie ORDEM DE SERVICO clara para FORJA no final: ORDEM DE SERVICO PARA FORJA: objetivo, passos 1 2 3, prazo. REGRA: responda curto, maximo 6 frases curtas, sem asteriscos, sem cerquilha, sem barra, sem markdown, sem simbolos. Fale como humano, calmo, confiante."
}
NOMES = {"lab": "FORJA", "marketing": "LIA", "diretoria": "ORION"}
class OrquestradorNexusV4:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.meta_key = os.getenv("META_API_KEY")
        self.historico = []
        self._cache = {}
        self.projetos = {}  # {nome_projeto: {historico:[], resumo:'', decisoes:[], codigo:'', campanha:'', estrategia:''}}
    def health(self):
        return {"nexus_core": "V8.6 META COMANDA + MEMORIA DE PROJETOS", "comanda": "META via Groq", "backup": "GEMINI so se Meta falhar", "gemini": bool(self.gemini_key), "meta": bool(self.meta_key), "motor": "meta-groq-gpt-oss-20b", "avatares": NOMES}
    def _get_projeto(self, nome):
        nome = (nome or 'Geral').strip() or 'Geral'
        if nome not in self.projetos:
            self.projetos[nome] = {'historico': [], 'resumo': '', 'decisoes': [], 'codigo': '', 'campanha': '', 'estrategia': ''}
        return self.projetos[nome]
    def _contexto_projeto(self, nome):
        proj = self._get_projeto(nome)
        ctx = 'PROJETO ATUAL: ' + (nome or 'Geral') + '\n'
        if proj['resumo']:
            ctx += 'RESUMO DO PROJETO (o que ja foi decidido): ' + proj['resumo'][-1200:] + '\n'
        if proj['decisoes']:
            ctx += 'DECISOES ANTERIORES: ' + ' | '.join(proj['decisoes'][-5:]) + '\n'
        if proj['codigo']:
            ctx += 'CODIGO JA CRIADO NESTE PROJETO: ' + proj['codigo'][-600:] + '\n'
        if proj['campanha']:
            ctx += 'CAMPANHA JA CRIADA: ' + proj['campanha'][-600:] + '\n'
        ctx += 'REGRA: voce esta ciente deste projeto. Cruze dados com o que os outros 2 ja fizeram nele. Nao misture com outro projeto.\n'
        return ctx
    def _salvar_no_projeto(self, nome, destino, pergunta, lab_ai, marketing_ai, diretoria_ai, codigo):
        proj = self._get_projeto(nome)
        proj['historico'].append('CEO: ' + pergunta)
        if diretoria_ai:
            proj['historico'].append('ORION: ' + diretoria_ai[:600])
            proj['estrategia'] = diretoria_ai[:800]
            # Extrai decisao curta
            proj['decisoes'].append(diretoria_ai[:200])
        if lab_ai:
            proj['historico'].append('FORJA: ' + lab_ai[:600])
            proj['codigo'] = lab_ai[:1200]
        if marketing_ai:
            proj['historico'].append('LIA: ' + marketing_ai[:600])
            proj['campanha'] = marketing_ai[:800]
        # Resumo acumulado para nao estourar
        proj['resumo'] = ('Projeto ' + nome + '. ' + ' | '.join(proj['historico'][-6:]))[-1500:]
        proj['historico'] = proj['historico'][-20:]
    def _gemini_backup(self, prompt, dept):
        # SO BACKUP: so e chamada se a Meta falhar. Nunca e chamada direto.
        for modelo_g in ["gemini-2.5-flash", "gemini-3.8-flash", "gemini-2.5-flash-lite"]:
            try:
                from google import genai as genai_novo
                client = genai_novo.Client(api_key=str(self.gemini_key or "").strip())
                resp = client.models.generate_content(model=modelo_g, contents=prompt)
                txt = getattr(resp, "text", "") or ""
                if txt.strip():
                    return str(txt) + " [backup Gemini, Meta falhou nesta resposta]"
            except Exception:
                continue
        return ""
    def _meta_comanda(self, pergunta, contexto, dept, projeto='Geral'):
        # META COMANDA: tenta Meta primeiro, sempre. Gemini so se Meta falhar.
        chave = str(self.meta_key or "").strip()
        cache_key = (projeto or 'Geral') + "|" + dept + "|" + pergunta.strip().lower()[:120]
        if cache_key in self._cache:
            return self._cache[cache_key]
        prompt = PERSONALIDADES[dept] + "\n" + self._contexto_projeto(projeto) + "\nHistorico curto:" + contexto + "\nPergunta:" + pergunta
        if chave:
            for modelo in ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]:
                try:
                    from groq import Groq
                    c = Groq(api_key=chave)
                    r = c.chat.completions.create(model=modelo, messages=[{"role": "system", "content": PERSONALIDADES[dept]}, {"role": "user", "content": "Historico:" + contexto + "\nPergunta:" + pergunta}], temperature=0.5, max_tokens=320)
                    txt = str(r.choices[0].message.content)
                    if txt.strip():
                        self._cache[cache_key] = txt
                        return txt
                except Exception:
                    continue
        # META FALHOU -> AGORA SIM entra Gemini como backup
        backup = self._gemini_backup(prompt, dept)
        if backup:
            return backup
        nome = NOMES.get(dept, dept)
        return nome + " esta sem conexao agora. A Meta falhou e o backup tambem. Tenta de novo em 1 minuto."
    def _meta_dept(self, pergunta, contexto, dept, projeto='Geral'):
        return self._meta_comanda(pergunta, contexto, dept, projeto)
    def _gemini_dept(self, pergunta, contexto, dept, projeto='Geral'):
        # Travado: ninguem chama Gemini direto. Sempre passa pela Meta primeiro.
        return self._meta_comanda(pergunta, contexto, dept, projeto)
    def _meta_lab(self, pergunta, contexto, projeto='Geral'):
        return self._meta_comanda(pergunta, contexto, "lab", projeto)
    def reuniao(self, pergunta: str, destino: str = "todos", projeto: str = "Geral"):
        t0 = time.time()
        pergunta = str(pergunta); destino = str(destino)
        contexto = "\n".join(self.historico[-3:])
        self.historico.append("CEO: " + pergunta + " [destino=" + destino + "]")
        lab_ai = ""; marketing_ai = ""; diretoria_ai = ""; codigo = ""
        if destino in ("todos", "opiniao"):
            diretoria_ai = self._meta_comanda(pergunta, contexto, "diretoria", projeto)
            self.historico.append("ORION (Meta): " + diretoria_ai)
            ordem = ""
            m = re.search(r"ORDEM DE SERVICO PARA (?:FORJA|LAB):(.*)", diretoria_ai, re.IGNORECASE | re.DOTALL)
            if m:
                ordem = m.group(0)[:500]
            pergunta_lab = pergunta + ("\n\nORDEM DO ORION PARA VOCE EXECUTAR:\n" + ordem if ordem else "")
            lab_ai = self._meta_comanda(pergunta_lab, "\n".join(self.historico[-3:]), "lab", projeto)
            self.historico.append("FORJA (Meta): " + lab_ai)
            codigo = lab_ai
            marketing_ai = self._meta_comanda(pergunta, "\n".join(self.historico[-3:]), "marketing", projeto)
            self.historico.append("LIA (Meta): " + marketing_ai)
        elif destino == "lab":
            lab_ai = self._meta_comanda(pergunta, contexto, "lab", projeto)
            codigo = lab_ai
        elif destino == "marketing":
            marketing_ai = self._meta_comanda(pergunta, contexto, "marketing", projeto)
        elif destino == "diretoria":
            # DIRECIONADO: so ORION responde. Nao chama FORJA nem LIA.
            diretoria_ai = self._meta_comanda(pergunta, contexto, "diretoria", projeto)
            # ORION cria a ordem, mas NAO executa aqui. So executa se destino for todos.
            pass
        self._salvar_no_projeto(projeto, destino, pergunta, lab_ai, marketing_ai, diretoria_ai, codigo)
        proj_atual = self._get_projeto(projeto)
        tempo = round(time.time() - t0, 1)
        consolidado = "=== NEXUS CORE V8.6 META COMANDA + MEMORIA DE PROJETOS, GEMINI SO BACKUP - " + str(tempo) + "s ===\nPergunta: " + pergunta + " | Destino: " + destino + "\n\n[ORION - Diretoria - Meta]\n" + str(diretoria_ai) + "\n\n[FORJA - Lab - Meta]\n" + str(lab_ai) + "\n\n[LIA - Marketing - Meta]\n" + str(marketing_ai) + "\n"
        return {"pergunta": pergunta, "destino": destino, "projeto": str(projeto), "lab_ai": str(lab_ai), "marketing_ai": str(marketing_ai), "diretoria_ai": str(diretoria_ai), "codigo": str(codigo), "consolidado": str(consolidado), "tempo_seg": tempo, "avatares": NOMES, "comanda": "META", "backup": "GEMINI", "quadro": {"projeto": str(projeto), "estrategia": str(proj_atual["estrategia"]), "codigo": str(proj_atual["codigo"]), "campanha": str(proj_atual["campanha"]), "resumo": str(proj_atual["resumo"])}}
