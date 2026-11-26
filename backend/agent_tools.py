"""Configuração segura das ferramentas nativas do agente Nexuscore.

As ferramentas são executadas pela infraestrutura Groq, não pelo processo Render.
Somente ferramentas explicitamente permitidas por variável de ambiente são enviadas.
"""
from __future__ import annotations

import os
from typing import Optional

SUPPORTED_GROQ_TOOLS = frozenset({"browser_search", "code_interpreter"})
BUILTIN_TOOLS_MODEL = "openai/gpt-oss-120b"


def configured_groq_tools(
    raw: Optional[str] = None,
    model: Optional[str] = None,
) -> list[dict[str, str]]:
    """Retorna ferramentas permitidas; por padrão, nenhuma fica habilitada.

    A execução nativa documentada pela Groq é limitada ao GPT-OSS 120B/20B.
    Nesta primeira etapa, habilitamos apenas o modelo já usado pelo Nexuscore.
    """
    selected_model = (model or os.getenv("GROQ_MODEL", BUILTIN_TOOLS_MODEL)).strip()
    if selected_model != BUILTIN_TOOLS_MODEL:
        return []

    configured = os.getenv("GROQ_AGENT_TOOLS", "") if raw is None else raw
    names = {
        item.strip().lower()
        for item in str(configured or "").split(",")
        if item.strip()
    }
    return [
        {"type": name}
        for name in ("browser_search", "code_interpreter")
        if name in names and name in SUPPORTED_GROQ_TOOLS
    ]


def agent_tools_status(
    raw: Optional[str] = None,
    model: Optional[str] = None,
) -> dict:
    """Estado seguro para diagnóstico: nunca retorna chaves ou segredos."""
    tools = configured_groq_tools(raw=raw, model=model)
    return {
        "disponivel": bool(tools),
        "modelo_compativel": (model or os.getenv("GROQ_MODEL", BUILTIN_TOOLS_MODEL)).strip()
        == BUILTIN_TOOLS_MODEL,
        "ferramentas_ativas": [tool["type"] for tool in tools],
        "observacao": "Ferramentas desativadas por padrão; configure GROQ_AGENT_TOOLS para habilitar.",
    }
