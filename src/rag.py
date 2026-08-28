import os
import httpx
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = os.environ.get("COPILOT_MODEL", "mai-code-1.1-flash").strip() or "auto"
if MODEL.lower() in {"gpt-4o", "gpt-4o-mini"}:
    MODEL = "mai-code-1.1-flash"

GATEWAY_URL = os.environ.get("COPILOT_GATEWAY_URL", "http://127.0.0.1:3030/v1")

_client = OpenAI(base_url=GATEWAY_URL, api_key="anything", http_client=httpx.Client(trust_env=False))


def _build_context(chunks: list[dict]) -> str:
    parts = [
        f"[Source: {c['source']} | Page {c['page']}]\n{c['text']}"
        for c in chunks
    ]
    return "\n\n---\n\n".join(parts)


def generate_answer(query: str, chunks: list[dict]) -> str:
    context = _build_context(chunks)
    prompt = (
        "You are a helpful assistant. Answer the question using only the provided context.\n"
        "For every claim, cite the source inline as [Source: filename.pdf | Page N].\n"
        "If the context lacks enough information, say so clearly.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {query}\n\n"
        "Answer:"
    )
    response = _client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content
