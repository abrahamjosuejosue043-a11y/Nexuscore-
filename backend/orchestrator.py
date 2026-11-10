import os, re, time
# V8.3 - REGRA TRAVADA: META COMANDA, GEMINI SO BACKUP
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
    def health(self):
        return {"nexus_core": "V8.3 META COMANDA", "comanda": "META via Groq", "backup": "GEMINI so se Meta falhar", "gemini": bool(self.gemini_key), "meta": bool(self.meta_key), "motor": "meta-groq-gpt-oss-20b", "avatares": NOMES}
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
    def _meta_comanda(self, pergunta, contexto, dept):
        # META COMANDA: tenta Meta primeiro, sempre. Gemini so se Meta falhar.
        chave = str(self.meta_key or "").strip()
        cache_key = dept + "|" + pergunta.strip().lower()[:120]
        if cache_key in self._cache:
            return self._cache[cache_key]
        prompt = PERSONALIDADES[dept] + "\nHistorico curto:" + contexto + "\nPergunta:" + pergunta
        if chave:
            for modelo in ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]:
                try:
                    from groq import Groq
                    c = Groq(api_key=chave)
                    r = c.chat.completions.create(model=modelo, messages=[{"role": "system", "content": PERSONALIDADES[dept]}, {"role": "user", "content": "Historico:" + contexto + "\nPergunta:" + pergunta}], temperature=0.5, max_tokens=450)
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
    def _meta_dept(self, pergunta, contexto, dept):
        return self._meta_comanda(pergunta, contexto, dept)
    def _gemini_dept(self, pergunta, contexto, dept):
        # Travado: ninguem chama Gemini direto. Sempre passa pela Meta primeiro.
        return self._meta_comanda(pergunta, contexto, dept)
    def _meta_lab(self, pergunta, contexto):
        return self._meta_comanda(pergunta, contexto, "lab")
    def reuniao(self, pergunta: str, destino: str = "todos"):
        t0 = time.time()
        pergunta = str(pergunta); destino = str(destino)
        contexto = "\n".join(self.historico[-3:])
        self.historico.append("CEO: " + pergunta + " [destino=" + destino + "]")
        lab_ai = ""; marketing_ai = ""; diretoria_ai = ""; codigo = ""
        if destino in ("todos", "opiniao"):
            diretoria_ai = self._meta_comanda(pergunta, contexto, "diretoria")
            self.historico.append("ORION (Meta): " + diretoria_ai)
            ordem = ""
            m = re.search(r"ORDEM DE SERVICO PARA (?:FORJA|LAB):(.*)", diretoria_ai, re.IGNORECASE | re.DOTALL)
            if m:
                ordem = m.group(0)[:500]
            pergunta_lab = pergunta + ("\n\nORDEM DO ORION PARA VOCE EXECUTAR:\n" + ordem if ordem else "")
            lab_ai = self._meta_comanda(pergunta_lab, "\n".join(self.historico[-3:]), "lab")
            self.historico.append("FORJA (Meta): " + lab_ai)
            codigo = lab_ai
            marketing_ai = self._meta_comanda(pergunta, "\n".join(self.historico[-3:]), "marketing")
            self.historico.append("LIA (Meta): " + marketing_ai)
        elif destino == "lab":
            lab_ai = self._meta_comanda(pergunta, contexto, "lab")
            codigo = lab_ai
        elif destino == "marketing":
            marketing_ai = self._meta_comanda(pergunta, contexto, "marketing")
        elif destino == "diretoria":
            diretoria_ai = self._meta_comanda(pergunta, contexto, "diretoria")
            m = re.search(r"ORDEM DE SERVICO PARA (?:FORJA|LAB):(.*)", diretoria_ai, re.IGNORECASE | re.DOTALL)
            if m:
                ordem = m.group(0)[:500]
                lab_ai = self._meta_comanda(pergunta + "\n\nORDEM DO ORION:\n" + ordem, "\n".join(self.historico[-3:]), "lab")
                codigo = lab_ai
                self.historico.append("FORJA executou ordem: " + lab_ai)
        tempo = round(time.time() - t0, 1)
        consolidado = "=== NEXUS CORE V8.3 META COMANDA, GEMINI SO BACKUP - " + str(tempo) + "s ===\nPergunta: " + pergunta + " | Destino: " + destino + "\n\n[ORION - Diretoria - Meta]\n" + str(diretoria_ai) + "\n\n[FORJA - Lab - Meta]\n" + str(lab_ai) + "\n\n[LIA - Marketing - Meta]\n" + str(marketing_ai) + "\n"
        return {"pergunta": pergunta, "destino": destino, "lab_ai": str(lab_ai), "marketing_ai": str(marketing_ai), "diretoria_ai": str(diretoria_ai), "codigo": str(codigo), "consolidado": str(consolidado), "tempo_seg": tempo, "avatares": NOMES, "comanda": "META", "backup": "GEMINI"}
