import logging
from typing import Protocol
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMProvider(Protocol):
    def generate(self, prompt: str, context: str) -> str:
        ...


class OpenAIProvider:
    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI provider")

    def generate(self, prompt: str, context: str) -> str:
        payload = {
            "model": settings.openai_model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": context},
            ],
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=60) as client:
            response = client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()


class OllamaProvider:
    def generate(self, prompt: str, context: str) -> str:
        payload = {
            "model": settings.ollama_model,
            "prompt": f"{prompt}\n\n{context}",
            "stream": False,
        }
        url = f"{settings.ollama_url.rstrip('/')}/api/generate"
        with httpx.Client(timeout=120) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()


def get_provider() -> LLMProvider:
    provider = settings.llm_provider.lower()
    if provider == "openai":
        logger.info("Using OpenAI provider")
        return OpenAIProvider()
    if provider == "ollama":
        logger.info("Using Ollama provider")
        return OllamaProvider()
    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
