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
        self._gemini_model = None
        self._meta_client = None
        self.historico = []
    def health(self):
        return {"nexus_core": "V4 ON", "gemini": bool(self.gemini_key), "meta": bool(self.meta_key)}
    def _get_gemini(self):
        if self._gemini_model is None:
            if not self.gemini_key:
                raise ValueError("GEMINI_API_KEY nao encontrada")
            import google.generativeai as genai
            genai.configure(api_key=str(self.gemini_key).strip())
            # CORRECAO V4.2: Google aposentou 1.5-flash e depois 2.0-flash.
            # O erro no seu print mesmo fala: use gemini-3.8-flash.
            # Agora usa 3.8-flash como principal.
            self._gemini_model = genai.GenerativeModel("gemini-3.8-flash")
        return self._gemini_model
    def _get_meta(self):
        if self._meta_client is None:
            if not self.meta_key:
                raise ValueError("META_API_KEY nao encontrada")
            from groq import Groq
            # CORRECAO: tira espaco que vem quando copia a chave, espaco ja dava 401 Invalid API Key
            self._meta_client = Groq(api_key=str(self.meta_key).strip())
        return self._meta_client
    def _meta_lab(self, pergunta, contexto):
        try:
            c = self._get_meta()
            # CORRECAO V4.2: Groq aposentou llama-3.3-70b-versatile, por isso dava 404 model_not_found.
            # Agora tenta os modelos atuais, um por um, ate um funcionar.
            for modelo in ["llama-3.1-8b-instant", "meta-llama/llama-4-scout-17b-16e-instruct", "llama-3.3-70b-versatile", "openai/gpt-oss-120b"]:
                try:
                    r = c.chat.completions.create(model=modelo, messages=[{"role": "system", "content": PERSONALIDADES["lab"]}, {"role": "user", "content": "Historico:" + contexto + "\nPergunta:" + pergunta}], temperature=0.4, max_tokens=900)
                    return str(r.choices[0].message.content)
                except Exception as e:
                    ultimo_erro = str(e)
                    continue
            return "[Lab indisponivel] " + ultimo_erro
        except Exception as e:
            return "[Lab indisponivel] " + str(e)
    def _gemini_dept(self, pergunta, contexto, dept):
        try:
            import google.generativeai as genai
            genai.configure(api_key=str(self.gemini_key).strip())
            prompt = PERSONALIDADES[dept] + "\nHistorico:" + contexto + "\nPergunta:" + pergunta
            # Tenta o modelo novo, se falhar tenta os outros - assim nao quebra de novo se o Google aposentar um
            for modelo in ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash-latest"]:
                try:
                    m = genai.GenerativeModel(modelo)
                    return str(m.generate_content(prompt).text)
                except Exception as e:
                    ultimo_erro = str(e)
                    continue
            return "[" + dept + " indisponivel] " + ultimo_erro
        except Exception as e:
            return "[" + dept + " indisponivel] " + str(e)
    def reuniao(self, pergunta: str, destino: str = "todos"):
        pergunta = str(pergunta); destino = str(destino)
        contexto = "\n".join(self.historico[-10:])
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
