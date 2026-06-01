import time
from typing import Optional

from openai import OpenAI

from app.config import settings


_client = None
_last_api_key = None
_last_api_base = None


def get_llm_client(api_key: Optional[str] = None, api_base: Optional[str] = None) -> OpenAI:
    global _client, _last_api_key, _last_api_base

    key = api_key or settings.deepseek_api_key
    base = api_base or settings.deepseek_api_base

    if _client is None or key != _last_api_key or base != _last_api_base:
        _client = OpenAI(
            api_key=key,
            base_url=base,
            timeout=300,
            max_retries=3,
        )
        _last_api_key = key
        _last_api_base = base

    return _client


def invalidate_llm_client():
    global _client, _last_api_key, _last_api_base
    _client = None
    _last_api_key = None
    _last_api_base = None


def chat_stream(
    messages: list,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    **kwargs,
):
    client = get_llm_client(api_key=api_key, api_base=api_base)
    return client.chat.completions.create(
        model=model or settings.llm_model,
        messages=messages,
        stream=True,
        temperature=kwargs.get("temperature", 0.7),
        max_tokens=kwargs.get("max_tokens", 8192),
        timeout=300,
    )


def chat(
    messages: list,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    **kwargs,
) -> str:
    client = get_llm_client(api_key=api_key, api_base=api_base)
    resp = client.chat.completions.create(
        model=model or settings.llm_model,
        messages=messages,
        stream=False,
        temperature=kwargs.get("temperature", 0.7),
        max_tokens=kwargs.get("max_tokens", 8192),
        timeout=300,
    )
    msg = resp.choices[0].message
    return msg.content or msg.reasoning_content or ""


def embed_text(text: str, api_key: Optional[str] = None, api_base: Optional[str] = None) -> list:
    client = get_llm_client(api_key=api_key, api_base=api_base)
    resp = client.embeddings.create(
        model=settings.embedding_model,
        input=text,
        timeout=120,
    )
    return resp.data[0].embedding
