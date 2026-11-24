"""Cliente assíncrono legado para Groq (Llama). O uso principal está em main.py."""
import os
import httpx

async def chamar_meta(pergunta: str) -> str:
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GROQ_API_KEY não está configurada.")
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": model, "messages": [
                {"role": "system", "content": "Você é o agente de Engenharia do Nexuscore AI. Responda em português."},
                {"role": "user", "content": str(pergunta)}
            ], "temperature": 0.4, "max_tokens": 4096}
        )
    if response.status_code != 200:
        raise RuntimeError(f"Groq retornou HTTP {response.status_code}.")
    choices = response.json().get("choices") or []
    answer = choices[0].get("message", {}).get("content", "") if choices else ""
    if not answer:
        raise RuntimeError("Groq retornou resposta vazia.")
    return answer.strip()
