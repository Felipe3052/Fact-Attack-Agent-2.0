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
) -> ChatOpenAI:
    """Factory to create a ChatOpenAI client routed to LiteLLM or direct provider.
    Priority:
    1. LITELLM_URL & LITELLM_API_KEY (FHNW Gateway)
    2. BASE_URL & API_KEY (CSCS Apertus Endpoint)
    3. LLM_BASE_URL & LLM_API_KEY
    """
    base_url = (
        os.getenv("LITELLM_URL")
        or os.getenv("BASE_URL")
        or os.getenv("LLM_BASE_URL")
        or "https://api.inference.cscs.ch/v1"
    )
    api_key = (
        os.getenv("LITELLM_API_KEY")
        or os.getenv("API_KEY")
        or os.getenv("LLM_API_KEY")
        or "dummy_key"
    )
    model = (
        model_name
        or os.getenv("MODEL")
        or os.getenv("LLM_NAME")
        or "swiss-ai/Apertus-v1.5-70B-thinking"
    )
    return ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=temperature,
        timeout=timeout,
    )
