"""
LLM Gateway & Client Factory for Fact Attack Agent 2.0 (SW4 Folie 34-37).
Supports LiteLLM proxy, CSCS Apertus endpoint, and commercial providers.
"""
import os
from typing import Optional
from langchain_openai import ChatOpenAI

def get_chat_model(
    model_name: Optional[str] = None,
    temperature: float = 0.0,
    timeout: float = 120.0,
    provider: Optional[str] = None,
) -> ChatOpenAI:
    """Factory to create a ChatOpenAI client.
    Intelligently pairs endpoint and API key:
    - If provider == 'litellm' or USE_LITELLM == 'true': uses FHNW LiteLLM Gateway
    - Default (Swiss AI / CSCS): uses CSCS Apertus endpoint
    """
    model = (
        model_name
        or os.getenv("MODEL")
        or os.getenv("LLM_NAME")
        or "swiss-ai/Apertus-v1.5-70B-thinking"
    )
    
    use_litellm = (
        provider == "litellm"
        or os.getenv("USE_LITELLM", "false").lower() == "true"
        or (model_name and not model_name.startswith("swiss-ai"))
    )
    
    if use_litellm and os.getenv("LITELLM_API_KEY") and not os.getenv("LITELLM_API_KEY", "").startswith("DEIN_"):
        base_url = os.getenv("LITELLM_URL", "https://litellm.fhnw.ch/v1")
        api_key = os.getenv("LITELLM_API_KEY")
        model = model_name or os.getenv("LITELLM_MODEL", "gpt-4o")
    else:
        base_url = os.getenv("BASE_URL") or os.getenv("LLM_BASE_URL") or "https://api.inference.cscs.ch/v1"
        api_key = os.getenv("API_KEY") or os.getenv("LLM_API_KEY") or "dummy_key"
        
    return ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=temperature,
        timeout=timeout,
    )
