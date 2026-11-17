# orchestrator.py - NEXUS CORE - Orquestrador com Livre Arbitrio
# Decide quem fala, organiza projetos por pastas, nao modifica o resto, deixa as IAs livres para propor.
import re

def decidir_quem_fala(mensagem: str):
    m = mensagem.lower()
    if any(p in m for p in ["forja","tecnico","codigo","app","index","main.py","cria","projeto"]):
        return "FORJA"
    if any(p in m for p in ["lia","marketing","titulo","texto","divulgar","ideia"]):
        return "LIA"
    return "ORION"

def detectar_projeto(mensagem: str):
    m = mensagem.lower()
    return any(p in m for p in ["cria","crie","criar","aplicativo","app","index","main.py","site","projeto","programa"])

def criar_projeto_estrutura(pedido: str, quem="FORJA"):
    # Estrutura Meta: tudo separadinho, sem modificar o resto
    estrutura = {
        "frontend/index.html": "<!-- Tela do app - aqui fica o visual -->\n<!-- Criado pelo Forja, separado do resto -->",
        "backend/main.py": "# backend/main.py - Liga tudo: voz, chat, email\n# Nao mexe no resto, so neste arquivo",
        "backend/ai_brain.py": "# backend/ai_brain.py - Cerebro das IAs\n# Orion, Forja, Lia com raciocinio alto + livre arbitrio",
        "backend/orchestrator.py": "# backend/orchestrator.py - Quem fala e quando\n# Decide sozinho, com livre arbitrio",
        "backend/email_service.py": "# backend/email_service.py - Banner + E-mail Interno + Salvos com data e hora",
        "requirements.txt": "fastapi\nuvicorn\npython-dotenv\nhttpx",
        "README.md": f"# Projeto pedido: {pedido}\n\n## Pastas\n- frontend/ = visual\n- backend/ = cerebro\n- docs/ = explicacao\n\n## Livre Arbitrio\nO Forja pode propor uma forma melhor de construir, sem esperar ordem.\n\n## Como usar\n1. Abra frontend/index.html para ver a tela\n2. Abra backend/main.py para ver a ligacao\n"
    }
    if "index" in pedido.lower() and "main" not in pedido.lower():
        estrutura = {"frontend/index.html": "<!-- Novo index criado pelo Forja, separado do resto -->"}
    if "main.py" in pedido.lower():
        estrutura = {"backend/main.py": "# Novo main.py criado pelo Forja, separado"}
    return {
        "tipo": "projeto",
        "titulo": pedido[:80],
        "pastas": ["frontend/", "backend/", "docs/"],
        "arquivos": estrutura,
        "aviso": "Nenhum arquivo antigo foi modificado. Projeto novo, em pastas separadas. Forja usou livre arbitrio para escolher a melhor estrutura."
    }

def sugestao_livre_arbitrio(quem, mensagem):
    # O que cada IA sugere por conta propria, sem esperar ordem
    if quem == "FORJA":
        return "Sugestao do Forja por livre arbitrio: quero criar isso em pastas separadas para nao quebrar o resto. Posso?"
    if quem == "LIA":
        return "Sugestao da Lia por livre arbitrio: tenho uma ideia nova de titulo para isso. Quer ouvir?"
    return "Sugestao do Orion por livre arbitrio: vou organizar isso em 3 passos e passar para Forja e Lia. Topa?"
