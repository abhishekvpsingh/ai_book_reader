import logging
from app.services.llm_providers import get_provider

logger = logging.getLogger(__name__)


def answer_question(selection_text: str, question: str) -> str:
    prompt = (
        "You are a helpful tutor. Answer the user's question using only the provided book excerpt. "
        "Keep the answer concise, clear, and friendly for TTS. If the excerpt doesn't contain the answer, "
        "say you cannot find it in the provided text."
    )
    context = f"Excerpt:\n{selection_text}\n\nQuestion:\n{question}"
    provider = get_provider()
    return provider.generate(prompt, context)
