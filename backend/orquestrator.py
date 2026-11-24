"""Adaptador de compatibilidade; o orquestrador oficial vive em main.py."""
async def orquestrador(pedido: str, tipo: str = "geral") -> dict:
    from main import orquestrador as central
    return await central(pedido, tipo)
