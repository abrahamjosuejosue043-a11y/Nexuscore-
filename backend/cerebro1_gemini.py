"""
CEREBRO 1 - GEMINI (Google)
Responsabilidade: apoiar Diretoria e Publicidade com organização,
resumos, ordens de serviço, nomes, slogans e campanhas.

Variáveis de ambiente:
- GEMINI_API_KEY: chave da API Google Gemini.
- GEMINI_MODEL: modelo utilizado (padrão: gemini-2.0-flash).

A chave deve ser configurada no ambiente do Render, nunca neste arquivo.
"""

import os
from typing import Any

import httpx


class GeminiError(RuntimeError):
    """Erro controlado durante a comunicação com a API Gemini."""


async def chamar_gemini(pergunta: str) -> str:
    """
    Envia uma solicitação ao Gemini e retorna somente o texto gerado.

    A função é assíncrona e utiliza httpx, em alinhamento com o main.py.
    Erros de configuração, rede, HTTP ou resposta inesperada geram GeminiError.
    """
    texto = str(pergunta or "").strip()
    if not texto:
        raise GeminiError("A solicitação para o Gemini está vazia.")

    chave = os.getenv("GEMINI_API_KEY", "").strip()
    if not chave:
        raise GeminiError("A variável GEMINI_API_KEY não está configurada.")

    modelo = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()
    if not modelo:
        modelo = "gemini-2.0-flash"

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{modelo}:generateContent"
    )
    corpo = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": texto}],
            }
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as cliente:
            resposta = await cliente.post(
                url,
                params={"key": chave},
                json=corpo,
            )
    except httpx.TimeoutException as erro:
        raise GeminiError("A API Gemini excedeu o tempo limite de resposta.") from erro
    except httpx.RequestError as erro:
        raise GeminiError("Não foi possível conectar à API Gemini.") from erro

    if resposta.status_code != 200:
        detalhe = ""
        try:
            dados_erro = resposta.json()
            detalhe = dados_erro.get("error", {}).get("message", "")
        except (ValueError, AttributeError):
            pass

        if not detalhe:
            detalhe = f"HTTP {resposta.status_code}"

        raise GeminiError(f"Falha na API Gemini: {detalhe[:300]}")

    try:
        dados: dict[str, Any] = resposta.json()
    except ValueError as erro:
        raise GeminiError("A API Gemini retornou uma resposta JSON inválida.") from erro

    candidatos = dados.get("candidates") or []
    if not candidatos:
        feedback = dados.get("promptFeedback") or {}
        motivo = feedback.get("blockReason")
        if motivo:
            raise GeminiError(f"A solicitação foi bloqueada pelo Gemini: {motivo}.")
        raise GeminiError("A API Gemini não retornou nenhum candidato de resposta.")

    partes = (candidatos[0].get("content") or {}).get("parts") or []
    partes_texto = [
        parte.get("text", "").strip()
        for parte in partes
        if isinstance(parte, dict) and parte.get("text", "").strip()
    ]

    if not partes_texto:
        motivo = candidatos[0].get("finishReason")
        complemento = f" Motivo: {motivo}." if motivo else ""
        raise GeminiError(
            "O Gemini retornou uma resposta sem conteúdo de texto." + complemento
        )

    return "\n".join(partes_texto)


if __name__ == "__main__":
    import asyncio

    async def teste_local() -> None:
        try:
            resultado = await chamar_gemini(
                "Crie uma ordem de serviço para um aplicativo de lista de tarefas."
            )
            print(resultado)
        except GeminiError as erro:
            print(f"Erro no teste do Gemini: {erro}")

    asyncio.run(teste_local())
