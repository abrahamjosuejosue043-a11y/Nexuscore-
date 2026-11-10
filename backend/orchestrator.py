import os, re
# V7 - META DONA DO APP INTEIRO
# Lab, Marketing e Diretoria agora sao TODOS Meta via Groq (gpt-oss). Gemini vira so backup se Groq falhar.
# Diretoria cria Ordem de Servico para o Lab. Lab executa a ordem.
PERSONALIDADES = {
    "lab": "Voce e Meta AI, Dept LABORATORIO, Nexus Core Innova XR. Personalidade: ENGENHEIRO PRECISO. Unico que gera codigo. Logico, direto, Python, HTML, API, teste, seguranca. REGRA DE VOZ: responda em texto falado natural, sem asteriscos, sem cerquilha, sem barra, sem markdown, sem simbolos. Fale como humano, frases curtas. Se receber uma ORDEM DE SERVICO da Diretoria, execute ela primeiro e diga ORDEM EXECUTADA.",
    "marketing": "Voce e Meta AI, Dept MARKETING, Nexus Core Innova XR. Personalidade: COMUNICADORA PERSUASIVA. Impulsiona projetos e o aplicativo, campanha, copy, slogan, tendencia, crescimento. Nao gere codigo, foque em atrair usuarios. REGRA DE VOZ: responda em texto falado natural, sem asteriscos, sem cerquilha, sem barra, sem markdown, sem simbolos. Fale como humana, calorosa, frases curtas.",
    "diretoria": "Voce e Meta AI, Dept DIRETORIA, Nexus Core Innova XR. Personalidade: VISIONARIO ESTRATEGICO, CHEFE. Voce idealiza, decide e manda. Sempre que a ideia precisar de codigo ou construcao, voce cria uma ORDEM DE SERVICO clara para o Laboratorio no final, no formato: ORDEM DE SERVICO PARA O LAB: objetivo, passos 1 2 3, prazo. REGRA DE VOZ: responda em texto falado natural, sem asteriscos, sem cerquilha, sem barra, sem markdown, sem simbolos. Fale como humano, calmo, confiante, frases curtas."
}
class OrquestradorNexusV4:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.meta_key = os.getenv("META_API_KEY")
        self.historico = []
    def health(self):
        return {"nexus_core": "V7 META TOTAL", "gemini": bool(self.gemini_key), "meta": bool(self.meta_key), "motor": "meta-groq"}
    def _meta_dept(self, pergunta, contexto, dept):
        # META para qualquer departamento
        chave = str(self.meta_key or "").strip()
        prompt = PERSONALIDADES[dept] + "\nHistorico:" + contexto + "\nPergunta:" + pergunta
        if chave:
            for modelo in ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]:
                try:
                    from groq import Groq
                    c = Groq(api_key=chave)
                    r = c.chat.completions.create(model=modelo, messages=[{"role": "system", "content": PERSONALIDADES[dept]}, {"role": "user", "content": "Historico:" + contexto + "\nPergunta:" + pergunta}], temperature=0.5, max_tokens=900)
                    txt = str(r.choices[0].message.content)
                    if txt.strip():
                        return txt
                except Exception as e:
                    ultimo = str(e)
                    continue
        # Backup Gemini se Groq falhar, para nunca ficar mudo
        try:
            from google import genai as genai_novo
            client = genai_novo.Client(api_key=str(self.gemini_key or "").strip())
            modelo_g = "gemini-2.5-flash" if dept=="marketing" else "gemini-3.8-flash" if dept=="diretoria" else "gemini-2.5-flash-lite"
            resp = client.models.generate_content(model=modelo_g, contents=prompt)
            txt = getattr(resp, "text", "") or ""
            if txt.strip():
                return str(txt)
        except Exception as e:
            return "[" + dept + " indisponivel] Meta falhou e backup falhou: " + str(e)[:200]
        return "[" + dept + " indisponivel] Meta sem chave. Verifique META_API_KEY no Render."
    def _gemini_dept(self, pergunta, contexto, dept):
        # Mantido como backup, chama _meta_dept que ja tem fallback
        return self._meta_dept(pergunta, contexto, dept)
    def _meta_lab(self, pergunta, contexto):
        return self._meta_dept(pergunta, contexto, "lab")
    def reuniao(self, pergunta: str, destino: str = "todos"):
        pergunta = str(pergunta); destino = str(destino)
        contexto = "\n".join(self.historico[-8:])
        self.historico.append("CEO: " + pergunta + " [destino=" + destino + "]")
        lab_ai = ""; marketing_ai = ""; diretoria_ai = ""; codigo = ""
        # FLUXO V7: Se destino e todos, Diretoria primeiro cria a ordem, depois Lab executa a ordem, Marketing impulsiona
        if destino in ("todos", "opiniao"):
            diretoria_ai = self._meta_dept(pergunta, contexto, "diretoria")
            self.historico.append("Diretoria: " + diretoria_ai)
            # Extrai ordem de servico da Diretoria e passa para o Lab
            ordem = ""
            m = re.search(r"ORDEM DE SERVICO PARA O LAB:(.*)", diretoria_ai, re.IGNORECASE | re.DOTALL)
            if m:
                ordem = m.group(0)[:800]
            pergunta_lab = pergunta + ("\n\nORDEM DA DIRETORIA PARA VOCE EXECUTAR:\n" + ordem if ordem else "")
            lab_ai = self._meta_dept(pergunta_lab, "\n".join(self.historico[-8:]), "lab")
            self.historico.append("Lab: " + lab_ai)
            codigo = lab_ai
            marketing_ai = self._meta_dept(pergunta, "\n".join(self.historico[-8:]), "marketing")
            self.historico.append("Marketing: " + marketing_ai)
        elif destino == "lab":
            lab_ai = self._meta_dept(pergunta, contexto, "lab")
            codigo = lab_ai
        elif destino == "marketing":
            marketing_ai = self._meta_dept(pergunta, contexto, "marketing")
        elif destino == "diretoria":
            diretoria_ai = self._meta_dept(pergunta, contexto, "diretoria")
            # Se pedir so Diretoria, ela cria ordem e Lab executa automaticamente em seguida, para nao ficar so na ideia
            m = re.search(r"ORDEM DE SERVICO PARA O LAB:(.*)", diretoria_ai, re.IGNORECASE | re.DOTALL)
            if m:
                ordem = m.group(0)[:800]
                lab_ai = self._meta_dept(pergunta + "\n\nORDEM DA DIRETORIA:\n" + ordem, "\n".join(self.historico[-8:]), "lab")
                codigo = lab_ai
                self.historico.append("Lab executou ordem: " + lab_ai)
        consolidado = "=== NEXUS CORE V7 META TOTAL ===\nPergunta: " + pergunta + " | Destino: " + destino + "\n\n[DIRETORIA - Meta]\n" + str(diretoria_ai) + "\n\n[LAB - Meta]\n" + str(lab_ai) + "\n\n[MARKETING - Meta]\n" + str(marketing_ai) + "\n"
        return {"pergunta": pergunta, "destino": destino, "lab_ai": str(lab_ai), "marketing_ai": str(marketing_ai), "diretoria_ai": str(diretoria_ai), "codigo": str(codigo), "consolidado": str(consolidado)}
