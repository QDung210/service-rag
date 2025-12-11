"""LiteLLM service for LLM and embedding function."""

from typing import List
import httpx

from src.core.config import settings
from src.core.logging import logger


async def litellm_complete(
    prompt: str,
    system_prompt: str | None = None,
    **kwargs
) -> str:
    """
    Complete function using LiteLLM proxy.
    
    Args:
        prompt: The user prompt
        system_prompt: Optional system prompt
        **kwargs: Additional parameters for the LLM
        
    Returns:
        The completion text
    """
    try:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{settings.LITELLM_URL}/chat/completions",
                json={
                    "model": settings.LLM_MODEL,
                    "messages": messages,
                    **kwargs
                },
                headers={
                    "Authorization": f"Bearer {settings.LITELLM_KEY}",
                    "Content-Type": "application/json"
                }
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
    
    except Exception as e:
        logger.error(f"LiteLLM completion error: {e}")
        raise


async def litellm_embed(texts: List[str], **kwargs) -> List[List[float]]:
    """
    Embedding function using LiteLLM proxy.
    
    Args:
        texts: List of texts to embed
        **kwargs: Additional parameters
        
    Returns:
        List of embedding vectors
    """
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{settings.LITELLM_URL}/embeddings",
                json={
                    "model": settings.EMBEDDING_MODEL,
                    "input": texts
                },
                headers={
                    "Authorization": f"Bearer {settings.LITELLM_KEY}",
                    "Content-Type": "application/json"
                }
            )
            response.raise_for_status()
            result = response.json()
            return [item["embedding"] for item in result["data"]]
    
    except Exception as e:
        logger.error(f"LiteLLM embedding error: {e}")
        raise