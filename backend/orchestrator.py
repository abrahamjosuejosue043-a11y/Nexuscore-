import os
PERSONALIDADES = {
    "lab": "Voce e Meta AI, Dept LABORATORIO, Nexus Core Innova XR. Personalidade: ENGENHEIRO PRECISO. Unico que gera codigo. Logico, direto, Python, HTML, API, teste, seguranca.",
    "marketing": "Voce e Gemini Marketing, Dept MARKETING, Nexus Core. Personalidade: COMUNICADORA PERSUASIVA. Campanha, copy, slogan, tendencia. Nao gere codigo.",
    "diretoria": "Voce e Gemini Diretoria, Dept DIRETORIA, Nexus Core. Personalidade: VISIONARIO ESTRATEGICO. Ideias novas, impulsiona empresa."
}
class OrquestradorNexusV4:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.meta_key = os.getenv("META_API_KEY")
        self.historico = []
    def health(self):
        return {"nexus_core": "V4 ON", "gemini": bool(self.gemini_key), "meta": bool(self.meta_key)}
    def _gemini_dept(self, pergunta, contexto, dept):
        # V4.3 RAPIDO: tenta so 1 modelo principal, nao 4 em sequencia.
        # Antes tentava 4 modelos, demorava tanto que o Render cortava e nao respondia nada.
        prompt = PERSONALIDADES[dept] + "\nHistorico:" + contexto + "\nPergunta:" + pergunta
        chave = str(self.gemini_key or "").strip()
        if not chave:
            return "[" + dept + " indisponivel] GEMINI_API_KEY nao encontrada no Render"
        # Tenta SDK novo primeiro (google-genai) que conhece gemini-3.8-flash
        try:
            from google import genai as genai_novo
            client = genai_novo.Client(api_key=chave)
            resp = client.models.generate_content(model="gemini-3.8-flash", contents=prompt)
            txt = getattr(resp, "text", "") or ""
            if txt.strip():
                return str(txt)
        except Exception as e:
            ultimo_erro_novo = str(e)
        else:
            ultimo_erro_novo = "sem texto"
        # Fallback SDK antigo
        try:
            import google.generativeai as genai_antigo
            genai_antigo.configure(api_key=chave)
            m = genai_antigo.GenerativeModel("gemini-3.8-flash")
            return str(m.generate_content(prompt).text)
        except Exception as e:
            return "[" + dept + " indisponivel] " + str(e) + " | novo SDK: " + ultimo_erro_novo
    def _meta_lab(self, pergunta, contexto):
        chave = str(self.meta_key or "").strip()
        if not chave:
            return "[Lab indisponivel] META_API_KEY nao encontrada no Render"
        try:
            from groq import Groq
            c = Groq(api_key=chave)
            # V4.3 RAPIDO: so 1 modelo principal, nao 4 em sequencia
            r = c.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": PERSONALIDADES["lab"]}, {"role": "user", "content": "Historico:" + contexto + "\nPergunta:" + pergunta}], temperature=0.4, max_tokens=900)
            return str(r.choices[0].message.content)
        except Exception as e:
            # 1 fallback so, rapido
            try:
                from groq import Groq
                c = Groq(api_key=chave)
                r = c.chat.completions.create(model="meta-llama/llama-4-scout-17b-16e-instruct", messages=[{"role": "system", "content": PERSONALIDADES["lab"]}, {"role": "user", "content": "Historico:" + contexto + "\nPergunta:" + pergunta}], temperature=0.4, max_tokens=900)
                return str(r.choices[0].message.content)
            except Exception as e2:
                return "[Lab indisponivel] " + str(e2)
    def reuniao(self, pergunta: str, destino: str = "todos"):
        pergunta = str(pergunta); destino = str(destino)
        contexto = "\n".join(self.historico[-6:])
        self.historico.append("CEO: " + pergunta + " [destino=" + destino + "]")
        lab_ai = ""; marketing_ai = ""; diretoria_ai = ""; codigo = ""
        if destino in ("todos", "lab", "opiniao"):
            lab_ai = self._meta_lab(pergunta, contexto)
            self.historico.append("Lab: " + lab_ai)
            codigo = lab_ai
        if destino in ("todos", "marketing", "opiniao"):
            marketing_ai = self._gemini_dept(pergunta, contexto, "marketing")
            self.historico.append("Marketing: " + marketing_ai)
        if destino in ("todos", "diretoria", "opiniao"):
            diretoria_ai = self._gemini_dept(pergunta, contexto, "diretoria")
            self.historico.append("Diretoria: " + diretoria_ai)
        if destino == "lab":
            marketing_ai = ""; diretoria_ai = ""
        if destino == "marketing":
            lab_ai = ""; diretoria_ai = ""; codigo = ""
        if destino == "diretoria":
            lab_ai = ""; marketing_ai = ""; codigo = ""
        consolidado = "=== NEXUS CORE V4 ===\nPergunta: " + pergunta + " | Destino: " + destino + "\n\n[LAB]\n" + str(lab_ai) + "\n\n[MARKETING]\n" + str(marketing_ai) + "\n\n[DIRETORIA]\n" + str(diretoria_ai) + "\n"
        return {"pergunta": pergunta, "destino": destino, "lab_ai": str(lab_ai), "marketing_ai": str(marketing_ai), "diretoria_ai": str(diretoria_ai), "codigo": str(codigo), "consolidado": str(consolidado)}
