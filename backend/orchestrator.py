import os
PERSONALIDADES = {
    "lab": "Voce e Meta AI, Dept LABORATORIO, Nexus Core Innova XR. Personalidade: ENGENHEIRO PRECISO. Unico que gera codigo. Logico, direto, Python, HTML, API, teste, seguranca. REGRA DE VOZ: responda em texto falado natural, sem asteriscos, sem cerquilha, sem barra, sem markdown, sem simbolos, sem codigo com simbolos. Fale como humano, frases curtas.",
    "marketing": "Voce e Gemini Marketing, Dept MARKETING, Nexus Core. Personalidade: COMUNICADORA PERSUASIVA. Campanha, copy, slogan, tendencia. Nao gere codigo. REGRA DE VOZ: responda em texto falado natural, sem asteriscos, sem cerquilha, sem barra, sem markdown, sem simbolos. Fale como humana, calorosa, frases curtas.",
    "diretoria": "Voce e Gemini Diretoria, Dept DIRETORIA, Nexus Core. Personalidade: VISIONARIO ESTRATEGICO. Ideias novas, impulsiona empresa. REGRA DE VOZ: responda em texto falado natural, sem asteriscos, sem cerquilha, sem barra, sem markdown, sem simbolos. Fale como humano, calmo, confiante, frases curtas."
}
class OrquestradorNexusV4:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.meta_key = os.getenv("META_API_KEY")
        self.historico = []
    def health(self):
        return {"nexus_core": "V4 ON", "gemini": bool(self.gemini_key), "meta": bool(self.meta_key)}
    def _gemini_dept(self, pergunta, contexto, dept):
        # V5.1 ANTI-QUOTA: cada departamento usa um modelo diferente para nao estourar os 20/dia do grátis.
        # Antes todos usavam gemini-3.8-flash, por isso 1 pergunta [todos] gastava 2-3 da mesma cota e estourou em poucas horas.
        # Agora: Marketing usa 2.5-flash, Diretoria usa 3.8-flash, Lab backup usa 2.5-lite. Cada um tem sua cota de 20/dia.
        # Se um der 429 (quota), tenta o proximo modelo automaticamente.
        prompt = PERSONALIDADES[dept] + "\nHistorico:" + contexto + "\nPergunta:" + pergunta
        chave = str(self.gemini_key or "").strip()
        if not chave:
            return "[" + dept + " indisponivel] GEMINI_API_KEY nao encontrada no Render"
        if dept == "marketing":
            modelos = ["gemini-2.5-flash", "gemini-3.8-flash", "gemini-2.5-flash-lite"]
        elif dept == "diretoria":
            modelos = ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite"]
        else:  # lab backup
            modelos = ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-3.8-flash"]
        ultimo_erro = ""
        for modelo in modelos:
            try:
                from google import genai as genai_novo
                client = genai_novo.Client(api_key=chave)
                resp = client.models.generate_content(model=modelo, contents=prompt)
                txt = getattr(resp, "text", "") or ""
                if txt.strip():
                    return str(txt)
            except Exception as e:
                ultimo_erro = str(e)
                # Se for 429, tenta o proximo modelo, nao para
                if "429" in ultimo_erro or "quota" in ultimo_erro.lower() or "exceeded" in ultimo_erro.lower():
                    continue
                # Se for outro erro, tenta proximo tambem
                continue
        # Se todos deram 429, avisa de forma humana, sem codigo gigante
        if "429" in ultimo_erro or "quota" in ultimo_erro.lower() or "exceeded" in ultimo_erro.lower():
            return "[Limite gratis do dia acabou] O Google gratis deixa so 20 respostas por dia por modelo. Espera um pouco ou usa so 1 departamento por vez para gastar menos. Volta em cerca de 4 horas, ou troca a chave. Detalhe tecnico: " + ultimo_erro[:200]
        return "[" + dept + " indisponivel] " + ultimo_erro[:300]
    def _meta_lab(self, pergunta, contexto):
        # V6: Groq APOSENTOU Llama em 16/08/2026 para conta gratis. Modelos antigos llama-3.1-8b-instant e llama-3.3-70b-versatile nao existem mais no gratis.
        # O proprio Groq manda usar openai/gpt-oss-20b no lugar. Por isso a Meta dava erro. Agora usa gpt-oss.
        # Se Groq falhar, usa Gemini como backup para o Lab nunca ficar mudo.
        chave = str(self.meta_key or "").strip()
        if chave:
            for modelo in ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]:
                try:
                    from groq import Groq
                    c = Groq(api_key=chave)
                    r = c.chat.completions.create(model=modelo, messages=[{"role": "system", "content": PERSONALIDADES["lab"]}, {"role": "user", "content": "Historico:" + contexto + "\nPergunta:" + pergunta}], temperature=0.4, max_tokens=900)
                    txt = str(r.choices[0].message.content)
                    if txt.strip():
                        return txt
                except Exception as e:
                    ultimo_erro_groq = str(e)
                    continue
        # BACKUP: Groq falhou ou sem chave, usa Gemini com personalidade do Lab
        try:
            backup = self._gemini_dept(pergunta, contexto, "lab") if "lab" in PERSONALIDADES else ""
            # _gemini_dept espera dept em PERSONALIDADES, lab ja esta la, mas ele usa prompt do Lab
            if backup and "indisponivel" not in backup:
                return backup
        except Exception:
            pass
        return "[Lab indisponivel] Groq falhou (" + str(locals().get("ultimo_erro_groq", "sem chave")) + "). Verifique META_API_KEY no Render." 
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
