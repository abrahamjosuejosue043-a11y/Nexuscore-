# orchestrator.py - NEXUS CORE - O QUE COMANDA O CEREBRO - V3
# O cerebro pensa. O orquestrador MANDA.
# Ele liga TODAS as funcoes do cerebro V3:
# - ORION diretoria: ordem de servico + e-mail detalhado + resumo + passa para departamentos a mando do CEO
# - FORJA: codigos e apps completos - objetivo principal = criar aplicativos
# - LIA: imagens em tempo real + marketing
# - Fila pedir a palavra: um fala de cada vez
# - Backup Gemini: salva TUDO
# - Perfil CEO: aprende o jeito do Josue
# - Voz principal: ElevenLabs
import re

VOZ_PRINCIPAL = "elevenlabs"  # Enfase ElevenLabs, Cartesia so de reserva
OBJETIVO_PRINCIPAL = "ajudar no desenvolvimento de aplicativos"

def decidir_quem_fala(mensagem: str):
    # Decide quem fala, com base no pedido do CEO
    m = (mensagem or "").lower()
    if any(p in m for p in ["ordem", "email", "e-mail", "analise", "analisa", "diretoria", "resumo", "reuniao", "orion"]):
        return "ORION"
    if any(p in m for p in ["forja", "tecnico", "codigo", "app", "index", "main.py", "cria", "projeto", "programa", "site", "sistema"]):
        return "FORJA"
    if any(p in m for p in ["lia", "marketing", "titulo", "texto", "divulgar", "ideia", "imagem", "capa", "foto", "video"]):
        return "LIA"
    return "ORION"

def detectar_projeto(mensagem: str):
    m = (mensagem or "").lower()
    return any(p in m for p in ["cria", "crie", "criar", "aplicativo", "app", "index", "main.py", "site", "projeto", "programa", "codigo", "sistema"])

def detectar_imagem(mensagem: str):
    m = (mensagem or "").lower()
    return any(p in m for p in ["imagem", "gera imagem", "cria imagem", "capa", "foto", "desenha", "logo", "banner", "cartaz"])

def detectar_ordem_servico(mensagem: str):
    m = (mensagem or "").lower()
    return any(p in m for p in ["ordem de servico", "ordem de serviço", "gera ordem", "cria ordem", "ordem"])

def detectar_email(mensagem: str):
    m = (mensagem or "").lower()
    return any(p in m for p in ["email", "e-mail", "analisa esse", "resumo do email", "ler email"])

def detectar_reuniao(mensagem: str):
    m = (mensagem or "").lower()
    return any(p in m for p in ["reuniao", "reunião", "inicia reuniao", "pedir a palavra", "encerrar"])

def criar_projeto_estrutura(pedido: str, quem="FORJA"):
    # FORJA - Cria projeto por pastas separadas, sem mexer no resto
    # Estrutura Meta: frontend, backend, docs
    pedido_limpo = (pedido or "Novo app")[:120]
    estrutura = {
        "frontend/index.html": "<!-- frontend/index.html - Tela do app - Visual -->\n<!-- Criado pelo Forja, separado do resto -->\n<!-- Objetivo: ajudar a criar aplicativos -->\n<h1>Seu app aqui</h1>",
        "backend/main.py": "# backend/main.py - Liga tudo: voz, chat, email\n# Nao mexe no resto, so neste arquivo\nfrom fastapi import FastAPI\napp = FastAPI(title='NEXUS CORE')",
        "backend/ai_brain.py": "# backend/ai_brain.py - Cerebro V3\n# Orion diretoria, Forja codigo, Lia imagem em tempo real\n# Raciocinio 6 passos, livre arbitrio altissimo, backup Gemini, perfil CEO",
        "backend/orchestrator.py": "# backend/orchestrator.py - O que comanda o cerebro V3\n# Liga todas as funcoes: ordem, email, codigo, imagem, fila, backup, voz ElevenLabs",
        "backend/email_service.py": "# backend/email_service.py - Banner + E-mail Interno + Salvos com data e hora\n# Orion le primeiro, analisa detalhadamente, resume e passa para o time a mando do CEO",
        "backend/voice_service.py": "# backend/voice_service.py - Voz principal ElevenLabs, reserva Cartesia\n# Nunca trava, se falhar usa navegador",
        "requirements.txt": "fastapi\nuvicorn\npython-dotenv\nhttpx",
        "README.md": f"# Projeto pedido: {pedido_limpo}\n\n## Objetivo principal\nAjudar no desenvolvimento de aplicativos.\n\n## Pastas\n- frontend/ = visual\n- backend/ = cerebro\n- docs/ = explicacao\n\n## Time\n- ORION diretoria: ordem de servico, e-mail, resumo\n- FORJA: codigo e app completo\n- LIA: imagem em tempo real e marketing\n\n## Voz\nPrincipal: ElevenLabs. Reserva: Cartesia.\n\n## Como usar\n1. Abra frontend/index.html para ver a tela\n2. Abra backend/main.py para ver a ligacao\n3. Peça para o Forja criar, para a Lia criar imagem, para o Orion gerar ordem.\n",
    }
    # Se pediu so um arquivo, entrega so ele, sem mexer no resto
    if "index" in pedido.lower() and "main" not in pedido.lower():
        estrutura = {"frontend/index.html": "<!-- Novo index criado pelo Forja, separado do resto -->"}
    if "main.py" in pedido.lower() and "index" not in pedido.lower():
        estrutura = {"backend/main.py": "# Novo main.py criado pelo Forja, separado"}
    return {
        "tipo": "projeto",
        "titulo": pedido_limpo,
        "pastas": ["frontend/", "backend/", "docs/"],
        "arquivos": estrutura,
        "aviso": "Nenhum arquivo antigo foi modificado. Projeto novo, em pastas separadas. Forja usou livre arbitrio para escolher a melhor estrutura.",
        "objetivo": OBJETIVO_PRINCIPAL,
        "voz_principal": VOZ_PRINCIPAL,
    }

def criar_ordem_estrutura(pedido: str):
    # ORION - Diretoria - Estrutura da ordem de servico
    return {
        "tipo": "ordem_servico",
        "pedido": pedido,
        "responsavel": "ORION - Diretoria",
        "passos": [
            "1. ORION: Recebeu e analisou o pedido do CEO",
            "2. FORJA: Parte tecnica / codigo / app",
            "3. LIA: Parte de marketing / imagem em tempo real",
            "4. ORION: Revisa e entrega para o CEO",
        ],
        "aviso": "Ordem gerada por Orion a mando do CEO. Salva no backup Gemini.",
    }

def criar_imagem_estrutura(pedido: str):
    # LIA - Imagem em tempo real
    return {
        "tipo": "imagem",
        "pedido": pedido,
        "responsavel": "LIA - Imagem em tempo real",
        "passos": [
            "1. LIA: Entendeu o pedido de imagem",
            "2. LIA: Gera imagem em tempo real",
            "3. ORION: Revisa e entrega para o CEO",
        ],
        "aviso": "Lia capacitada totalmente para gerar imagens em tempo real.",
    }

def comandar_cerebro(mensagem: str):
    # FUNCAO PRINCIPAL - O que comanda o cerebro
    # Recebe a mensagem do CEO e decide: quem fala, o que fazer, para quem passar
    # Retorna um plano claro, para o main.py e o ai_brain.py executarem
    m = (mensagem or "").strip()
    quem = decidir_quem_fala(m)
    acao = "conversar"
    detalhes = {}
    # Prioridade 1: Ordem de servico - ORION diretoria
    if detectar_ordem_servico(m):
        quem = "ORION"
        acao = "ordem_servico"
        detalhes = criar_ordem_estrutura(m)
    # Prioridade 2: E-mail - ORION diretoria analisa detalhadamente
    elif detectar_email(m):
        quem = "ORION"
        acao = "analisar_email"
        detalhes = {"tipo": "analisar_email", "responsavel": "ORION - Diretoria", "passos": ["1. ORION: Recebe e-mail", "2. ORION: Analisa detalhadamente, extrai conteudo", "3. ORION: Faz resumo", "4. ORION: Passa para Forja e Lia a mando do CEO"]}
    # Prioridade 3: Imagem - LIA tempo real
    elif detectar_imagem(m):
        quem = "LIA"
        acao = "gerar_imagem"
        detalhes = criar_imagem_estrutura(m)
    # Prioridade 4: Projeto / Codigo / App - FORJA
    elif detectar_projeto(m):
        quem = "FORJA"
        acao = "criar_projeto"
        detalhes = criar_projeto_estrutura(m, "FORJA")
    # Prioridade 5: Reuniao
    elif detectar_reuniao(m):
        quem = "ORION"
        acao = "reuniao"
        detalhes = {"tipo": "reuniao", "responsavel": "ORION - Moderador e Diretoria", "passos": ["1. ORION: Inicia reuniao", "2. Fila pedir a palavra: um fala de cada vez", "3. FORJA: Tecnico", "4. LIA: Imagem e marketing", "5. ORION: Resume e gera ordem se precisar"]}
    # Plano final - tudo vinculado
    plano = {
        "quem": quem,
        "acao": acao,
        "mensagem_original": m,
        "detalhes": detalhes,
        "voz_principal": VOZ_PRINCIPAL,
        "objetivo_principal": OBJETIVO_PRINCIPAL,
        "salvar_backup": True,
        "aprender_perfil_ceo": True,
        "regras": [
            "Um fala de cada vez - fila pedir a palavra",
            "Sem repetir frase",
            "Portugues simples, passo a passo",
            "Sem emoji",
            "Salvar tudo no backup Gemini",
        ],
        "para_onde_vai": {
            "ORION": "diretoria, ordem, e-mail, resumo",
            "FORJA": "codigo e app completo",
            "LIA": "imagem em tempo real e marketing",
        },
    }
    return plano

def sugestao_livre_arbitrio(quem, mensagem):
    # O que cada IA sugere por conta propria, sem esperar ordem
    if quem == "FORJA":
        return "Sugestao do Forja por livre arbitrio: quero criar isso em pastas separadas para nao quebrar o resto. Posso? Objetivo principal e ajudar voce a criar aplicativos."
    if quem == "LIA":
        return "Sugestao da Lia por livre arbitrio: tenho uma ideia nova de imagem em tempo real para isso. Quer que eu gere agora?"
    return "Sugestao do Orion por livre arbitrio: vou organizar isso em 3 passos, gerar ordem de servico se precisar, e passar para Forja e Lia a seu mando. Topa?"

def iniciar_reuniao_plano():
    return {
        "tipo": "reuniao",
        "moderador": "ORION - Diretoria",
        "participantes": ["ORION", "FORJA", "LIA"],
        "regras": ["Um fala de cada vez", "Pedir a palavra na fila", "Orion organiza", "Forja codigo", "Lia imagem"],
        "voz_principal": VOZ_PRINCIPAL,
    }
